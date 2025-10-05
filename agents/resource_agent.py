import asyncio
import re
import json
import time
from typing import Callable, Dict, List, Optional, Union, Any

try:
    from crawl4ai import AsyncWebCrawler
except ImportError:
    print("Warning: crawl4ai not installed. Install with 'pip install crawl4ai'")
    AsyncWebCrawler = None

# Import centralized environment configuration
from utils.env_config import get_api_key, is_key_available

try:
    from exa_py import Exa
    # Initialize Exa client if API key available
    exa = None
    if is_key_available('EXA_API_KEY'):
        exa = Exa(api_key=get_api_key('EXA_API_KEY'))
except ImportError:
    print("Warning: exa-py not installed. Install with 'pip install exa-py'")
    exa = None

try:
    from cerebras.cloud.sdk import Cerebras
    # Initialize Cerebras client if API key available
    client = None
    if is_key_available('CEREBRAS_API_KEY'):
        client = Cerebras(api_key=get_api_key('CEREBRAS_API_KEY'))
except ImportError:
    print("Warning: cerebras-cloud-sdk not installed. Install with 'pip install cerebras-cloud-sdk'")
    client = None

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
            update_callback("Resource Agent", "Processing with AI...")
            
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
            update_callback("Resource Agent", f"Error in AI processing: {e}")
        return None

