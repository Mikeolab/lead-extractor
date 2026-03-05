"""
Name Extractor - Extracts person and business names from web content.

Uses multiple strategies:
1. Meta tags (author, og:site_name)
2. Structured data (JSON-LD, Schema.org)
3. Title and heading analysis
4. Contact page patterns
"""
import re
import json
import logging
from typing import List, Set, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def extract_from_meta_tags(soup: BeautifulSoup) -> Set[str]:
    """Extract names from HTML meta tags."""
    names = set()
    
    # Author meta tag
    author_meta = soup.find("meta", attrs={"name": "author"})
    if author_meta and author_meta.get("content"):
        name = author_meta["content"].strip()
        if 2 < len(name) < 100:
            names.add(name)
    
    # OG site name
    og_name = soup.find("meta", attrs={"property": "og:site_name"})
    if og_name and og_name.get("content"):
        name = og_name["content"].strip()
        if 2 < len(name) < 100:
            names.add(name)
    
    # OG title as fallback
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        name = og_title["content"].strip()
        if 2 < len(name) < 100:
            names.add(name)
    
    return names


def extract_from_structured_data(soup: BeautifulSoup) -> Set[str]:
    """Extract names from JSON-LD structured data."""
    names = set()
    
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            if not script.string:
                continue
            data = json.loads(script.string)
            
            # Handle both single objects and arrays
            if isinstance(data, list):
                items = data
            else:
                items = [data]
            
            for item in items:
                _extract_names_from_jsonld(item, names)
                
        except (json.JSONDecodeError, Exception):
            continue
    
    return names


def _extract_names_from_jsonld(data: dict, names: Set[str], depth: int = 0):
    """Recursively extract names from JSON-LD data."""
    if depth > 5 or not isinstance(data, dict):
        return
    
    # Direct name fields
    for key in ["name", "legalName", "alternateName"]:
        if key in data and isinstance(data[key], str):
            name = data[key].strip()
            if 2 < len(name) < 100:
                names.add(name)
    
    # Author
    if "author" in data:
        author = data["author"]
        if isinstance(author, str):
            names.add(author)
        elif isinstance(author, dict):
            _extract_names_from_jsonld(author, names, depth + 1)
        elif isinstance(author, list):
            for a in author:
                if isinstance(a, dict):
                    _extract_names_from_jsonld(a, names, depth + 1)
                elif isinstance(a, str):
                    names.add(a)
    
    # Nested objects
    for key, value in data.items():
        if isinstance(value, dict):
            _extract_names_from_jsonld(value, names, depth + 1)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _extract_names_from_jsonld(item, names, depth + 1)


def extract_from_title(soup: BeautifulSoup) -> Optional[str]:
    """Extract a potential business name from the page title."""
    title = soup.find("title")
    if title and title.string:
        # Clean common suffixes
        name = title.string.strip()
        # Remove common title patterns
        for separator in [" | ", " - ", " — ", " – ", " :: ", " >> "]:
            if separator in name:
                parts = name.split(separator)
                # Usually the business name is the first or last part
                name = parts[0].strip()
                break
        
        if 2 < len(name) < 80:
            return name
    return None


def extract_from_headings(soup: BeautifulSoup) -> Set[str]:
    """Extract potential names from H1 headings."""
    names = set()
    
    for h1 in soup.find_all("h1"):
        text = h1.get_text(strip=True)
        if text and 2 < len(text) < 80:
            # Filter out generic headings
            generic = ["home", "welcome", "about", "contact", "blog", "news", "menu"]
            if text.lower() not in generic:
                names.add(text)
    
    return names


def extract_phone_numbers(text: str) -> List[str]:
    """Extract phone numbers from text."""
    phone_patterns = [
        r'(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',
        r'\+?[0-9]{1,3}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{0,4}',
    ]
    
    phones = set()
    for pattern in phone_patterns:
        found = re.findall(pattern, text)
        for phone in found:
            clean = re.sub(r'[^\d+]', '', phone)
            if 7 <= len(clean) <= 15:
                phones.add(phone.strip())
    
    return sorted(phones)[:5]  # Limit to 5 phone numbers


def extract_names(text: str, soup: BeautifulSoup) -> dict:
    """
    Main name extraction function.
    
    Returns a dict with:
    - business_name: Most likely business/site name
    - contact_names: List of person names found
    - phones: List of phone numbers
    """
    all_names = set()
    
    # From structured data (highest quality)
    structured_names = extract_from_structured_data(soup)
    all_names.update(structured_names)
    
    # From meta tags
    meta_names = extract_from_meta_tags(soup)
    all_names.update(meta_names)
    
    # From headings
    heading_names = extract_from_headings(soup)
    all_names.update(heading_names)
    
    # Title-based name
    title_name = extract_from_title(soup)
    
    # Phone numbers
    phones = extract_phone_numbers(text)
    
    # Determine business name (prefer title, then structured data)
    business_name = title_name or (list(meta_names)[0] if meta_names else "")
    
    # Other names are potential contact names
    contact_names = sorted(all_names - {business_name}) if business_name else sorted(all_names)
    
    return {
        "business_name": business_name or "",
        "contact_names": contact_names[:10],  # Limit
        "phones": phones,
    }

