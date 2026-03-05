"""
Google Search Module - Searches Google and returns URLs.

Uses googlesearch-python (free) as the default engine.
"""
import asyncio
import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result."""
    url: str
    title: str = ""
    description: str = ""


async def google_search(
    query: str,
    num_results: int = 20,
    lang: str = "en",
    region: str = "",
    sleep_interval: float = 1.0,
) -> List[SearchResult]:
    """
    Search Google for the given query and return URLs.
    
    Uses googlesearch-python library (free, no API key needed).
    
    Args:
        query: Search query string
        num_results: Number of results to fetch
        lang: Language for results
        region: Region filter (e.g., 'us', 'uk')
        sleep_interval: Delay between requests to avoid rate limiting
        
    Returns:
        List of SearchResult objects
    """
    results = []
    
    try:
        # Run the synchronous googlesearch in a thread pool
        from googlesearch import search
        
        loop = asyncio.get_event_loop()
        urls = await loop.run_in_executor(
            None,
            lambda: list(search(
                query,
                num_results=num_results,
                lang=lang,
                sleep_interval=sleep_interval,
            ))
        )
        
        for url in urls:
            results.append(SearchResult(url=url))
            
        logger.info(f"Google search for '{query}' returned {len(results)} results")
        
    except ImportError:
        logger.error("googlesearch-python not installed. Run: pip install googlesearch-python")
    except Exception as e:
        logger.error(f"Google search error: {e}")
    
    return results


async def google_search_with_context(
    query: str,
    num_results: int = 20,
    include_contact_pages: bool = True,
) -> List[SearchResult]:
    """
    Enhanced Google search that also searches for contact pages.
    
    This does the main search AND a second search for "contact" pages
    to maximize email/name extraction.
    """
    # Main search
    main_results = await google_search(query, num_results=num_results)
    
    all_results = list(main_results)
    seen_urls = {r.url for r in all_results}
    
    if include_contact_pages:
        # Also search for contact pages
        contact_query = f"{query} contact email"
        contact_results = await google_search(
            contact_query,
            num_results=min(10, num_results // 2),
            sleep_interval=2.0,  # Be more careful with extra searches
        )
        
        for result in contact_results:
            if result.url not in seen_urls:
                all_results.append(result)
                seen_urls.add(result.url)
    
    logger.info(f"Total search results for '{query}': {len(all_results)}")
    return all_results

