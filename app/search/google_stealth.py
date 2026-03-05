"""
Google Stealth Scraper Module
Uses Selenium with undetected-chromedriver for anti-detection scraping.
Human-like behavior simulation with configurable delays and retries.
"""
from __future__ import annotations

import time
import random
from dataclasses import dataclass, field
from typing import Optional, Callable
from urllib.parse import urlparse, quote_plus
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc


@dataclass
class GoogleSearchResult:
    title: str
    url: str
    snippet: str
    display_link: str = ""
    is_pdf: bool = False


@dataclass
class GoogleSearchResponse:
    query: str
    total_results: int
    results: list[GoogleSearchResult] = field(default_factory=list)
    error: str = ""
    pages_fetched: int = 0


def _human_delay(min_sec: float = 0.5, max_sec: float = 2.0):
    """Random delay to simulate human behavior."""
    time.sleep(random.uniform(min_sec, max_sec))


def _create_stealth_driver(headless: bool = False) -> uc.Chrome:
    """Create an undetected Chrome driver with stealth settings."""
    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Randomize user agent
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    options.add_argument(f"--user-agent={random.choice(user_agents)}")
    
    driver = uc.Chrome(options=options, version_main=None)
    
    # Execute stealth script
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
    })
    
    return driver


def google_search(
    query: str,
    num_results: int = 10,
    max_pages: int = 3,
    delay_between_pages: float = 3.0,
    delay_between_actions: float = 1.0,
    max_retries: int = 2,
    headless: bool = True,
    callback: Optional[Callable[[str], None]] = None,
    stop_flag: Optional[dict] = None,
) -> GoogleSearchResponse:
    """
    Search Google using stealth Chrome driver.

    Args:
        query: Search query string
        num_results: Target number of results
        max_pages: Maximum pages to fetch
        delay_between_pages: Seconds to wait between pages
        delay_between_actions: Seconds to wait between actions (human-like)
        max_retries: Number of retries on failure
        headless: Run browser in headless mode
        callback: Optional function(message) for live updates
        stop_flag: Optional dict with {"stop": bool} to check for cancellation

    Returns:
        GoogleSearchResponse with results
    """
    driver = None
    all_results = []
    pages_fetched = 0

    try:
        if callback:
            callback(f"🔍 Starting Google search: \"{query}\"")
            callback(f"   Max Pages: {max_pages} | Delay: {delay_between_pages}s | Retries: {max_retries}")

        # Create driver
        if callback:
            callback("   [*] Initializing Chrome driver (stealth mode)...")
        driver = _create_stealth_driver(headless=headless)
        driver.set_page_load_timeout(30)
        _human_delay(1.0, 2.0)

        for page_num in range(1, max_pages + 1):
            if stop_flag and stop_flag.get("stop"):
                if callback:
                    callback("   🛑 Search stopped by user")
                break

            if page_num > 1:
                if callback:
                    callback(f"   ⏳ Waiting {delay_between_pages}s before page {page_num}...")
                time.sleep(delay_between_pages)

            # Build Google search URL
            if page_num == 1:
                url = f"https://www.google.com/search?q={quote_plus(query)}&num=10"
            else:
                # Get next page URL from Google's pagination
                try:
                    next_button = driver.find_element(By.ID, "pnnext")
                    url = next_button.get_attribute("href")
                    if not url:
                        if callback:
                            callback(f"   ⚠️ No more pages available")
                        break
                except NoSuchElementException:
                    if callback:
                        callback(f"   ⚠️ No more pages available")
                    break

            # Navigate to page
            if callback:
                callback(f"   [*] Loading page {page_num}...")
            
            for attempt in range(1, max_retries + 1):
                try:
                    driver.get(url)
                    _human_delay(delay_between_actions, delay_between_actions * 1.5)
                    
                    # Wait for results to load
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "search"))
                    )
                    break
                except TimeoutException:
                    if callback:
                        callback(f"   [!] Page load timeout (attempt {attempt}/{max_retries})")
                    if attempt < max_retries:
                        time.sleep(3)
                    else:
                        raise

            # Check for CAPTCHA
            try:
                captcha = driver.find_element(By.ID, "captcha-form")
                if captcha:
                    if callback:
                        callback("   ❌ CAPTCHA detected! Please solve manually or wait.")
                    return GoogleSearchResponse(
                        query=query, total_results=0,
                        error="CAPTCHA detected. Please try again later.",
                    )
            except NoSuchElementException:
                pass

            # Extract results
            try:
                results_container = driver.find_element(By.ID, "search")
                result_elements = results_container.find_elements(By.CSS_SELECTOR, "div.g")
                
                page_results = []
                for elem in result_elements:
                    try:
                        # Title
                        title_elem = elem.find_element(By.CSS_SELECTOR, "h3")
                        title = title_elem.text.strip()

                        # URL
                        link_elem = elem.find_element(By.CSS_SELECTOR, "a")
                        url = link_elem.get_attribute("href")
                        if not url or "google.com" in url:
                            continue

                        # Snippet
                        try:
                            snippet_elem = elem.find_element(By.CSS_SELECTOR, "div.VwiC3b")
                            snippet = snippet_elem.text.strip()
                        except NoSuchElementException:
                            snippet = ""

                        # Display link
                        try:
                            display_elem = elem.find_element(By.CSS_SELECTOR, "cite")
                            display_link = display_elem.text.strip()
                        except NoSuchElementException:
                            parsed = urlparse(url)
                            display_link = parsed.netloc

                        is_pdf = url.lower().endswith(".pdf")

                        page_results.append(GoogleSearchResult(
                            title=title, url=url, snippet=snippet,
                            display_link=display_link, is_pdf=is_pdf,
                        ))
                    except Exception:
                        continue

                if page_results:
                    all_results.extend(page_results)
                    pages_fetched += 1
                    if callback:
                        callback(f"   ✅ Page {page_num}: {len(page_results)} results (total: {len(all_results)})")
                else:
                    if callback:
                        callback(f"   ⚠️ Page {page_num}: 0 results found")
                    if page_num > 1:
                        break

                # Enough results?
                if len(all_results) >= num_results:
                    break

            except Exception as e:
                if callback:
                    callback(f"   ❌ Error extracting results: {str(e)[:60]}")
                if page_num == 1:
                    return GoogleSearchResponse(
                        query=query, total_results=0,
                        error=f"Failed to extract results: {str(e)}",
                    )

        # Trim to requested number
        all_results = all_results[:num_results]

        if not all_results:
            return GoogleSearchResponse(
                query=query, total_results=0,
                error="No results found. Try a different query.",
            )

        if callback:
            pdf_count = sum(1 for r in all_results if r.is_pdf)
            extra = f" ({pdf_count} PDFs)" if pdf_count else ""
            callback(f"✅ Search complete: {len(all_results)} results from {pages_fetched} page(s){extra}")

        return GoogleSearchResponse(
            query=query, total_results=len(all_results),
            results=all_results, pages_fetched=pages_fetched,
        )

    except Exception as e:
        return GoogleSearchResponse(
            query=query, total_results=0,
            error=f"Search error: {str(e)}",
        )
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

