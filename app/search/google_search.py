"""
Google Custom Search API Module
Searches Google and returns structured results.
"""
from __future__ import annotations
import httpx
from dataclasses import dataclass, field


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


async def google_search(
    query: str,
    api_key: str,
    cse_id: str,
    num_results: int = 10,
    start: int = 1,
) -> SearchResponse:
    """
    Search Google using Custom Search JSON API.

    Args:
        query: Search query string
        api_key: Google API key
        cse_id: Custom Search Engine ID
        num_results: Number of results to return (max 10 per request)
        start: Start index for pagination (1-based)

    Returns:
        SearchResponse with results
    """
    if not api_key or not cse_id:
        return SearchResponse(
            query=query,
            total_results=0,
            error="Google API key or CSE ID not configured. Check your .env file.",
        )

    url = "https://www.googleapis.com/customsearch/v1"

    all_results = []
    total_results = 0
    current_start = start
    remaining = num_results

    async with httpx.AsyncClient(timeout=30) as client:
        while remaining > 0:
            # Google CSE returns max 10 results per request
            batch_size = min(remaining, 10)

            params = {
                "key": api_key,
                "cx": cse_id,
                "q": query,
                "num": batch_size,
                "start": current_start,
            }

            try:
                response = await client.get(url, params=params)

                if response.status_code == 403:
                    return SearchResponse(
                        query=query,
                        total_results=0,
                        error="API quota exceeded or invalid API key. Check your Google API key.",
                    )

                if response.status_code != 200:
                    return SearchResponse(
                        query=query,
                        total_results=0,
                        error=f"Google API error: {response.status_code} - {response.text}",
                    )

                data = response.json()
                total_results = int(
                    data.get("searchInformation", {}).get("totalResults", 0)
                )

                items = data.get("items", [])
                if not items:
                    break

                for item in items:
                    all_results.append(
                        SearchResult(
                            title=item.get("title", ""),
                            url=item.get("link", ""),
                            snippet=item.get("snippet", ""),
                            display_link=item.get("displayLink", ""),
                        )
                    )

                remaining -= len(items)
                current_start += len(items)

                # If we got fewer results than requested, no more pages
                if len(items) < batch_size:
                    break

            except httpx.TimeoutException:
                return SearchResponse(
                    query=query,
                    total_results=len(all_results),
                    results=all_results,
                    error="Request timed out. Partial results returned.",
                )
            except Exception as e:
                return SearchResponse(
                    query=query,
                    total_results=len(all_results),
                    results=all_results,
                    error=f"Search error: {str(e)}",
                )

    return SearchResponse(
        query=query,
        total_results=total_results,
        results=all_results,
    )

