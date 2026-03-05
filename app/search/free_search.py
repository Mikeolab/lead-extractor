"""
Free Search Module - No API Key Required
Uses DuckDuckGo search as a free alternative to Google Custom Search API.
No billing, no API keys, works immediately.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from duckduckgo_search import DDGS


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    display_link: str = ""


@dataclass
class SearchResponse:
    query: str
    total_results: int
    results: list[SearchResult] = field(default_factory=list)
    error: str = ""


def free_search(query: str, num_results: int = 10) -> SearchResponse:
    """
    Search using DuckDuckGo - completely free, no API key needed.

    Args:
        query: Search query string
        num_results: Number of results to return

    Returns:
        SearchResponse with results
    """
    try:
        ddgs = DDGS()
        raw_results = ddgs.text(query, max_results=num_results)

        results = []
        for item in raw_results:
            url = item.get("href", "")
            # Extract display link from URL
            display_link = ""
            if url:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                display_link = parsed.netloc

            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=url,
                    snippet=item.get("body", ""),
                    display_link=display_link,
                )
            )

        return SearchResponse(
            query=query,
            total_results=len(results),
            results=results,
        )

    except Exception as e:
        return SearchResponse(
            query=query,
            total_results=0,
            error=f"Search error: {str(e)}",
        )

