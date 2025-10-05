import asyncio
import json
import time
import logging
import traceback
import re
from typing import Callable, Dict, List, Optional, Union, Any

from agents.rescue_agent import run as rescue_run
from agents.resource_agent import run as resource_run
from agents.information_agent import run as information_run

# Import centralized environment configuration
from utils.env_config import get_api_key, is_key_available

# Import AI helpers
from utils.ai_helpers import get_cerebras_client, call_cerebras_api

# Initialize Cerebras client
client = get_cerebras_client()

# Local fallback data - duplicate from run_system_test to avoid circular imports
LOCAL_EMERGENCY_CONTACTS = {
    "general": {"name": "Emergency Services", "number": "911"},
    "police": {"name": "Police Department", "number": "911"},
    "fire": {"name": "Fire Department", "number": "911"},
    "medical": {"name": "Emergency Medical Services", "number": "911"},
    "poison": {"name": "Poison Control", "number": "1-800-222-1222"},
    "disaster": {"name": "FEMA Helpline", "number": "1-800-621-3362"},
    "crisis": {"name": "Crisis Text Line", "number": "Text HOME to 741741"},
}

LOCAL_SAFETY_INSTRUCTIONS = {
    "flood": [
        "Move to higher ground immediately",
        "Do not walk through moving water",
        "Do not drive through flooded areas",
        "Follow evacuation orders from authorities"
    ],
    "fire": [
        "Evacuate immediately if authorities order it",
        "Cover nose and mouth with a wet cloth",
        "Test doorknobs and spaces around doors before opening",
        "Use stairs instead of elevators",
        "If trapped, signal for help from a window"
    ],
    "earthquake": [
        "Drop, cover, and hold on",
        "If indoors, stay away from windows",
        "If outdoors, move to a clear area away from buildings",
        "After shaking stops, check for injuries and damage",
        "Be prepared for aftershocks"
    ],
    "hurricane": [
        "Follow evacuation orders from local authorities",
        "Secure your home and property",
        "Have emergency supplies ready",
        "Stay indoors during the storm",
        "Avoid flooded areas during and after the storm"
    ],
    "tornado": [
        "Seek shelter in a basement or interior room on the lowest floor",
        "Stay away from windows and outside walls",
        "Cover your head and neck with arms",
        "If caught outside, lie flat in a nearby ditch or depression",
        "Do not try to outrun a tornado in a vehicle"
    ],
    "general": [
        "Call 911 for immediate life-threatening emergencies",
        "Follow instructions from local authorities",
        "Have emergency supplies prepared",
        "Stay informed through official channels",
        "Help others if you can do so safely"
    ]
}

def extract_json_from_string(text: str) -> Optional[Dict]:
    """
    Extract a JSON object from a string containing JSON.
    
    Args:
        text (str): String that may contain a JSON object
        
    Returns:
        Optional[Dict]: Parsed JSON object or None if extraction fails
    """
    if not text: 
        return None
    
    # Find the first opening brace and last closing brace
    start_brace = text.find('{')
    end_brace = text.rfind('}')
    
    if start_brace == -1 or end_brace == -1: 
        return None
    
    # Extract the JSON string
    json_str = text[start_brace:end_brace+1]
    
    try: 
        return json.loads(json_str)
    except json.JSONDecodeError: 
        return None
        
