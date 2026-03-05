"""
Page Scraper - Fetches and parses web pages for lead extraction.

Uses httpx for async HTTP requests and BeautifulSoup for parsing.
"""
import asyncio
import httpx
import logging
from typing import Optional, Tuple
from bs4 import BeautifulSoup
from backend.config import USER_AGENT, MAX_CONCURRENT_SCRAPES

logger = logging.getLogger(__name__)

# Semaphore to limit concurrent scrapes
_scrape_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCRAPES)

# Skip these file types
SKIP_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".mp4", ".mp3",
    ".zip", ".tar", ".gz", ".exe", ".dmg", ".doc", ".docx", ".xls",
    ".xlsx", ".ppt", ".pptx", ".css", ".js", ".woff", ".woff2",
}


def should_skip_url(url: str) -> bool:
    """Check if URL should be skipped (non-HTML content)."""
    lower_url = url.lower()
    for ext in SKIP_EXTENSIONS:
        if lower_url.endswith(ext):
            return True
    return False


async def scrape_page(url: str, timeout: float = 15.0) -> Tuple[Optional[str], Optional[BeautifulSoup]]:
    """
    Fetch a web page and return its text content and parsed HTML.
    
    Args:
        url: URL to scrape
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (raw_text, BeautifulSoup object) or (None, None) on failure
    """
    if should_skip_url(url):
        logger.debug(f"Skipping non-HTML URL: {url}")
        return None, None
    
    async with _scrape_semaphore:
        try:
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
            
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                max_redirects=5,
            ) as client:
                response = await client.get(url, headers=headers)
                
                # Check content type
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    logger.debug(f"Skipping non-HTML content at {url}: {content_type}")
                    return None, None
                
                response.raise_for_status()
                html_content = response.text
            
            # Parse HTML
            soup = BeautifulSoup(html_content, "lxml")
            
            # Remove script and style elements
            for element in soup(["script", "style", "noscript", "iframe"]):
                element.decompose()
            
            # Get clean text
            text = soup.get_text(separator=" ", strip=True)
            
            logger.debug(f"Successfully scraped: {url} ({len(text)} chars)")
            return text, soup
            
        except httpx.TimeoutException:
            logger.debug(f"Timeout scraping: {url}")
        except httpx.HTTPStatusError as e:
            logger.debug(f"HTTP {e.response.status_code} for: {url}")
        except Exception as e:
            logger.debug(f"Error scraping {url}: {e}")
        
        return None, None


async def scrape_multiple_pages(urls: list) -> list:
    """
    Scrape multiple pages concurrently.
    
    Args:
        urls: List of URLs to scrape
        
    Returns:
        List of (url, text, soup) tuples for successful scrapes
    """
    tasks = [scrape_page(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    scraped = []
    for url, result in zip(urls, results):
        if isinstance(result, Exception):
            logger.debug(f"Exception scraping {url}: {result}")
            continue
        text, soup = result
        if text and soup:
            scraped.append((url, text, soup))
    
    logger.info(f"Successfully scraped {len(scraped)}/{len(urls)} pages")
    return scraped

