import asyncio
import json
import time
from typing import Callable, Dict, List, Optional, Any

# Import centralized environment configuration
from utils.env_config import get_api_key, is_key_available

# Import AI helpers
from utils.ai_helpers import get_cerebras_client, call_cerebras_api

# Initialize Cerebras client
client = get_cerebras_client()

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

async def ask_ai(prompt: str, model: str = "llama-4-scout-17b-16e-instruct", update_callback: Optional[Callable[[str, str], None]] = None) -> Optional[str]:
    """
    Make a call to the AI model to process the given prompt.
    
    Args:
        prompt (str): The prompt to send to the AI
        model (str): The model identifier to use
        update_callback: Optional callback to update UI
        
    Returns:
        Optional[str]: The AI's response or None if the call fails
    """
    try:
        if update_callback:
            update_callback("Information Agent", "Processing with AI...")
            
        if client is None:
            # No client available, provide minimal response
            return None
        
        # Make the API call
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}], 
            model=model, 
            max_tokens=1024, 
            temperature=0.1
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        if update_callback:
            update_callback("Information Agent", f"Error in AI processing: {e}")
        return None

async def get_weather_alerts(lat: float, lon: float) -> Dict[str, Any]:
    """Get weather alerts for specific coordinates"""
    try:
        # In a real implementation, this would call a weather API
        # For example, using the National Weather Service API for US locations:
        # url = f"https://api.weather.gov/points/{lat},{lon}"
        # response = requests.get(url)
        # data = response.json()
        # forecast_url = data["properties"]["forecast"]
        # forecast_response = requests.get(forecast_url)
        # return forecast_response.json()
        
        # Default response for when API is not available
        return {
            "location": f"{lat},{lon}",
            "alerts": [],
            "forecast": {
                "next_24_hours": "Weather information unavailable. Please check local weather services.",
                "next_48_hours": "Weather information unavailable. Please check local weather services."
            }
        }
    except Exception as e:
        return {
            "error": f"Failed to get weather data: {str(e)}",
            "alerts": []
        }

async def get_evacuation_routes(lat: float, lon: float) -> List[Dict[str, Any]]:
    """Get evacuation routes for specific coordinates"""
    try:
        # In a real implementation, this would call an evacuation API or database
        # For example:
        # url = f"https://api.example.org/evacuation-routes?lat={lat}&lon={lon}"
        # response = requests.get(url)
        # return response.json()["routes"]
        
        # Default response for when API is not available
        return [
            {
                "name": "Primary Evacuation Route",
                "status": "Unknown",
                "description": "Please contact local authorities for current evacuation routes",
                "closure_points": []
            }
        ]
    except Exception as e:
        return [
            {
                "name": "Error",
                "status": "Error",
                "description": f"Failed to get evacuation routes: {str(e)}",
                "closure_points": []
            }
        ]

async def get_emergency_shelter_locations(lat: float, lon: float) -> List[Dict[str, Any]]:
    """Get emergency shelter locations for specific coordinates"""
    try:
        # In a real implementation, this would call a shelter API or database
        # For example:
        # url = f"https://api.example.org/emergency-shelters?lat={lat}&lon={lon}&radius=25"
        # response = requests.get(url)
        # return response.json()["shelters"]
        
        # Default response for when API is not available
        return [
            {
                "name": "Local Emergency Shelter",
                "address": "Please contact local authorities for current shelter locations",
                "status": "Unknown",
                "amenities": []
            }
        ]
    except Exception as e:
        return [
            {
                "name": "Error",
                "status": "Error",
                "address": f"Failed to get shelter locations: {str(e)}"
            }
        ]

