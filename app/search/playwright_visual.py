"""
Playwright Visual Browser Automation
Shows live browser window with clicks, navigation, and automation in real-time.
Screenshots are captured and streamed to Streamlit for live visualization.
"""
from __future__ import annotations

import time
import threading
from pathlib import Path
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass, field
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from PIL import Image
import io
import base64


@dataclass
class VisualSearchResult:
    title: str
    url: str
    snippet: str
    display_link: str = ""
    is_pdf: bool = False


@dataclass
class VisualSearchResponse:
    query: str
    total_results: int
    results: list[VisualSearchResult] = field(default_factory=list)
    error: str = ""
    pages_fetched: int = 0
    screenshots: list[str] = field(default_factory=list)  # Base64 encoded screenshots


class VisualBrowserAutomation:
    """Manages Playwright browser with live screenshot streaming."""

    def __init__(
        self,
        screenshot_dir: Path,
        headless: bool = False,
        slow_mo: int = 500,  # Slow down actions for visibility
    ):
        self.screenshot_dir = screenshot_dir
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.slow_mo = slow_mo
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.current_screenshot_path: Optional[Path] = None
        self.screenshot_counter = 0

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        self.context = self.browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        self.page = self.context.new_page()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def take_screenshot(self, label: str = "") -> str:
        """Take screenshot and return base64 encoded string."""
        if not self.page:
            return ""
        
        self.screenshot_counter += 1
        filename = f"screenshot_{self.screenshot_counter:04d}_{label.replace(' ', '_')[:20]}.png"
        filepath = self.screenshot_dir / filename
        
        try:
            self.page.screenshot(path=str(filepath), full_page=False)
            self.current_screenshot_path = filepath
            
            # Convert to base64 for Streamlit
            with open(filepath, "rb") as f:
                img_data = f.read()
                base64_str = base64.b64encode(img_data).decode()
                return f"data:image/png;base64,{base64_str}"
        except Exception:
            return ""

    def human_like_click(self, selector: str, delay: float = 0.5):
        """Click with human-like behavior."""
        if not self.page:
            return
        try:
            element = self.page.wait_for_selector(selector, timeout=5000)
            if element:
                # Move mouse to element first
                element.hover()
                time.sleep(delay)
                element.click()
                self.take_screenshot(f"click_{selector[:20]}")
        except Exception:
            pass

    def human_like_type(self, selector: str, text: str, delay: float = 0.1):
        """Type with human-like delays."""
        if not self.page:
            return
        try:
            element = self.page.wait_for_selector(selector, timeout=5000)
            if element:
                element.click()
                time.sleep(0.2)
                for char in text:
                    element.type(char, delay=delay)
                self.take_screenshot(f"typed_{text[:20]}")
        except Exception:
            pass

    def scroll_page(self, pixels: int = 300):
        """Scroll page with human-like behavior."""
        if not self.page:
            return
        self.page.evaluate(f"window.scrollBy(0, {pixels})")
        time.sleep(0.3)
        self.take_screenshot("scrolled")