def extract_contacts_from_markdown(markdown_text: str) -> Dict[str, List[str]]:
    """
    Enhanced function to extract contact information (phone, emergency phone, email, address) 
    from markdown text using regular expressions.
    
    Args:
        markdown_text (str): The markdown text from a crawled webpage
        
    Returns:
        Dict[str, List[str]]: Dictionary with contact information by type
    """
    extracted_contacts = {
        "phone": [],
        "emergency_phone": [],
        "email": [],
        "address": []
    }
    
    if not markdown_text:
        return extracted_contacts
    
    # --- Emergency Phone Number Extraction ---
    # Look for keywords like 'emergency', 'hotline', 'urgent', '24/7', 'rescue' near phone patterns
    emergency_phone_pattern = re.compile(
        r'(?:emergency|hotline|urgent|24\/7|rescue)[-.\s]*:?[-.\s]*' # Look for keywords followed by optional separators
        r'(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})' # Common US format
        r'|(?:\+\d{1,3}[-.\s]?)?(?:\(?\d{1,4}\)?[-.\s]?)?[\d\s-]{7,18}(?:\s*(?:ext|x|#)\.?\s*\d{1,5})?' # More general global
        r'|\[.*?\]\(tel:([\d\s\+\(\)-]+)\)', # Markdown tel: link
        re.IGNORECASE # Pass flags as positional argument
    )
    emergency_matches = emergency_phone_pattern.findall(markdown_text)
    cleaned_emergency_phones = []
    for match in emergency_matches:
        phone_str = match[0] if isinstance(match, tuple) and len(match) > 0 and match[0] else ''.join(match)
        cleaned_phone = re.sub(r'[-.\s\(\)]', '', phone_str).strip()
        if len(re.sub(r'\D', '', cleaned_phone)) >= 7:
            cleaned_emergency_phones.append(cleaned_phone)
    extracted_contacts["emergency_phone"] = list(dict.fromkeys(cleaned_emergency_phones))

    # --- Standard Phone Number Extraction ---
    # Use the general pattern, but exclude those already found as emergency
    phone_pattern = re.compile(
        r'(?<!\d{4}[-.\s])' # Avoid preceding 4 digits and separator (like in YYYY-MM-DD)
        r'(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})' # Common US format (###) ###-#### or ###-###-####
        r'|(?:\+\d{1,3}[-.\s]?)?(?:\(?\d{1,4}\)?[-.\s]?)?[\d\s-]{7,18}(?:\s*(?:ext|x|#)\.?\s*\d{1,5})?' # More general global
        r'|\[.*?\]\(tel:([\d\s\+\(\)-]+)\)' # Markdown tel: link, capture number inside tel:
        r'(?![-.\s]\d{2})' # Avoid trailing separator and 2 digits (like in MM-DD)
        r'(?!\s*(?:BC|AD)\b)' # Avoid trailing BC/AD
        r'(?!\s*(?:(?:19|20)\d{2}))', # Avoid trailing 4-digit years
        re.IGNORECASE # Pass flags as positional argument
    )
    phone_matches = phone_pattern.findall(markdown_text)
    cleaned_phones = []
    for match in phone_matches:
        phone_str = match[0] if isinstance(match, tuple) and len(match) > 0 and match[0] else ''.join(match)
        cleaned_phone = re.sub(r'[-.\s\(\)]', '', phone_str).strip()
        if (len(re.sub(r'\D', '', cleaned_phone)) >= 7 and 
            not (re.fullmatch(r'\d{4}', cleaned_phone) or re.fullmatch(r'\d{6}', cleaned_phone))):
            # Exclude numbers already found as emergency phones
            if cleaned_phone not in extracted_contacts["emergency_phone"]:
                cleaned_phones.append(cleaned_phone)
    
    extracted_contacts["phone"] = list(dict.fromkeys(cleaned_phones))
    
    # --- Email Extraction ---
    # Standard email regex
    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', re.IGNORECASE)
    extracted_contacts["email"] = list(dict.fromkeys(email_pattern.findall(markdown_text)))
    
    # --- Address Extraction (Improved Multi-line Handling & Validation) ---
    address_candidates = []
    lines = markdown_text.split('\n')
    for line in lines:
        cleaned_line = line.strip()
        # Heuristic: look for lines with a number followed by a word, OR common address keywords, OR postal codes, OR PO Box
        if (re.search(r'^\d+\s+\w+', cleaned_line) or # Starts with number and space (street number)
            re.search(r'\b(St|Ave|Rd|Blvd|Ln|Cir|Dr|Ct|Pl|Sq|Street|Avenue|Road|Boulevard|Lane|Circle|Drive|Court|Place|Square)\b', cleaned_line, re.IGNORECASE) or # Common street types
            re.search(r'\b\d{5}(?:-\d{4})?\b', cleaned_line) or # US Zip code
            re.search(r'\b[A-Za-z]\d[A-Za-z]\s*\d[A-Za-z]\d\b', cleaned_line) or # Canadian Postal Code (basic)
            re.search(r'\b(PO Box|P.O. Box)\b', cleaned_line, re.IGNORECASE) or # PO Box
            re.search(r'^\*\*\w+\s+Address\*\*', cleaned_line, re.IGNORECASE) # Pattern like **Physical Address**
        ):
            address_candidates.append(cleaned_line)
        # Add the else if condition here - check if the previous line was an address candidate
        elif address_candidates and cleaned_line and not re.fullmatch(r'[-*\s]+', cleaned_line):
            # Add line if it seems to continue the block (e.g., starts with alphanumeric or is just text)
            if re.search(r'^\w', cleaned_line) or re.search(r'[A-Za-z]\b', cleaned_line):
                address_candidates.append(cleaned_line)
    
    # Join consecutive likely address lines into potential full addresses
    compiled_addresses = []
    current_block = []
    # Iterate through address_candidates to group consecutive lines
    for line in address_candidates:
        # Simple heuristic: if the line is not empty and not just markdown list markers
        if line and not re.fullmatch(r'[-*\s]+', line):
            # If this is the first line in a block or the previous line wasn't just whitespace/markers, add it
            if not current_block or (current_block and current_block[-1].strip()): # Check if the last line wasn't just whitespace
                current_block.append(line)
            else: # If the previous line was just whitespace/markers, start a new block
                if current_block:
                    compiled_addresses.append(" ".join(current_block))
                current_block = [line]
        else:
            # If line is empty or just markers, finalize the current block
            if current_block:
                compiled_addresses.append(" ".join(current_block))
            current_block = [] # Start a new block
    
    if current_block: # Add the last block if any
        compiled_addresses.append(" ".join(current_block))
    
    # Further refinement: Filter out very short or unlikely addresses, remove duplicates
    final_addresses = []
    for addr in compiled_addresses:
        # Simple split heuristic: split if a long sequence of non-address-like text is found
        parts = re.split(r'\s{10,}', addr) # Split on large gaps of whitespace
        for part in parts:
            cleaned_part = part.strip()
            # Basic validation: must contain a number/PO Box/Canadian PC and be long enough
            if len(cleaned_part) > 15 and (re.search(r'\d+\s+\w+', cleaned_part) or 
                                          re.search(r'\b(PO Box|P.O. Box)\b', cleaned_part, re.IGNORECASE) or 
                                          re.search(r'\b[A-Za-z]\d[A-Za-z]\s*\d[A-Za-z]\d\b', cleaned_part)):
                final_addresses.append(cleaned_part)
    
    extracted_contacts["address"] = list(dict.fromkeys(final_addresses))
    return extracted_contacts