async def extract_location_from_query(query: str, update_callback: Callable[[str, str], None]) -> Dict[str, Any]:
    """
    Extract location information from a query using AI
    
    Args:
        query: The user's query
        update_callback: Callback function for UI updates
        
    Returns:
        Dict with location information including coordinates
    """
    update_callback("Information Agent", "Extracting location from query...")
    
    # Try to extract location with AI if available
    if client is not None:
        location_prompt = f"""
        Analyze the following query and extract location information.
        Return ONLY a JSON object with keys:
        - "location_name": The name of the location mentioned
        - "lat": The approximate latitude as a float
        - "lon": The approximate longitude as a float
        
        Query: "{query}"
        """
        
        location_str = await ask_ai(location_prompt, update_callback=update_callback)
        if location_str:
            location_info = extract_json_from_string(location_str)
            if location_info and 'lat' in location_info and 'lon' in location_info:
                return location_info
    
    # Fallback if AI extraction fails or is unavailable
    # In a real implementation, this would use geocoding APIs
    # For now, simple keyword matching
    lower_query = query.lower()
    if "punjab" in lower_query:
        return {
            "location_name": "Punjab, India",
            "lat": 31.1471, 
            "lon": 75.3412
        }
    elif any(word in lower_query for word in ["houston", "texas"]):
        return {
            "location_name": "Houston, Texas, USA",
            "lat": 29.7604,
            "lon": -95.3698
        }
    elif "miami" in lower_query:
        return {
            "location_name": "Miami, Florida, USA",
            "lat": 25.7617,
            "lon": -80.1918
        }
    else:
        return {
            "location_name": "Unknown Location",
            "lat": 0.0,
            "lon": 0.0
        }

async def generate_information_response(query: str, location_data: Dict[str, Any], 
                                      all_results: List[Dict[str, Any]],
                                      update_callback: Callable[[str, str], None]) -> Dict:
    """
    Generate a coherent information response using AI if available
    
    Args:
        query: Original user query
        location_data: Location information
        all_results: Results from various information sources
        update_callback: Callback function for UI updates
        
    Returns:
        Dict containing the formatted response and structured data
    """
    update_callback("Information Agent", "Synthesizing information response...")
    
    # Prepare structured data for the response
    structured_data = {
        "location": location_data.get("location_name"),
        "coordinates": location_data.get("coordinates", {}),
        "timestamp": time.time(),
        "data_sources": all_results
    }
    
    if client is not None:
        # Format the collected data for AI
        data_str = json.dumps(all_results, indent=2)
        
        synthesis_prompt = f"""
        You are an AI assistant named C.L.A.R.I.O.N., helping during a climate emergency.
        Generate a clear, informative response based on the following information:
        
        USER QUERY: "{query}"
        
        LOCATION: {location_data['location_name']} (Coordinates: {location_data['lat']}, {location_data['lon']})
        
        COLLECTED DATA:
        {data_str}
        
        Format your response as a helpful information brief with clear sections for:
        - Weather alerts (if any)
        - Evacuation routes (if available)
        - Shelter information (if available)
        - Safety recommendations
        
        Keep your response factual and actionable. If information is missing, acknowledge that.
        """
        
        ai_response = await ask_ai(synthesis_prompt, update_callback=update_callback)
        if ai_response:
            return ai_response
    
    # Fallback if AI is unavailable or fails
    response_parts = [f"Here's the latest information for {location_data['location_name']}:"]
    
    # Manually format the collected data
    for result in all_results:
        if isinstance(result, dict) and "alerts" in result:
            # Weather data
            weather_data = result
            if weather_data.get("alerts"):
                response_parts.append("\nACTIVE WEATHER ALERTS:")
                for alert in weather_data["alerts"]:
                    alert_type = alert.get("type", "Alert")
                    severity = alert.get("severity", "Unknown")
                    description = alert.get("description", "No details available")
                    response_parts.append(f"- {alert_type} ({severity}): {description}")
            
            if "forecast" in weather_data:
                response_parts.append("\nWEATHER FORECAST:")
                forecast = weather_data.get("forecast", {})
                if "next_24_hours" in forecast:
                    response_parts.append(f"- Next 24 hours: {forecast['next_24_hours']}")
                if "next_48_hours" in forecast:
                    response_parts.append(f"- Next 48 hours: {forecast['next_48_hours']}")
        
        elif isinstance(result, list):
            if result and "status" in result[0] and "closure_points" in result[0]:
                # Evacuation routes
                routes = result
                response_parts.append("\nEVACUATION ROUTES:")
                for route in routes:
                    name = route.get("name", "Unnamed Route")
                    status = route.get("status", "Unknown")
                    desc = route.get("description", "No description available")
                    status_str = f" ({status})" if status != "Open" else ""
                    response_parts.append(f"- {name}{status_str}: {desc}")
                    
                    closures = route.get("closure_points", [])
                    for closure in closures:
                        response_parts.append(f"  * CLOSURE: {closure}")
            
            elif result and "address" in result[0]:
                # Shelter information
                shelters = result
                response_parts.append("\nEMERGENCY SHELTERS:")
                for shelter in shelters:
                    name = shelter.get("name", "Unnamed Shelter")
                    address = shelter.get("address", "Address unknown")
                    status = shelter.get("status", "")
                    status_str = f" ({status})" if status else ""
                    
                    response_parts.append(f"- {name}{status_str}")
                    response_parts.append(f"  Address: {address}")
                    
                    if "capacity" in shelter:
                        response_parts.append(f"  Capacity: {shelter['capacity']}")
                    
                    amenities = shelter.get("amenities", [])
                    if amenities:
                        response_parts.append(f"  Amenities: {', '.join(amenities)}")
    
    # Add a safety recommendation
    response_parts.append("\nSAFETY RECOMMENDATION:")
    response_parts.append("Please follow all instructions from local authorities and stay tuned to official communication channels for updates.")
    
    response_text = "\n".join(response_parts)
    
    # Return both the formatted text response and structured data
    return {
        "response": response_text,
        "data": structured_data,
        "info_type": "emergency_information",
        "location": location_data.get("location_name"),
        "has_weather_data": any("weather" in str(r).lower() for r in all_results),
        "has_evacuation_data": any("evacuation" in str(r).lower() for r in all_results),
        "has_shelter_data": any("shelter" in str(r).lower() for r in all_results)
    }

