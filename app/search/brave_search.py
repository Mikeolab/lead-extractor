"""
Brave Search API Module — free tier: 2,000 queries/month, no CAPTCHA, works from datacenter IPs.
Sign up at https://api-dashboard.search.brave.com/ to get a key.
Set BRAVE_API_KEY in your environment / Render env vars.
"""
from __future__ import annotations

import httpx
from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    display_link: str = ""
    is_pdf: bool = False


@dataclass
class SearchResponse:
    query: str
    total_results: int
    results: list[SearchResult] = field(default_factory=list)
    error: str = ""
    pages_fetched: int = 0


async def brave_search(
    query: str,
    api_key: str,
    num_results: int = 20,
    offset: int = 0,
) -> SearchResponse:
    """
    Search the web using the Brave Search API.

    Args:
        query:       Search query string (supports operators like filetype:pdf).
        api_key:     Brave Search subscription token.
        num_results: Number of results (max 20 per request).
        offset:      Pagination offset.

    Returns:
        SearchResponse with results or an error message.
    """
    if not api_key:
        return SearchResponse(
            query=query, total_results=0,
            error="BRAVE_API_KEY not set. Get one free at https://api-dashboard.search.brave.com/",
        )

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    params = {
        "q": query,
        "count": min(num_results, 20),
        "offset": offset,
        "extra_snippets": "true",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers, params=params)

            if resp.status_code == 401:
                return SearchResponse(
                    query=query, total_results=0,
                    error="Invalid BRAVE_API_KEY. Check your key at https://api-dashboard.search.brave.com/",
                )
            if resp.status_code == 429:
                return SearchResponse(
                    query=query, total_results=0,
                    error="Brave API rate limit reached. Free tier allows 2,000 queries/month.",
                )
            if resp.status_code != 200:
                return SearchResponse(
                    query=query, total_results=0,
                    error=f"Brave API HTTP {resp.status_code}: {resp.text[:120]}",
                )

            data = resp.json()
            web = data.get("web", {})
            raw_results = web.get("results", [])

            results: list[SearchResult] = []
            for item in raw_results:
                item_url = item.get("url", "")
                parsed = urlparse(item_url)
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item_url,
                    snippet=item.get("description", ""),
                    display_link=parsed.netloc,
                    is_pdf=item_url.lower().endswith(".pdf"),
                ))

            return SearchResponse(
                query=query,
                total_results=len(results),
                results=results,
                pages_fetched=1,
            )

    except httpx.TimeoutException:
        return SearchResponse(
            query=query, total_results=0,
            error="Brave API request timed out. Try again.",
        )
    except Exception as e:
        return SearchResponse(
            query=query, total_results=0,
            error=f"Brave search error: {str(e)[:100]}",
        )