# Local fallback function implementations to avoid circular imports
def orchestrator_local_process_query(query: str) -> Dict[str, Any]:
    """
    Process a query locally to extract structured information without API calls
    
    Args:
        query: The user's query text
        
    Returns:
        Dict containing structured information about the query
    """
    query_lower = query.lower()
    
    # Initialize with default values
    result = {
        "original_query": query,
        "processed": True,
        "location": None,
        "needs_location_prompt": True,
        "crisis_type": "unknown",
        "urgency_level": "high",
        "specific_requests": [],
        "needs_medical": False,
        "needs_evacuation": False,
        "needs_supplies": False,
        "has_dependents": False,
        "extracted_keywords": [],
        "potential_resources_needed": []
    }
    
    # Extract location with simple pattern matching
    location_patterns = [
        (r'in ([A-Za-z\s]+),\s*([A-Za-z\s]+)', 2),  # "in Austin, Texas" -> groups(1, 2)
        (r'at ([A-Za-z0-9\s]+)', 1),  # "at 123 Main Street" -> group(1)
        (r'near ([A-Za-z\s]+)', 1),  # "near Central Park" -> group(1)
        (r'([A-Za-z\s]+) area', 1),  # "Manhattan area" -> group(1)
    ]
    
    for pattern, group_count in location_patterns:
        match = re.search(pattern, query)
        if match:
            if group_count == 1:
                result["location"] = match.group(1).strip()
            elif group_count == 2:
                result["location"] = f"{match.group(1).strip()}, {match.group(2).strip()}"
            result["needs_location_prompt"] = False
            break
    
    # Detect crisis type
    crisis_keywords = {
        "flood": ["flood", "flooding", "water rising", "submerged"],
        "fire": ["fire", "burning", "flames", "smoke", "wildfire"],
        "earthquake": ["earthquake", "tremor", "shaking", "quake"],
        "hurricane": ["hurricane", "cyclone", "storm", "typhoon"],
        "tornado": ["tornado", "twister", "funnel cloud"],
        "medical": ["injured", "hurt", "medical", "bleeding", "wound", "heart attack", "stroke"],
        "general": ["emergency", "help", "danger", "disaster", "trapped", "stuck"]
    }
    
    for crisis, keywords in crisis_keywords.items():
        if any(keyword in query_lower for keyword in keywords):
            result["crisis_type"] = crisis
            break
    
    # Extract needs
    if any(word in query_lower for word in ["medical", "ambulance", "doctor", "nurse", "injured", "hurt", "wound", "bleeding", "pain"]):
        result["needs_medical"] = True
        result["extracted_keywords"].append("medical")
        result["potential_resources_needed"].append("medical assistance")
    
    if any(word in query_lower for word in ["evacuate", "evacuation", "leave", "escape", "flee", "get out"]):
        result["needs_evacuation"] = True
        result["extracted_keywords"].append("evacuation")
        result["potential_resources_needed"].append("evacuation assistance")
    
    if any(word in query_lower for word in ["water", "food", "supplies", "blankets", "shelter", "clothing"]):
        result["needs_supplies"] = True
        result["extracted_keywords"].append("supplies")
        result["potential_resources_needed"].extend(["food", "water", "shelter"])
    
    if any(word in query_lower for word in ["child", "children", "baby", "elderly", "disabled", "pet", "dog", "cat"]):
        result["has_dependents"] = True
        result["extracted_keywords"].append("dependents")
    
    # Set urgency level based on keywords
    high_urgency_words = ["immediately", "emergency", "urgent", "critical", "life-threatening", "danger", "dying", "trapped"]
    medium_urgency_words = ["soon", "worried", "concerned", "help", "assistance", "need"]
    
    if any(word in query_lower for word in high_urgency_words):
        result["urgency_level"] = "high"
    elif any(word in query_lower for word in medium_urgency_words):
        result["urgency_level"] = "medium"
    else:
        result["urgency_level"] = "low"
    
    return result