def google_search_visual(
    query: str,
    num_results: int = 10,
    max_pages: int = 3,
    delay_between_pages: float = 3.0,
    delay_between_actions: float = 1.0,
    max_retries: int = 2,
    headless: bool = False,
    screenshot_dir: Path = None,
    callback: Optional[Callable[[str], None]] = None,
    screenshot_callback: Optional[Callable[[str], None]] = None,
    stop_flag: Optional[dict] = None,
) -> VisualSearchResponse:
    """
    Search Google using Playwright with live visual feedback.

    Args:
        query: Search query
        num_results: Target number of results
        max_pages: Maximum pages to fetch
        delay_between_pages: Delay between pages
        delay_between_actions: Delay between actions
        max_retries: Max retries on failure
        headless: Run browser in headless mode (False = visible)
        screenshot_dir: Directory to save screenshots
        callback: Function(message) for text updates
        screenshot_callback: Function(base64_image) for screenshot updates
        stop_flag: Dict with {"stop": bool} for cancellation

    Returns:
        VisualSearchResponse with results and screenshots
    """
    if screenshot_dir is None:
        screenshot_dir = Path("/tmp/lead_extractor_screenshots")
    
    all_results = []
    screenshots = []
    pages_fetched = 0

    try:
        if callback:
            callback(f"🔍 Starting Google search: \"{query}\"")
            callback(f"   Browser: {'Headless' if headless else 'Visible (Live View)'}")

        with VisualBrowserAutomation(screenshot_dir, headless=headless, slow_mo=int(delay_between_actions * 1000)) as browser:
            if callback:
                callback("   [*] Opening browser...")
            
            # Navigate to Google
            browser.page.goto("https://www.google.com", wait_until="networkidle")
            screenshot = browser.take_screenshot("google_homepage")
            if screenshot and screenshot_callback:
                screenshot_callback(screenshot)
            if callback:
                callback("   [✓] Google homepage loaded")

            # Accept cookies if present
            try:
                accept_btn = browser.page.query_selector("button:has-text('Accept'), button:has-text('I agree')")
                if accept_btn:
                    browser.human_like_click("button:has-text('Accept'), button:has-text('I agree')")
                    if callback:
                        callback("   [*] Accepted cookies")
            except Exception:
                pass

            # Type search query
            if callback:
                callback(f"   [*] Typing search query...")
            search_box = browser.page.wait_for_selector('textarea[name="q"], input[name="q"]', timeout=5000)
            if search_box:
                browser.human_like_type('textarea[name="q"], input[name="q"]', query, delay=0.05)
                screenshot = browser.take_screenshot("query_typed")
                if screenshot and screenshot_callback:
                    screenshot_callback(screenshot)

            # Press Enter
            if callback:
                callback("   [*] Pressing Enter to search...")
            browser.page.keyboard.press("Enter")
            browser.page.wait_for_load_state("networkidle")
            screenshot = browser.take_screenshot("search_results_page1")
            if screenshot and screenshot_callback:
                screenshot_callback(screenshot)
            if callback:
                callback("   [✓] Search results loaded")

            # Extract results from current page
            for page_num in range(1, max_pages + 1):
                if stop_flag and stop_flag.get("stop"):
                    break

                if page_num > 1:
                    if callback:
                        callback(f"   ⏳ Waiting {delay_between_pages}s before page {page_num}...")
                    time.sleep(delay_between_pages)

                    # Find and click "Next" button
                    try:
                        next_btn = browser.page.query_selector('a#pnnext, a:has-text("Next")')
                        if next_btn:
                            if callback:
                                callback(f"   [*] Clicking 'Next' button...")
                            browser.human_like_click('a#pnnext, a:has-text("Next")')
                            browser.page.wait_for_load_state("networkidle")
                            screenshot = browser.take_screenshot(f"search_results_page{page_num}")
                            if screenshot and screenshot_callback:
                                screenshot_callback(screenshot)
                        else:
                            if callback:
                                callback("   ⚠️ No more pages available")
                            break
                    except Exception:
                        if callback:
                            callback("   ⚠️ Could not navigate to next page")
                        break

                # Extract results
                try:
                    result_elements = browser.page.query_selector_all("div.g")
                    page_results = []

                    for elem in result_elements:
                        try:
                            title_elem = elem.query_selector("h3")
                            link_elem = elem.query_selector("a")
                            snippet_elem = elem.query_selector("div.VwiC3b, span.aCOpRe")

                            if not title_elem or not link_elem:
                                continue

                            title = title_elem.inner_text().strip()
                            url = link_elem.get_attribute("href")
                            
                            if not url or "google.com" in url:
                                continue

                            snippet = snippet_elem.inner_text().strip() if snippet_elem else ""

                            # Get display link
                            cite_elem = elem.query_selector("cite")
                            display_link = cite_elem.inner_text().strip() if cite_elem else url.split("/")[2] if "/" in url else ""

                            is_pdf = url.lower().endswith(".pdf")

                            page_results.append(VisualSearchResult(
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
                            callback(f"   ⚠️ Page {page_num}: 0 results")

                    if len(all_results) >= num_results:
                        break

                except Exception as e:
                    if callback:
                        callback(f"   ❌ Error extracting results: {str(e)[:60]}")

            # Scroll and take final screenshot
            browser.scroll_page(500)
            final_screenshot = browser.take_screenshot("final_results")
            if final_screenshot and screenshot_callback:
                screenshot_callback(final_screenshot)

        # Trim results
        all_results = all_results[:num_results]

        if not all_results:
            return VisualSearchResponse(
                query=query, total_results=0,
                error="No results found.",
            )

        if callback:
            pdf_count = sum(1 for r in all_results if r.is_pdf)
            extra = f" ({pdf_count} PDFs)" if pdf_count else ""
            callback(f"✅ Search complete: {len(all_results)} results from {pages_fetched} page(s){extra}")

        return VisualSearchResponse(
            query=query, total_results=len(all_results),
            results=all_results, pages_fetched=pages_fetched,
            screenshots=screenshots,
        )

    except Exception as e:
        return VisualSearchResponse(
            query=query, total_results=0,
            error=f"Search error: {str(e)}",
        )