async def run(query: str, update_callback: Callable[[str, str], None], query_info: Optional[Dict] = None) -> Dict:
    """
    Main function for the Information Agent
    
    Args:
        query: The user's query text
        update_callback: Callback function to update the UI with agent activity
        query_info: Structured query information from the orchestrator (optional)
    
    Returns:
        Dict containing the response and structured data
    """
    # Use query_info if available, otherwise extract location from the query
    if query_info and query_info.get('location'):
        update_callback("Information Agent", f"Using provided location: {query_info['location']}")
        location_data = {
            'location_name': query_info['location'],
            'coordinates': query_info.get('coordinates', {})
        }
    else:
        update_callback("Information Agent", "Analyzing query to identify location...")
        location_data = await extract_location_from_query(query, update_callback)
    
    # Step 2: Determine what information the user needs
    update_callback("Information Agent", f"Determining what information is needed for {location_data['location_name']}...")
    
    # Analyze the query with AI if available
    info_needs = set(["weather", "evacuation", "shelter"])  # Default to all
    
    if client is not None:
        needs_prompt = f"""
        Analyze this query and determine what information the user needs.
        Return ONLY a JSON object with boolean keys: "weather", "evacuation", "shelter"
        
        Query: "{query}"
        """
        
        needs_str = await ask_ai(needs_prompt, update_callback=update_callback)
        if needs_str:
            needs_info = extract_json_from_string(needs_str)
            if needs_info:
                info_needs = set()
                if needs_info.get("weather", True):
                    info_needs.add("weather")
                if needs_info.get("evacuation", True):
                    info_needs.add("evacuation")
                if needs_info.get("shelter", True):
                    info_needs.add("shelter")
    
    # If AI is not available, use simple keyword matching
    if client is None:
        lower_query = query.lower()
        info_needs = set()
        
        if any(word in lower_query for word in ["weather", "forecast", "flood", "rain", "storm", "alert"]):
            info_needs.add("weather")
        
        if any(word in lower_query for word in ["evacuation", "evacuate", "route", "road", "path", "escape"]):
            info_needs.add("evacuation")
        
        if any(word in lower_query for word in ["shelter", "safe", "safety", "camp", "stay"]):
            info_needs.add("shelter")
        
        # If no specific needs identified, get all types
        if not info_needs:
            info_needs = {"weather", "evacuation", "shelter"}
    
    # Step 3: Fetch all the requested information in parallel
    update_callback("Information Agent", "Retrieving up-to-date information...")
    tasks = []
    
    lat, lon = location_data.get("lat", 0), location_data.get("lon", 0)
    
    if "weather" in info_needs:
        tasks.append(asyncio.create_task(get_weather_alerts(lat, lon)))
    
    if "evacuation" in info_needs:
        tasks.append(asyncio.create_task(get_evacuation_routes(lat, lon)))
    
    if "shelter" in info_needs:
        tasks.append(asyncio.create_task(get_emergency_shelter_locations(lat, lon)))
    
    all_results = await asyncio.gather(*tasks)
    
    # Step 4: Generate a comprehensive response
    return await generate_information_response(query, location_data, all_results, update_callback)