def orchestrator_generate_local_response(query: str, query_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a response locally based on the query information
    
    Args:
        query: The user's original query
        query_info: Structured information about the query
        
    Returns:
        Dict containing the response and metadata
    """
    query_lower = query.lower()
    crisis_type = query_info.get("crisis_type", "general")
    location = query_info.get("location", "your area")
    
    # Determine intent based on query patterns
    intent = "information"  # Default intent
    
    if any(word in query_lower for word in ["help", "emergency", "trapped", "hurt", "injured", "danger", "save", "rescue"]):
        intent = "rescue"
    elif any(word in query_lower for word in ["where", "location", "find", "need", "supplies", "resource", "contact", "shelter"]):
        intent = "resource"
    
    # Build response based on intent and crisis type
    response = ""
    structured_data = {}
    
    if intent == "rescue":
        response = f"EMERGENCY RESCUE INFORMATION:\n\n"
        
        if location:
            response += f"For your location ({location}), please follow these safety instructions:\n\n"
        else:
            response += "Please follow these general safety instructions:\n\n"
        
        # Add safety instructions
        safety_instructions = LOCAL_SAFETY_INSTRUCTIONS.get(crisis_type, LOCAL_SAFETY_INSTRUCTIONS["general"])
        for i, instruction in enumerate(safety_instructions, 1):
            response += f"{i}. {instruction}\n"
        
        response += f"\nContact emergency services immediately: {LOCAL_EMERGENCY_CONTACTS['general']['number']}"
        
        structured_data = {
            "emergency_type": crisis_type,
            "location": location,
            "safety_instructions": safety_instructions,
            "emergency_contact": LOCAL_EMERGENCY_CONTACTS['general']
        }
    
    elif intent == "resource":
        response = f"EMERGENCY RESOURCE INFORMATION:\n\n"
        
        if location:
            response += f"For resources in {location}, please contact the following services:\n\n"
        else:
            response += "Please contact the following emergency services:\n\n"
        
        # Add relevant emergency contacts
        relevant_contacts = []
        if crisis_type == "fire":
            relevant_contacts.append(LOCAL_EMERGENCY_CONTACTS["fire"])
        elif query_info.get("needs_medical", False) or "medical" in crisis_type:
            relevant_contacts.append(LOCAL_EMERGENCY_CONTACTS["medical"])
        else:
            relevant_contacts.append(LOCAL_EMERGENCY_CONTACTS["general"])
        
        if "poison" in query_lower:
            relevant_contacts.append(LOCAL_EMERGENCY_CONTACTS["poison"])
        if "disaster" in query_lower:
            relevant_contacts.append(LOCAL_EMERGENCY_CONTACTS["disaster"])
        if "crisis" in query_lower or "mental" in query_lower:
            relevant_contacts.append(LOCAL_EMERGENCY_CONTACTS["crisis"])
        
        for contact in relevant_contacts:
            response += f"- {contact['name']}: {contact['number']}\n"
        
        structured_data = {
            "resource_type": crisis_type,
            "location": location,
            "emergency_contacts": relevant_contacts
        }
    
    else:  # information
        response = f"EMERGENCY INFORMATION:\n\n"
        
        if location:
            response += f"Information for {crisis_type} emergency in {location}:\n\n"
        else:
            response += f"General information for {crisis_type} emergency:\n\n"
        
        # Add general safety instructions based on crisis type
        safety_instructions = LOCAL_SAFETY_INSTRUCTIONS.get(crisis_type, LOCAL_SAFETY_INSTRUCTIONS["general"])
        for i, instruction in enumerate(safety_instructions, 1):
            response += f"{i}. {instruction}\n"
        
        response += f"\nFor more information, contact: {LOCAL_EMERGENCY_CONTACTS['general']['name']} at {LOCAL_EMERGENCY_CONTACTS['general']['number']}"
        
        structured_data = {
            "information_type": crisis_type,
            "location": location,
            "safety_instructions": safety_instructions
        }
    
    # Add a note about using local fallback
    response += "\n\n[Note: This response was generated using local emergency protocols due to connection issues.]"
    
    return {
        "response": response,
        "intent": intent,
        "query_info": query_info,
        "agent_data": structured_data,
        "used_local_fallback": True
    }

async def cerebras_llama_call(prompt: str, update_callback: Optional[Callable[[str, str], None]] = None) -> str:
    """
    Call the Cerebras API using Llama model with improved JSON output format
    
    Args:
        prompt: The prompt to send to the API
        update_callback: Optional callback to update UI
        
    Returns:
        The API response as a string, potentially containing JSON
    """
    if update_callback:
        update_callback("Orchestrator", "Processing with AI...")
    
    try:
        # Use our improved AI helper with retry logic
        modified_prompt = prompt
        
        # Ensure we're asking for JSON output if not already specified
        if "JSON" not in prompt and "json" not in prompt:
            modified_prompt = f"{prompt}\n\nPlease respond with a valid JSON object."
        
        response_text = call_cerebras_api(modified_prompt)
        
        # If the response doesn't look like JSON, try to extract it
        if not response_text.strip().startswith('{'):
            extracted_json = extract_json_from_string(response_text)
            if extracted_json:
                return json.dumps(extracted_json)
        
        return response_text
        
    except Exception as e:
        if update_callback:
            update_callback("Orchestrator", f"Error calling AI: {str(e)}")
        logging.error(f"Error in cerebras_llama_call: {str(e)}")
        
        # In case of errors, return a minimal JSON response
        # For intent classification, default to treating as a potential emergency (safest option)
        if "rescue" in prompt.lower() or "emergency" in prompt.lower():
            return '{"intent": "rescue", "confidence": 90, "reasoning": "Error occurred, defaulting to rescue for safety"}'
        elif "resource" in prompt.lower() or "contact" in prompt.lower():
            return '{"intent": "resource", "confidence": 70, "reasoning": "Error occurred, defaulting to resource based on keywords"}'
        else:
            return '{"intent": "information", "confidence": 50, "reasoning": "Error occurred, defaulting to information"}'

async def process_query(query: str, update_callback: Callable[[str, str], None]) -> Dict[str, Any]:
    """
    Process a user query to extract structured information with fallback to local processing
    
    Args:
        query: The user's query text
        update_callback: Callback function to update the UI with agent activity
        
    Returns:
        Dict containing structured information about the query
    """
    update_callback("Orchestrator", "Extracting structured information from query...")
    
    # Enhanced prompt for better location detection and emergency analysis with stricter JSON output
    prompt = f"""
    Analyze the following emergency query and extract key information.
    Your response MUST be a valid JSON object with EXACTLY these fields and no additional text:
    {{
        "location": "Geographic location mentioned (be as specific as possible, or null if none)",
        "coordinates": {{
            "latitude": "latitude if explicitly mentioned (or null)",
            "longitude": "longitude if explicitly mentioned (or null)"
        }},
        "location_confidence": Number between 0-1 indicating confidence in location detection,
        "needs_location_prompt": Boolean true if location is missing, vague or needed for proper response,
        "crisis_type": "Type of emergency or disaster (flood, fire, earthquake, etc.)",
        "urgency_level": "high", "medium", or "low",
        "specific_requests": ["List of specific things being requested"],
        "needs_medical": Boolean true if medical assistance is needed,
        "needs_evacuation": Boolean true if evacuation assistance is needed,
        "needs_supplies": Boolean true if food/water/supplies are needed,
        "has_dependents": Boolean true if query mentions children, elderly, or others who need help,
        "extracted_keywords": ["List of key terms extracted from the query"],
        "potential_resources_needed": ["List of resources that might be needed based on the crisis"]
    }}
    
    Query: "{query}"
    
    JSON Response:
    """
    
    try:
        # Use our improved AI helper with retry logic
        response_text = await cerebras_llama_call(prompt, update_callback)
        
        try:
            # Try to parse as JSON directly
            extracted_info = json.loads(response_text)
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from the string
            extracted_info = extract_json_from_string(response_text)
            if not extracted_info:
                # If we still can't get a valid response, fall back to local processing
                update_callback("Orchestrator", "Failed to parse API response. Falling back to local processing.")
                return orchestrator_local_process_query(query)
        
        # Add metadata to the response
        extracted_info["original_query"] = query
        extracted_info["processed"] = True
        extracted_info["timestamp"] = time.time()
        
        # Enhanced location handling
        if not extracted_info.get("location") or extracted_info.get("location") == "null":
            extracted_info["location"] = None
            extracted_info["needs_location_prompt"] = True
            update_callback("Orchestrator", "No location detected - will prompt user for location")
        elif extracted_info.get("location_confidence", 0) < 0.5:
            extracted_info["needs_location_prompt"] = True
            update_callback("Orchestrator", f"Low confidence in detected location: {extracted_info.get('location')} - will confirm with user")
        else:
            update_callback("Orchestrator", f"Location identified: {extracted_info.get('location')}")
        
        # Log structured data
        update_callback("Orchestrator", f"Crisis type: {extracted_info.get('crisis_type')} - Urgency: {extracted_info.get('urgency_level')}")
        
        return extracted_info
    
    except Exception as e:
        update_callback("Orchestrator", f"Error extracting structured information: {str(e)}")
        logging.error(f"Query processing error: {str(e)}")
        logging.error(traceback.format_exc())
        
        # Use local processing as fallback
        update_callback("Orchestrator", "Falling back to local query processing.")
        return orchestrator_local_process_query(query)

async def route_query(query: str, update_callback: Callable[[str, str], None]) -> Dict:
    """
    Route the user query to the appropriate specialist agent based on intent
    with fallback to local processing if API calls fail
    
    Args:
        query: The user's query text
        update_callback: Callback function to update the UI with agent activity
    
    Returns:
        Dict containing the structured response and metadata
    """
    use_local_fallback = False
    query_info = None
    
    # Step 1: Process the query to extract structured information
    try:
        # Try with API first
        query_info = await process_query(query, update_callback)
    except Exception as process_error:
        # Fall back to local processing if API call fails
        update_callback("Orchestrator", f"API connection error: {str(process_error)}. Using local fallback.")
        use_local_fallback = True
        
        # Use local processing function defined in orchestrator
        query_info = orchestrator_local_process_query(query)
    
    # If we're using local fallbacks and we've successfully processed the query
    if use_local_fallback and query_info:
        update_callback("Orchestrator", "Local fallback activated: Processing query locally.")
        result = orchestrator_generate_local_response(query, query_info)
        return result
    
    # Check if we need to request location data
    if query_info.get("needs_location_prompt", False) and not query_info.get("location"):
        update_callback("Orchestrator", "Location information needed for this request.")
        return {
            "response": "I need to know your location to help with this request. Can you share your current location?",
            "needs_location": True,
            "query_info": query_info,
            "intent": "pending_location"
        }
    
    # Step 2: Classify the user's intent with structured JSON output
    intent_prompt = f"""
    Analyze the following emergency query and classify its primary intent as one of these categories.
    Return your answer as a JSON object with the following structure:
    {{
        "intent": "rescue|resource|information",
        "confidence": 0-100,
        "reasoning": "brief explanation of classification"
    }}
    
    Where:
    - "rescue": User needs immediate life-saving assistance
    - "resource": User needs to locate specific resources/contacts
    - "information": User is seeking general information or status updates
    
    Query: "{query}"
    Location: {query_info.get('location', 'Unknown')}
    Crisis Type: {query_info.get('crisis_type', 'Unknown')}
    
    JSON Response:
    """
    
    intent = "information"  # Default intent if all else fails
    intent_data = {"intent": "information", "confidence": 60, "reasoning": "Default classification due to API issue"}
    
    try:
        # Call Cerebras API for intent classification
        intent_response = await cerebras_llama_call(intent_prompt, update_callback)
        
        try:
            intent_data = json.loads(intent_response)
            intent = intent_data.get("intent", "information")  # Default to information if parsing fails
        except (json.JSONDecodeError, TypeError):
            # Fallback if response isn't valid JSON
            intent = "information"
            update_callback("Orchestrator", "Warning: Could not parse intent classification. Defaulting to Information Agent.")
    except Exception as intent_error:
        # Fall back to local intent classification if API call fails
        update_callback("Orchestrator", f"Intent classification API error: {str(intent_error)}. Using local intent classification.")
        
        # Simple keyword-based intent classification
        lower_query = query.lower()
        if any(word in lower_query for word in ["help", "emergency", "trapped", "hurt", "injured", "danger", "save", "rescue"]):
            intent = "rescue"
            intent_data = {"intent": "rescue", "confidence": 70, "reasoning": "Local classification based on emergency keywords"}
        elif any(word in lower_query for word in ["where", "location", "find", "need", "supplies", "resource", "contact", "shelter"]):
            intent = "resource"
            intent_data = {"intent": "resource", "confidence": 70, "reasoning": "Local classification based on resource keywords"}
        else:
            intent = "information"
            intent_data = {"intent": "information", "confidence": 70, "reasoning": "Local classification defaulting to information"}
    
    # Update the UI
    update_callback("Orchestrator", f"Intent classified as {intent.upper()} with {intent_data.get('confidence', 'unknown')}% confidence. Activating {intent.capitalize()} Agent.")
    
    # Step 3: Route to the appropriate specialist agent
    try:
        response = None
        
        # Try specialized agent with API first
        try:
            if intent == "rescue":
                response = await rescue_run(query, update_callback, query_info)
            elif intent == "resource":
                response = await resource_run(query, update_callback, query_info)
            else:  # information
                response = await information_run(query, update_callback, query_info)
                
        except Exception as agent_error:
            # Fall back to local processing if specialized agent fails
            update_callback("Orchestrator", f"Error in {intent.capitalize()} Agent API: {str(agent_error)}. Using local fallback.")
            
            # If we haven't done local processing yet, do it now
            if not use_local_fallback:
                query_info = orchestrator_local_process_query(query)
                
            # Generate a local response based on the intent
            local_response = orchestrator_generate_local_response(query, query_info)
            
            # Mark that we're using a local response
            local_response["used_local_fallback"] = True
            local_response["intent"] = intent
            local_response["query_info"] = query_info
            
            return local_response
        
        # Combine agent response with metadata
        return {
            "response": response.get("response") if isinstance(response, dict) else response,
            "intent": intent,
            "query_info": query_info,
            "agent_data": response.get("data") if isinstance(response, dict) else None,
            "used_local_fallback": use_local_fallback
        }
    except Exception as e:
        update_callback("Orchestrator", f"Error in {intent.capitalize()} Agent: {str(e)}")
        
        # Try local fallback as last resort
        try:
            if not query_info:
                query_info = orchestrator_local_process_query(query)
                
            local_response = orchestrator_generate_local_response(query, query_info)
            local_response["intent"] = intent
            local_response["query_info"] = query_info
            local_response["used_local_fallback"] = True
            local_response["error"] = str(e)
            
            update_callback("Orchestrator", "Successfully generated fallback response.")
            return local_response
            
        except Exception as fallback_error:
            # Create a comprehensive error message with emergency instructions if all else fails
            error_message = f"""
            I apologize, but I encountered an error while processing your request: {str(e)}. 
            
            If this is a life-threatening emergency, please immediately contact your local emergency services:
            - In most countries, dial 911 or 112 for emergency services
            - If possible, provide clear details about your location and situation
            
            Please try again with your request in a moment.
            """.strip()
            
            # Return error response with metadata
            return {
                "response": error_message,
                "intent": intent,
                "query_info": query_info,
                "error": f"{str(e)}. Fallback also failed: {str(fallback_error)}",
                "is_error": True,
                "used_local_fallback": False
            }
