"""
Website Scraper Module
Visits URLs from search results and extracts page content for lead extraction.
Uses requests (sync) for maximum SSL/LibreSSL compatibility.
"""
from __future__ import annotations

import requests
import warnings
from bs4 import BeautifulSoup
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.config import REQUEST_TIMEOUT, MAX_CONCURRENT_SCRAPES, USER_AGENT

warnings.filterwarnings("ignore", category=UserWarning)


@dataclass
class ScrapedPage:
    url: str
    title: str = ""
    text_content: str = ""
    html_content: str = ""
    meta_description: str = ""
    success: bool = False
    error: str = ""


def _scrape_single(url: str, callback=None) -> ScrapedPage:
    """Scrape a single URL and extract its text content."""
    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        response = requests.get(
            url, headers=headers, timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

        if response.status_code != 200:
            return ScrapedPage(url=url, error=f"HTTP {response.status_code}")

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            return ScrapedPage(url=url, error=f"Not HTML: {content_type[:30]}")

        html = response.text
        soup = BeautifulSoup(html, "lxml")

        for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            element.decompose()

        title = soup.title.get_text(strip=True) if soup.title else ""
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            meta_desc = meta_tag.get("content", "")

        text_content = soup.get_text(separator=" ", strip=True)

        if callback:
            callback(f"  ✅ {url[:60]}...")

        return ScrapedPage(
            url=url, title=title, text_content=text_content,
            html_content=html, meta_description=meta_desc, success=True,
        )

    except requests.exceptions.Timeout:
        return ScrapedPage(url=url, error="Timed out")
    except requests.exceptions.ConnectionError:
        return ScrapedPage(url=url, error="Connection failed")
    except Exception as e:
        return ScrapedPage(url=url, error=f"Error: {str(e)[:60]}")


def scrape_pages(urls: list[str], callback=None) -> list[ScrapedPage]:
    """
    Scrape multiple URLs concurrently with thread pool.

    Args:
        urls: List of URLs to scrape
        callback: Optional function(message) for live progress

    Returns:
        List of ScrapedPage results (in same order as urls)
    """
    results = [None] * len(urls)

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SCRAPES) as executor:
        future_to_idx = {
            executor.submit(_scrape_single, url, callback): i
            for i, url in enumerate(urls)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                results[idx] = ScrapedPage(url=urls[idx], error=str(e))

    return results


# Keep async interface for backward compatibility
async def scrape_pages_async(urls: list[str]) -> list[ScrapedPage]:
    """Async wrapper (actually runs sync under the hood for SSL compat)."""
    return scrape_pages(urls)