async def crawl_and_extract_contacts_HYBRID(url: str, update_callback: Optional[Callable[[str, str], None]] = None) -> Dict[str, Any]:
    """
    Advanced hybrid approach to crawl a webpage and extract contact information.
    Uses both regex-based and AI-powered extraction for more reliable results.
    
    Args:
        url (str): URL to crawl
        update_callback (Optional[Callable[[str, str], None]]): Callback to update UI with status
        
    Returns:
        Dict[str, Any]: Dictionary with extracted contact information
    """
    if update_callback:
        update_callback("Resource Agent", f"Crawling URL: {url}")
    
    try:
        # Step 1: Crawl the webpage
        if AsyncWebCrawler is None:
            if update_callback:
                update_callback("Resource Agent", "Error: crawl4ai not installed. Unable to crawl websites.")
            return {"error": "crawl4ai not installed"}
            
        async with AsyncWebCrawler() as crawler:
            if update_callback:
                update_callback("Resource Agent", f"Initiating crawl for {url}")
            
            result = await crawler.arun(url, text={"max_characters": 8000})
            
            if not result or not result.markdown:
                if update_callback:
                    update_callback("Resource Agent", f"Crawl returned no content from {url}")
                return {"error": "No content found"}
            
            markdown_content = result.markdown
            
            # Step 2: Extract contacts using regex
            if update_callback:
                update_callback("Resource Agent", "Extracting contacts using pattern matching...")
            
            contacts = extract_contacts_from_markdown(markdown_content)
            
            # Step 3: If regex found insufficient contacts, fall back to AI extraction
            if not contacts.get("phone") and not contacts.get("email") and not contacts.get("emergency_phone"):
                if update_callback:
                    update_callback("Resource Agent", "Pattern matching found insufficient contacts, falling back to AI extraction...")
                
                # Use AI for extraction if available
                if client is not None:
                    ai_extraction_prompt = f"""
                    Analyze the following webpage content for contact information.
                    Explicitly look for:
                    - Standard Phone Number(s)
                    - Emergency Contact Number(s) (look for terms like 'emergency', 'hotline', 'urgent', '24/7', 'rescue' nearby)
                    - Email Address(es)
                    - Physical Address(es)
                    
                    Format the output strictly as a JSON object with keys "phone" (list of strings), 
                    "emergency_phone" (list of strings), "email" (list of strings), and 
                    "address" (list of strings). If no information is found for a category, 
                    the value should be an empty list [].
                    
                    Return ONLY the JSON object and nothing else.
                    
                    Webpage Content from {url}:
                    {markdown_content[:6000]}  # Pass a significant portion to the AI
                    """
                    
                    # Call AI for extraction
                    ai_extracted_str = await ask_ai(ai_extraction_prompt, update_callback=update_callback)
                    if ai_extracted_str:
                        ai_extracted = extract_json_from_string(ai_extracted_str)
                        
                        if ai_extracted:
                            if update_callback:
                                update_callback("Resource Agent", "AI extraction successful")
                            # Combine results, prioritizing AI since regex was empty
                            return ai_extracted
            
            return contacts
            
    except Exception as e:
        if update_callback:
            update_callback("Resource Agent", f"Error crawling {url}: {str(e)}")
        return {"error": str(e)}

async def search_web(query: str, num_results: int = 3, update_callback: Optional[Callable[[str, str], None]] = None) -> List[Dict[str, str]]:
    """
    Search the web for information related to the query.
    
    Args:
        query (str): Search query
        num_results (int): Number of results to return
        update_callback: Optional callback to update UI
        
    Returns:
        List[Dict[str, str]]: List of search results or empty list if search fails
    """
    try:
        if update_callback:
            update_callback("Resource Agent", f"Searching for: '{query}'")
            
        if exa is None:
            if update_callback:
                update_callback("Resource Agent", "Warning: exa-py not installed. Unable to search the web.")
            return []
        
        # Make the actual API call
        search_result = exa.search_and_contents(
            query, 
            type="auto", 
            num_results=num_results, 
            text={"max_characters": 2000}
        )
        
        # Format results in a consistent way
        results = []
        for result in search_result.results:
            results.append({
                "title": result.title,
                "url": result.url,
                "snippet": result.text[:200] if hasattr(result, 'text') else ""
            })
        
        return results
    
    except Exception as e:
        if update_callback:
            update_callback("Resource Agent", f"Error searching the web: {e}")
        return []

