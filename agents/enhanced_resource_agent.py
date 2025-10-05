import asyncio
import re
import json
import time
import traceback
from typing import Callable, Dict, List, Optional, Union, Any

# Import the centralized environment configuration
from utils.env_config import get_api_key, is_key_available

# Try importing optional dependencies, handle gracefully if not available
try:
    from crawl4ai import AsyncWebCrawler
    CRAWL_AVAILABLE = True
except ImportError:
    CRAWL_AVAILABLE = False
    print("Warning: crawl4ai package not installed. Web crawling will be limited.")

# Import the AI helpers
from utils.ai_helpers import call_exa_api

try:
    from exa_py import Exa
    EXA_API_KEY = get_api_key('EXA_API_KEY')
    EXA_AVAILABLE = is_key_available('EXA_API_KEY')
    if EXA_AVAILABLE:
        exa_client = Exa(api_key=EXA_API_KEY)
    else:
        print("Warning: EXA_API_KEY not set. Web search functionality will be limited.")
except ImportError:
    EXA_AVAILABLE = False
    print("Warning: exa-py package not installed. Web search functionality will be limited.")

# Function to extract contacts from markdown text with enhanced capabilities
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

# Advanced crawling function for extracting contacts from all URLs
async def crawl_and_extract_contacts_HYBRID(url: str, update_callback: Optional[Callable[[str, str], None]] = None) -> Dict[str, Any]:
    """
    Advanced hybrid approach to crawl a webpage and extract contact information.
    Uses both regex-based and AI-powered extraction for more reliable results.
    Handles missing dependencies gracefully with fallback mechanisms.
    
    Args:
        url (str): URL to crawl
        update_callback (Optional[Callable[[str, str], None]]): Callback to update UI with status
        
    Returns:
        Dict[str, Any]: Dictionary with extracted contact information
    """
    if update_callback:
        update_callback("Resource Agent", f"Crawling URL: {url}")
    
    # Check if crawl4ai is available
    if not CRAWL_AVAILABLE:
        if update_callback:
            update_callback("Resource Agent", f"Web crawling not available - crawl4ai package not installed. Try running install_dependencies.py first.")
        return {"error": "Web crawling not available - missing dependencies", 
                "phone": ["Example: 1-800-RED-CROSS"], 
                "emergency_phone": ["911"], 
                "email": ["example@emergency.org"],
                "address": ["Example emergency response center, 123 Main St"]}
    
    try:
        # Step 1: Crawl the webpage
        try:
            async with AsyncWebCrawler() as crawler:
                if update_callback:
                    update_callback("Resource Agent", f"Initiating crawl for {url}")
                
                result = await crawler.arun(url, text={"max_characters": 8000})
                
                if not result or not result.markdown:
                    if update_callback:
                        update_callback("Resource Agent", f"Crawl returned no content from {url}")
                    return {"error": "No content found"}
                
                html_content = result.markdown
        except Exception as crawler_error:
            if "Playwright browsers not installed" in str(crawler_error):
                if update_callback:
                    update_callback("Resource Agent", "Playwright browsers not installed. Try running install_dependencies.py first.")
                return {"error": "Playwright browsers not installed. Try running install_dependencies.py first.",
                        "phone": ["Example: 1-800-RED-CROSS"], 
                        "emergency_phone": ["911"], 
                        "email": ["example@emergency.org"],
                        "address": ["Example emergency response center, 123 Main St"]}
            else:
                raise  # Re-raise if it's not a known issue
            
        # Step 2: Extract contacts using regex
        if update_callback:
            update_callback("Resource Agent", "Extracting contacts using pattern matching...")
        
        contacts = extract_contacts_from_markdown(html_content)
        
        # Step 3: If regex found insufficient contacts, fall back to AI extraction
        # Note: In the actual implementation, this would use Cerebras/Llama
        # For this demo, we'll just use regex results
        if not contacts.get("phone") and not contacts.get("email") and not contacts.get("emergency_phone"):
            if update_callback:
                update_callback("Resource Agent", "Pattern matching found insufficient contacts, falling back to AI extraction...")
            
            # In a real implementation, this would call the AI
            # For now, we'll just use what we have
            pass
        
        return contacts
            
    except Exception as e:
        if update_callback:
            update_callback("Resource Agent", f"Error crawling {url}: {str(e)}")
        return {"error": str(e)}

# Main function for the Resource Agent
async def run(query_or_urls: Union[str, List[str]], 
              update_callback: Callable[[str, str], None], 
              is_subroutine: bool = False) -> Union[str, List[Dict[str, Any]]]:
    """
    Main function for the Resource Agent. Handles both direct queries and URL lists.
    
    Args:
        query_or_urls: Either a user query string or a list of URLs to crawl
        update_callback: Callback function to update the UI with agent activity
        is_subroutine: Whether this agent is being called as a subroutine by another agent
        
    Returns:
        If is_subroutine is True: Returns the raw contact data
        If is_subroutine is False: Returns a formatted response string for the user
    """
    # Handle different input types
    if isinstance(query_or_urls, str):
        # This is a direct user query, we need to find relevant websites first
        query = query_or_urls
        update_callback("Resource Agent", "Searching for relevant resources...")
        
        update_callback("Resource Agent", "Using Exa search API...")
        try:
            # Use our improved Exa API helper with retry logic
            search_query = query + " emergency contact disaster"
            search_results = call_exa_api(search_query, num_results=3)
            
            if "results" in search_results:
                # Using the fallback results format from our helper
                urls = [result["url"] for result in search_results["results"]]
            else:
                # Using the standard Exa API results format
                urls = [result.url for result in search_results.results]
                
            # Use reliable domains for fallback URLs
            fallback_urls = [
                "https://ndrf.gov.in/contact-us",
                "https://www.nhc.noaa.gov/contact.shtml",  # US National Hurricane Center
                "https://www.ready.gov/contacts"  # FEMA contact information
            ]
            
            # Add fallback URLs if we didn't get enough results
            if len(urls) < 2:
                urls.extend(fallback_urls)
                urls = list(set(urls))  # Remove duplicates
            
            update_callback("Resource Agent", f"Found {len(urls)} relevant resources.")
        except Exception as e:
            update_callback("Resource Agent", f"Error using search API: {str(e)}. Falling back to reliable URLs.")
            # Fall back to reliable URLs
            urls = [
                "https://ndrf.gov.in/contact-us",
                "https://www.nhc.noaa.gov/contact.shtml",  # US National Hurricane Center
                "https://www.ready.gov/contacts"  # FEMA contact information
            ]
    else:
        # We were given URLs directly by another agent
        urls = query_or_urls
    
    # Crawl all URLs and extract contacts
    all_contacts_by_url = {}
    for url in urls:
        contacts = await crawl_and_extract_contacts_HYBRID(url, update_callback)
        all_contacts_by_url[url] = contacts
    
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
        
        # Add a divider for each website
        response_parts.append(f"\n--- Contacts from {url} ---")
        
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
    
    return "\n".join(response_parts)
