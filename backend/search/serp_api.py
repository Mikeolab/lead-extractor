"""
SerpAPI Search Module - Premium search backend using SerpAPI.

Requires a SerpAPI key (https://serpapi.com).
More reliable than free Google search, with structured data.
"""
import httpx
import logging
from typing import List, Optional
from backend.search.google_search import SearchResult

logger = logging.getLogger(__name__)

SERPAPI_BASE = "https://serpapi.com/search.json"


async def serpapi_search(
    query: str,
    api_key: str,
    num_results: int = 20,
    location: str = "",
    gl: str = "us",
) -> List[SearchResult]:
    """
    Search using SerpAPI for more reliable results.
    
    Args:
        query: Search query
        api_key: SerpAPI key
        num_results: Number of results
        location: Location filter
        gl: Country code
        
    Returns:
        List of SearchResult objects
    """
    results = []
    
    params = {
        "q": query,
        "api_key": api_key,
        "engine": "google",
        "num": min(num_results, 100),
        "gl": gl,
    }
    
    if location:
        params["location"] = location
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(SERPAPI_BASE, params=params)
            response.raise_for_status()
            data = response.json()
        
        organic_results = data.get("organic_results", [])
        
        for item in organic_results:
            results.append(SearchResult(
                url=item.get("link", ""),
                title=item.get("title", ""),
                description=item.get("snippet", ""),
            ))
        
        logger.info(f"SerpAPI search for '{query}' returned {len(results)} results")
        
    except httpx.HTTPError as e:
        logger.error(f"SerpAPI HTTP error: {e}")
    except Exception as e:
        logger.error(f"SerpAPI error: {e}")
    
    return results