async def crawl_and_extract_contacts_all_urls(urls: List[str], update_callback: Callable[[str, str], None]) -> Dict[str, Dict[str, Any]]:
    """
    Advanced version: Crawls ALL provided URLs and extracts contact info from each.
    Uses a hybrid approach with both regex and AI-based extraction.
    
    Args:
        urls (List[str]): List of URLs to crawl
        update_callback: Callback to update UI
        
    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of extracted contacts keyed by URL
    """
    if not urls:
        return {}
    
    update_callback("Resource Agent", f"Crawling {len(urls)} URLs for contact information...")
    
    # Store extracted contacts per URL
    extracted_contacts_by_url = {}
    
    for url in urls:
        contacts = await crawl_and_extract_contacts_HYBRID(url, update_callback)
        extracted_contacts_by_url[url] = contacts
    
    update_callback("Resource Agent", "Contact extraction complete")
    return extracted_contacts_by_url

async def run(query_or_urls: Union[str, List[str]], update_callback: Callable[[str, str], None], query_info: Optional[Dict] = None, is_subroutine: bool = False) -> Union[Dict, Dict[str, Dict[str, Any]]]:
    """
    Main function for the Resource Agent
    
    Args:
        query_or_urls: Either a user query string or a list of URLs to crawl
        update_callback: Callback function to update the UI with agent activity
        is_subroutine: Whether this agent is being called as a subroutine by another agent
    
    Returns:
        If is_subroutine is True: Returns the raw contact data by URL
        If is_subroutine is False: Returns a formatted response string for the user
    """
    # Handle different input types
    if isinstance(query_or_urls, str):
        # This is a direct user query, we need to find relevant websites first
        query = query_or_urls
        update_callback("Resource Agent", "Searching for relevant resources...")
        
        # Use Exa API for intelligent web search
        web_results = await search_web(query, num_results=3, update_callback=update_callback)
        
        if not web_results:
            if is_subroutine:
                return {}
            return "I couldn't find any specific resources for your query. Please try again with more details about your location and the type of emergency."
        
        urls = [result['url'] for result in web_results]
    else:
        # We were given URLs directly by another agent
        urls = query_or_urls
    
    # Crawl all URLs and extract contacts
    all_contacts_by_url = await crawl_and_extract_contacts_all_urls(urls, update_callback)
    
    # If this is a subroutine call, return the raw data
    if is_subroutine:
        return all_contacts_by_url
    
    # Otherwise, format a nice response for the user
    update_callback("Resource Agent", "Synthesizing resource information for user...")
    
    response_parts = ["Here are the emergency contacts I found for you:"]
    
    # Process and format the contacts for display
    for url, contact_info in all_contacts_by_url.items():
        # Add a section for each URL
        if "error" in contact_info:
            # Skip URLs that failed
            continue
        
        # Find the source title from web results
        source_title = url
        for result in urls if isinstance(urls, list) else []:
            if result.get('url') == url:
                source_title = result.get('title', url)
                break
        
        # Add a divider for each website
        response_parts.append(f"\n--- Contacts from {source_title} ---")
        
        # Add emergency phones with priority
        if contact_info.get("emergency_phone"):
            response_parts.append("\nEMERGENCY NUMBERS:")
            for phone in contact_info["emergency_phone"]:
                response_parts.append(f"- {phone}")
        
        # Add regular phones
        if contact_info.get("phone"):
            response_parts.append("\nOTHER CONTACT NUMBERS:")
            for phone in contact_info["phone"]:
                response_parts.append(f"- {phone}")
        
        # Add emails
        if contact_info.get("email"):
            response_parts.append("\nEMAIL CONTACTS:")
            for email in contact_info["email"]:
                response_parts.append(f"- {email}")
        
        # Add addresses
        if contact_info.get("address"):
            response_parts.append("\nPHYSICAL LOCATIONS:")
            for address in contact_info["address"]:
                response_parts.append(f"- {address}")
    
    # If no contacts were found, provide a fallback message
    if len(response_parts) == 1:
        response_parts.append("\nI couldn't find specific contact information for the resources. Please try contacting general emergency services or check official government websites for your location.")
    
    response_text = "\n".join(response_parts)
    
    # Prepare structured data for the response
    structured_data = {
        "timestamp": time.time(),
        "query": query if isinstance(query_or_urls, str) else "",
        "urls_searched": urls,
        "contact_info": {
            "emergency": contact_info.get("emergency", []),
            "phone": contact_info.get("phone", []),
            "email": contact_info.get("email", []),
            "address": contact_info.get("address", []),
            "websites": contact_info.get("websites", [])
        },
        "resource_types": []
    }
    
    # Get location from query_info if available
    location = None
    if query_info and query_info.get('location'):
        location = query_info.get('location')
    
    # Return both the formatted text response and structured data
    return {
        "response": response_text,
        "data": structured_data,
        "info_type": "resource_information",
        "location": location,
        "contact_count": sum(len(contact_info.get(k, [])) for k in ["emergency", "phone", "email", "address"])
    }
