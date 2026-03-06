"""
FastAPI WebSocket Server for Live Browser Automation
Runs Playwright automation, extracts leads from PDFs, and saves them.
"""
from __future__ import annotations

import asyncio
import json
import base64
import time
import io
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright, Page, Browser
from urllib.parse import quote_plus
import pdfplumber
import httpx


def is_rdp_session() -> bool:
    """
    Detect if running in RDP (Remote Desktop Protocol) session.
    RDP sessions often lack GPU acceleration and proper display drivers,
    so we should use headless mode for browser automation.
    """
    if sys.platform != 'win32':
        return False
    
    # Check Windows environment variables that indicate RDP session
    session_name = os.environ.get('SESSIONNAME', '').upper()
    client_name = os.environ.get('CLIENTNAME', '')
    remote_session = os.environ.get('REMOTE_SESSION', '0')
    
    # RDP sessions typically have SESSIONNAME starting with 'RDP'
    if session_name.startswith('RDP'):
        return True
    
    # If CLIENTNAME is set, it's likely a remote session
    if client_name:
        return True
    
    # REMOTE_SESSION environment variable
    if remote_session == '1':
        return True
    
    # Check for TERM_PROGRAM (some RDP clients set this)
    if os.environ.get('TERM_PROGRAM', '').upper() in ['RDP', 'REMOTE']:
        return True
    
    return False

# Import extractors and database
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.extractors.email_extractor import extract_emails
from app.extractors.name_extractor import extract_contact_names, extract_names_from_email
from app.extractors.phone_extractor import extract_phones
from app.export.pdf_exporter import export_to_pdf
from app.database.db import save_search, save_leads
from app.config import EXPORT_DIR

app = FastAPI()

# CORS for Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AutomationManager:
    """Manages Playwright browser automation and WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.is_running = False
        self.stop_flag = False
        self.last_screenshot_time = 0
        self.screenshot_throttle = 1.0  # Max 1 screenshot per second
        self.all_leads_buffer = []  # Buffer to save on disconnect
        self.current_session_id = None  # Track current search session

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

    def _schedule_browser_closed_complete(self):
        """Called on event loop thread when browser disconnects; schedules async broadcast."""
        if getattr(self, "_browser_closed_completion_sent", False):
            return
        asyncio.ensure_future(self._broadcast_browser_closed())

    async def _broadcast_browser_closed(self):
        """Send 'complete' to UI so it clears Running state when user closes the browser."""
        if getattr(self, "_browser_closed_completion_sent", False):
            return
        self._browser_closed_completion_sent = True
        try:
            await self.broadcast({"type": "status", "message": "🔚 Browser closed by user"})
            await self.broadcast({"type": "complete", "data": []})
        except Exception:
            pass

    async def take_screenshot(self, force: bool = False) -> str:
        """Take screenshot and return base64 string (throttled)."""
        if not self.page:
            return ""
        
        # Throttle screenshots to prevent spam
        current_time = time.time()
        if not force and (current_time - self.last_screenshot_time) < self.screenshot_throttle:
            return ""
        
        try:
            screenshot_bytes = await self.page.screenshot(full_page=False, timeout=5000)
            self.last_screenshot_time = current_time
            return base64.b64encode(screenshot_bytes).decode()
        except Exception:
            return ""

    async def extract_from_pdf(self, pdf_url: str, title: str, display_link: str) -> List[Dict]:
        """Download PDF, extract text, and extract leads."""
        leads = []
        try:
            await self.broadcast({
                "type": "status",
                "message": f"  📥 Downloading PDF: {title[:50]}...",
            })

            # Download PDF with better error handling
            pdf_bytes = None
            try:
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    response = await client.get(pdf_url)
                    if response.status_code != 200:
                        await self.broadcast({
                            "type": "status",
                            "message": f"  ❌ Failed to download PDF (HTTP {response.status_code})",
                        })
                        return leads
                    pdf_bytes = io.BytesIO(response.content)
            except httpx.TimeoutException:
                await self.broadcast({
                    "type": "status",
                    "message": f"  ❌ PDF download timeout",
                })
                return leads
            except Exception as e:
                await self.broadcast({
                    "type": "status",
                    "message": f"  ❌ Download error: {str(e)[:50]}",
                })
                return leads

            if not pdf_bytes:
                return leads
                
            # Extract text from PDF
            text_parts = []
            try:
                with pdfplumber.open(pdf_bytes) as pdf:
                    total_pages = len(pdf.pages)
                    await self.broadcast({
                        "type": "status",
                        "message": f"  📖 PDF has {total_pages} page(s), extracting text...",
                    })
                    
                    # Extract from ALL pages (not just first page)
                    for page_num, page in enumerate(pdf.pages[:100]):  # Max 100 pages
                        try:
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(page_text)
                                await self.broadcast({
                                    "type": "status",
                                    "message": f"  📄 Extracted text from page {page_num + 1}/{total_pages} ({len(page_text)} chars)",
                                })
                        except Exception as e:
                            await self.broadcast({
                                "type": "status",
                                "message": f"  ⚠️ Page {page_num + 1} extraction error: {str(e)[:40]}",
                            })
                            continue
            except Exception as e:
                await self.broadcast({
                    "type": "status",
                    "message": f"  ❌ PDF parsing error: {str(e)[:60]}",
                })
                return leads

            pdf_text = "\n".join(text_parts)
            
            if not pdf_text or len(pdf_text.strip()) < 10:
                await self.broadcast({
                    "type": "status",
                    "message": f"  ⚠️ No text extracted from PDF (might be image-based/scanned)",
                })
                return leads

            await self.broadcast({
                "type": "status",
                "message": f"  ✅ Extracted {len(pdf_text)} chars from PDF",
            })

            # Extract ONLY: name, phone, email (as requested)
            await self.broadcast({
                "type": "status",
                "message": f"  🔍 Searching for emails, phones, names...",
            })
            
            emails = extract_emails(pdf_text, "")
            phones = extract_phones(pdf_text, "")
            names = extract_contact_names(pdf_text)

            await self.broadcast({
                "type": "status",
                "message": f"  📊 Found: {len(emails)} emails, {len(phones)} phones, {len(names)} names",
            })

            # Derive names from emails if no names found
            if emails and not names:
                for email in emails:
                    derived = extract_names_from_email(email)
                    if derived:
                        names.append(derived)

            # Create lead entries - ONLY name, phone, email
            if emails:
                # Create one lead per email
                for j, email in enumerate(emails):
                    cn = names[j] if j < len(names) else (names[0] if names else "")
                    ph = phones[j] if j < len(phones) else (phones[0] if phones else "")
                    leads.append({
                        "email": email,
                        "phone": ph,
                        "contact_name": cn,
                        # Minimal fields for database compatibility
                        "business_name": "",
                        "website": "",
                        "source_url": pdf_url,
                        "snippet": "",
                    })
                await self.broadcast({
                    "type": "status",
                    "message": f"  ✅ Created {len(leads)} lead(s) from PDF",
                })
            elif phones or names:
                # Include even without email (at least phone or name)
                leads.append({
                    "email": "",
                    "phone": phones[0] if phones else "",
                    "contact_name": names[0] if names else "",
                    "business_name": "",
                    "website": "",
                    "source_url": pdf_url,
                    "snippet": "",
                })
                await self.broadcast({
                    "type": "status",
                    "message": f"  ✅ Created 1 lead (phone/name only) from PDF",
                })
            else:
                await self.broadcast({
                    "type": "status",
                    "message": f"  ⚠️ No emails/phones/names found in PDF text",
                })
                # Debug: show first 200 chars of text
                await self.broadcast({
                    "type": "status",
                    "message": f"  🔍 PDF text sample: {pdf_text[:200]}...",
                })

        except Exception as e:
            await self.broadcast({
                "type": "status",
                "message": f"  ❌ PDF extraction error: {str(e)[:60]}",
            })

        return leads

    async def run_automation(
        self,
        queries: List[str],
        max_pages: int = 10,
        delay_between_pages: float = 3.0,
        delay_between_actions: float = 1.0,
        target_leads: int = 0,  # Target lead count (0 = no limit)
    ):
        """Run browser automation loop through multiple queries."""
        self.is_running = True
        self.stop_flag = False
        all_leads = []
        total_leads_extracted = 0  # Track total leads for real-time updates
        self._event_loop = asyncio.get_running_loop()
        self._browser_closed_completion_sent = False

        try:
            self.playwright = await async_playwright().start()
            
            # Headless on server (no display) or RDP; headed on desktop with display
            use_headless = is_rdp_session() or not os.environ.get("DISPLAY") or os.environ.get("RENDER")
            if use_headless:
                await self.broadcast({
                    "type": "status",
                    "message": "🖥️ Running in headless browser mode (server/cloud)",
                })
            
            self.browser = await self.playwright.chromium.launch(
                headless=use_headless,
                slow_mo=int(delay_between_actions * 1000),
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                ],
            )

            # When user closes the external browser: set flags AND immediately tell the UI so "Running" clears
            def on_browser_disconnected():
                self.stop_flag = True
                self.is_running = False
                try:
                    loop = getattr(self, "_event_loop", None)
                    if loop and not loop.is_closed():
                        loop.call_soon_thread_safe(self._schedule_browser_closed_complete)
                except Exception:
                    pass
            self.browser.on("disconnected", on_browser_disconnected)

            # Create context with better stealth settings
            context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},  # More realistic size
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
                permissions=["geolocation"],
                geolocation={"latitude": 40.7128, "longitude": -74.0060},  # New York
                color_scheme="light",
            )
            
            # Add extra headers to look more like a real browser
            await context.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            })
            
            self.page = await context.new_page()
            
            # Remove webdriver property
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Override plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Override languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)

            await self.broadcast({
                "type": "status",
                "message": f"🚀 Starting automation - {len(queries)} queries",
            })

            session_start_time = datetime.now()
            self.all_leads_buffer = []  # Reset buffer

            # Loop through queries
            for query_idx, query in enumerate(queries):
                if self.stop_flag:
                    await self.broadcast({"type": "status", "message": "🛑 Stopped by user"})
                    break

                try:
                    await self.broadcast({
                        "type": "status",
                        "message": f"--- Query {query_idx + 1}/{len(queries)}: \"{query}\" ---",
                    })

                    # Create search record in database
                    try:
                        search_id = save_search(query, num_results=0)
                        self.current_session_id = search_id
                        await self.broadcast({
                            "type": "status",
                            "message": f"💾 Created search session #{search_id}",
                        })
                    except Exception as e:
                        await self.broadcast({
                            "type": "status",
                            "message": f"⚠️ Database error: {str(e)[:50]}. Continuing...",
                        })
                        search_id = None
                        self.current_session_id = None

                    query_leads = []

                    # STEP 1: Navigate to Google (retry up to 3 times so first page does not quit the run)
                    step1_ok = False
                    for step1_attempt in range(1, 4):
                        if self.stop_flag:
                            break
                        await self.broadcast({"type": "status", "message": f"🌐 [STEP 1] Opening Google... (attempt {step1_attempt}/3)"})
                        try:
                            await self.page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=30000)
                            await asyncio.sleep(2)
                            await self.page.wait_for_load_state("networkidle", timeout=30000)
                            if "google.com" not in self.page.url.lower():
                                raise Exception(f"Navigation failed - URL is {self.page.url}")
                            await self.broadcast({"type": "status", "message": "✅ [STEP 1] Successfully navigated to Google"})
                            screenshot = await self.take_screenshot(force=True)
                            if screenshot:
                                await self.broadcast({"type": "screenshot", "data": screenshot})
                            step1_ok = True
                            break
                        except Exception as e:
                            await self.broadcast({
                                "type": "status",
                                "message": f"⚠️ [STEP 1] Attempt {step1_attempt}/3 failed: {str(e)[:50]}",
                            })
                            if step1_attempt < 3:
                                await asyncio.sleep(3)  # Brief pause before retry
                    if not step1_ok:
                        await self.broadcast({"type": "status", "message": "❌ [STEP 1] Could not load Google after 3 attempts. Skipping query."})
                        continue

                    await asyncio.sleep(delay_between_actions)

                    # Accept cookies if present
                    try:
                        accept_btn = await self.page.query_selector("button:has-text('Accept'), button:has-text('I agree')")
                        if accept_btn:
                            await accept_btn.click()
                            await self.broadcast({"type": "status", "message": "✅ Accepted cookies"})
                            await asyncio.sleep(0.5)
                    except Exception:
                        pass

                    # STEP 2: Type search query
                    await self.broadcast({"type": "status", "message": f"⌨️ [STEP 2] Typing: \"{query}\""})
                    try:
                        search_box = await self.page.wait_for_selector('textarea[name="q"], input[name="q"]', timeout=10000)
                        if not search_box:
                            raise Exception("Search box element not found")
                        # Human-like click and type
                        await search_box.click()
                        await asyncio.sleep(0.5)  # Pause before typing
                        
                        # Type character by character for more human-like behavior
                        await search_box.fill("")  # Clear first
                        for char in query:
                            await search_box.type(char, delay=50 + (hash(char) % 50))  # Random delay 50-100ms
                        await asyncio.sleep(0.3)  # Pause after typing
                        
                        # Validate input
                        input_value = await search_box.input_value()
                        if input_value != query:
                            raise Exception(f"Input validation failed - expected '{query}', got '{input_value}'")
                        await self.broadcast({"type": "status", "message": "✅ [STEP 2] Query typed successfully"})
                        screenshot = await self.take_screenshot(force=True)
                        if screenshot:
                            await self.broadcast({"type": "screenshot", "data": screenshot})
                    except Exception as e:
                        await self.broadcast({
                            "type": "status",
                            "message": f"❌ [STEP 2] Could not type query: {str(e)[:50]}. Skipping query.",
                        })
                        continue

                    # STEP 3: Press Enter and wait for results
                    await self.broadcast({"type": "status", "message": "🔍 [STEP 3] Searching..."})
                    try:
                        # Check for reCAPTCHA before searching
                        recaptcha = await self.page.query_selector("iframe[src*='recaptcha'], div[class*='recaptcha']")
                        if recaptcha:
                            await self.broadcast({
                                "type": "status",
                                "message": "⚠️ [STEP 3] reCAPTCHA detected! Waiting 10 seconds...",
                            })
                            await asyncio.sleep(10)  # Wait for manual solve or auto-solve
                        
                        await self.page.keyboard.press("Enter")
                        await asyncio.sleep(1)  # Human-like pause
                        
                        # Wait for URL to change to search page
                        try:
                            await self.page.wait_for_url("**/search**", timeout=30000)
                        except Exception:
                            # Check if we hit reCAPTCHA
                            current_url = self.page.url
                            if "sorry" in current_url.lower() or "recaptcha" in current_url.lower():
                                await self.broadcast({
                                    "type": "status",
                                    "message": "⚠️ [STEP 3] reCAPTCHA page detected! Please solve manually or wait...",
                                })
                                await asyncio.sleep(15)  # Wait for manual solve
                                # Try to continue
                                try:
                                    await self.page.goto(f"https://www.google.com/search?q={quote_plus(query)}", wait_until="networkidle", timeout=30000)
                                except Exception:
                                    raise Exception("reCAPTCHA not solved")
                            pass  # URL might not change, continue anyway
                        
                        await self.page.wait_for_load_state("networkidle", timeout=30000)
                        await asyncio.sleep(3)  # Give results time to render
                        
                        # Check again for reCAPTCHA on results page
                        recaptcha_check = await self.page.query_selector("iframe[src*='recaptcha'], div[class*='recaptcha']")
                        if recaptcha_check:
                            await self.broadcast({
                                "type": "status",
                                "message": "⚠️ [STEP 3] reCAPTCHA on results page! Waiting 15 seconds...",
                            })
                            await asyncio.sleep(15)
                        
                        # Wait for results selector to appear
                        try:
                            await self.page.wait_for_selector("div.g", timeout=10000)
                        except Exception:
                            await self.broadcast({
                                "type": "status",
                                "message": "⚠️ [STEP 3] Results selector not found, waiting longer...",
                            })
                            await asyncio.sleep(3)
                        
                        # Validate results loaded
                        result_elements = await self.page.query_selector_all("div.g")
                        if len(result_elements) == 0:
                            # Try alternative selectors
                            result_elements = await self.page.query_selector_all("div[data-ved]")
                            if len(result_elements) == 0:
                                raise Exception("No search results found")
                        await self.broadcast({
                            "type": "status", 
                            "message": f"✅ [STEP 3] Search results loaded ({len(result_elements)} results found)"
                        })
                        screenshot = await self.take_screenshot(force=True)
                        if screenshot:
                            await self.broadcast({"type": "screenshot", "data": screenshot})
                    except Exception as e:
                        await self.broadcast({
                            "type": "status",
                            "message": f"⚠️ [STEP 3] Search timeout: {str(e)[:50]}. Continuing anyway...",
                        })
                        # Try to continue anyway
                        try:
                            await asyncio.sleep(5)  # Give it more time to load
                            result_elements = await self.page.query_selector_all("div.g")
                            if len(result_elements) == 0:
                                result_elements = await self.page.query_selector_all("div[data-ved]")
                            if len(result_elements) > 0:
                                await self.broadcast({
                                    "type": "status",
                                    "message": f"✅ [STEP 3] Found {len(result_elements)} results after extended wait",
                                })
                            screenshot = await self.take_screenshot(force=True)
                            if screenshot:
                                await self.broadcast({"type": "screenshot", "data": screenshot})
                        except Exception:
                            pass

                    # Extract results from multiple pages and PROCESS PDFs IMMEDIATELY
                    for page_num in range(1, max_pages + 1):
                        if self.stop_flag:
                            break

                        if page_num > 1:
                            await self.broadcast({
                                "type": "status",
                                "message": f"⏳ Waiting {delay_between_pages}s before page {page_num}...",
                            })
                            await asyncio.sleep(delay_between_pages)

                            # Click Next button
                            try:
                                next_btn = await self.page.query_selector('a#pnnext, a:has-text("Next")')
                                if next_btn:
                                    await self.broadcast({"type": "status", "message": f"➡️ Clicking 'Next' (page {page_num})..."})
                                    await next_btn.click()
                                    try:
                                        await self.page.wait_for_load_state("networkidle", timeout=30000)
                                        screenshot = await self.take_screenshot(force=True)
                                        if screenshot:
                                            await self.broadcast({"type": "screenshot", "data": screenshot})
                                    except Exception:
                                        await asyncio.sleep(3)  # Fallback wait
                                        screenshot = await self.take_screenshot(force=True)
                                        if screenshot:
                                            await self.broadcast({"type": "screenshot", "data": screenshot})
                                else:
                                    await self.broadcast({"type": "status", "message": "⚠️ No more pages"})
                                    break
                            except Exception:
                                await self.broadcast({"type": "status", "message": "⚠️ Could not navigate to next page"})
                                break

                        # STEP 4: Extract results and CLICK ALL PDFs (query already filters for filetype:pdf)
                        await self.broadcast({"type": "status", "message": f"📋 [STEP 4] Scanning page {page_num} for results..."})
                        try:
                            # Wait for results to be available
                            try:
                                await self.page.wait_for_selector("div.g", timeout=10000)
                            except Exception:
                                # Try alternative selector
                                try:
                                    await self.page.wait_for_selector("div[data-ved]", timeout=5000)
                                except Exception:
                                    pass
                            
                            result_elements = await self.page.query_selector_all("div.g")
                            if len(result_elements) == 0:
                                # Try alternative selector
                                result_elements = await self.page.query_selector_all("div[data-ved]")
                            
                            if len(result_elements) == 0:
                                await self.broadcast({
                                    "type": "status",
                                    "message": f"⚠️ [STEP 4] No result elements found on page {page_num}",
                                })
                                continue
                            await self.broadcast({
                                "type": "status",
                                "message": f"✅ [STEP 4] Found {len(result_elements)} result elements",
                            })
                            pdf_count = 0
                            processed_urls = set()  # Track processed URLs to avoid duplicates

                            for elem in result_elements:
                                try:
                                    title_elem = await elem.query_selector("h3")
                                    link_elem = await elem.query_selector("a")

                                    if not title_elem or not link_elem:
                                        continue

                                    title = await title_elem.inner_text()
                                    url = await link_elem.get_attribute("href")

                                    if not url:
                                        continue

                                    # Extract actual URL from Google redirect URL
                                    if url.startswith("/url?q="):
                                        from urllib.parse import unquote
                                        try:
                                            actual_url = unquote(url.split("&")[0].replace("/url?q=", ""))
                                            url = actual_url
                                        except Exception:
                                            pass

                                    # Skip Google internal URLs and already processed URLs
                                    if "google.com" in url or url.startswith("/") or url in processed_urls:
                                        continue
                                    
                                    processed_urls.add(url)

                                    cite_elem = await elem.query_selector("cite")
                                    display_link = await cite_elem.inner_text() if cite_elem else url.split("/")[2] if "/" in url else ""

                                    # STEP 5: Since query has filetype:pdf, ALL results should be PDFs - CLICK THEM ALL
                                    pdf_count += 1
                                    await self.broadcast({
                                        "type": "status",
                                        "message": f"  📄 [STEP 5.{pdf_count}] Processing result #{pdf_count}: {title[:50]}",
                                    })
                                    
                                    # STEP 6: CLICK THIS RESULT IMMEDIATELY (process now!)
                                    try:
                                        await self.broadcast({
                                            "type": "status",
                                            "message": f"  🖱️ [STEP 6.{pdf_count}] Clicking result #{pdf_count}...",
                                        })
                                        
                                        # Scroll into view FIRST
                                        await link_elem.scroll_into_view_if_needed()
                                        await asyncio.sleep(0.5)
                                        
                                        # Get current URL before click
                                        current_url_before = self.page.url
                                        
                                        # Click the title (most reliable)
                                        await self.broadcast({
                                            "type": "status",
                                            "message": f"  🖱️ Clicking title: {title[:40]}...",
                                        })
                                        
                                        try:
                                            await title_elem.click(timeout=5000)
                                            await self.broadcast({
                                                "type": "status",
                                                "message": f"  ✅ Clicked title element",
                                            })
                                        except Exception as click_err:
                                            # Fallback to link element
                                            await self.broadcast({
                                                "type": "status",
                                                "message": f"  ⚠️ Title click failed, trying link: {str(click_err)[:40]}",
                                            })
                                            try:
                                                await link_elem.click(timeout=5000)
                                                await self.broadcast({
                                                    "type": "status",
                                                    "message": f"  ✅ Clicked link element",
                                                })
                                            except Exception as link_err:
                                                # Final fallback: use JavaScript click
                                                await self.broadcast({
                                                    "type": "status",
                                                    "message": f"  ⚠️ Link click failed, using JS click: {str(link_err)[:40]}",
                                                })
                                                await self.page.evaluate("""
                                                    (element) => {
                                                        element.click();
                                                    }
                                                """, link_elem)
                                                await self.broadcast({
                                                    "type": "status",
                                                    "message": f"  ✅ Clicked via JavaScript",
                                                })
                                        
                                        await asyncio.sleep(2)  # Wait for navigation
                                        
                                        screenshot = await self.take_screenshot(force=True)
                                        if screenshot:
                                            await self.broadcast({"type": "screenshot", "data": screenshot})
                                        
                                        # Verify navigation happened
                                        await asyncio.sleep(1)
                                        current_url_after = self.page.url
                                        
                                        if current_url_after == current_url_before:
                                            await self.broadcast({
                                                "type": "status",
                                                "message": f"  ⚠️ Click did not navigate! Trying direct navigation to: {url[:60]}...",
                                            })
                                            # Fallback: Navigate directly to URL
                                            try:
                                                await self.page.goto(url, wait_until="networkidle", timeout=30000)
                                                await self.broadcast({
                                                    "type": "status",
                                                    "message": f"  ✅ Navigated directly",
                                                })
                                            except Exception as nav_error:
                                                await self.broadcast({
                                                    "type": "status",
                                                    "message": f"  ❌ Direct navigation failed: {str(nav_error)[:60]}. Skipping...",
                                                })
                                                # Go back to search results before continuing
                                                try:
                                                    await self.page.go_back()
                                                    await self.page.wait_for_load_state("networkidle", timeout=10000)
                                                except Exception:
                                                    await self.page.goto(f"https://www.google.com/search?q={quote_plus(query)}", wait_until="networkidle", timeout=15000)
                                                continue  # Skip this result
                                        else:
                                            await self.broadcast({
                                                "type": "status",
                                                "message": f"  ✅ Navigation successful! URL changed to: {current_url_after[:60]}",
                                            })
                                        
                                        # Wait for page to load
                                        try:
                                            await self.page.wait_for_load_state("networkidle", timeout=20000)
                                            await asyncio.sleep(2)
                                            screenshot = await self.take_screenshot(force=True)
                                            if screenshot:
                                                await self.broadcast({"type": "screenshot", "data": screenshot})
                                        except Exception:
                                            await asyncio.sleep(3)  # Fallback wait
                                        
                                        # STEP 7: Extract leads from PDF/page
                                        await self.broadcast({
                                            "type": "status",
                                            "message": f"  📥 [STEP 7.{pdf_count}] Extracting leads from result #{pdf_count}...",
                                        })
                                        
                                        pdf_leads = await self.extract_from_pdf(
                                            url,
                                            title,
                                            display_link,
                                        )
                                        
                                        if pdf_leads:
                                            for lead in pdf_leads:
                                                lead["search_query"] = query
                                            query_leads.extend(pdf_leads)
                                            total_leads_extracted += len(pdf_leads)
                                            # Broadcast real-time update after each PDF
                                            await self.broadcast({
                                                "type": "lead_count",
                                                "count": total_leads_extracted,
                                                "target": target_leads,
                                            })
                                            await self.broadcast({
                                                "type": "status",
                                                "message": f"  ✅ [STEP 7.{pdf_count}] Extracted {len(pdf_leads)} leads | Total: {total_leads_extracted} leads",
                                            })
                                            
                                            # Check if target reached after each PDF
                                            if target_leads > 0 and total_leads_extracted >= target_leads:
                                                await self.broadcast({
                                                    "type": "status",
                                                    "message": f"🎯 Target reached! Extracted {total_leads_extracted} leads (target: {target_leads}). Stopping...",
                                                })
                                                self.stop_flag = True
                                                # Break out of result loop
                                                break
                                        else:
                                            await self.broadcast({
                                                "type": "status",
                                                "message": f"  ⚠️ [STEP 7.{pdf_count}] No leads extracted",
                                            })
                                        
                                        # STEP 8: Go back to search results
                                        await self.broadcast({
                                            "type": "status",
                                            "message": f"  ⬅️ [STEP 8.{pdf_count}] Returning to search results...",
                                        })
                                        try:
                                            await self.page.go_back()
                                            await self.page.wait_for_load_state("networkidle", timeout=15000)
                                            await asyncio.sleep(1)
                                            screenshot = await self.take_screenshot(force=True)
                                            if screenshot:
                                                await self.broadcast({"type": "screenshot", "data": screenshot})
                                        except Exception:
                                            # If back fails, navigate to Google search again
                                            await self.page.goto(f"https://www.google.com/search?q={quote_plus(query)}", wait_until="networkidle", timeout=15000)
                                        
                                    except Exception as e:
                                        import traceback
                                        error_trace = traceback.format_exc()
                                        await self.broadcast({
                                            "type": "status",
                                            "message": f"  ❌ Result #{pdf_count} error: {str(e)[:80]}",
                                        })
                                        # Try to get back to search results
                                        try:
                                            await self.page.go_back()
                                            await self.page.wait_for_load_state("networkidle", timeout=10000)
                                        except Exception:
                                            await self.page.goto(f"https://www.google.com/search?q={quote_plus(query)}", wait_until="networkidle", timeout=15000)

                                except Exception:
                                    continue

                            if pdf_count > 0:
                                await self.broadcast({
                                    "type": "status",
                                    "message": f"✅ Page {page_num}: Processed {pdf_count} result(s)",
                                })
                            else:
                                await self.broadcast({"type": "status", "message": f"⚠️ Page {page_num}: No results found"})

                        except Exception as e:
                            await self.broadcast({
                                "type": "status",
                                "message": f"❌ Error scanning page: {str(e)[:60]}",
                            })
                            # Continue to next page even if this page had errors
                            continue

                    # If target was reached inside the page loop, exit query loop too
                    if self.stop_flag:
                        break

                    # Save leads after each query (CRITICAL: Save to database FIRST, then PDF)
                    if query_leads:
                        all_leads.extend(query_leads)
                        self.all_leads_buffer.extend(query_leads)  # Keep buffer updated
                        # total_leads_extracted already updated per-PDF in inner loop; do not double-count
                        
                        # Broadcast real-time lead count update
                        await self.broadcast({
                            "type": "lead_count",
                            "count": total_leads_extracted,
                            "target": target_leads,
                        })
                        
                        # SAVE TO DATABASE FIRST (incremental save)
                        try:
                            saved_count = save_leads(search_id, query_leads)
                            await self.broadcast({
                                "type": "status",
                                "message": f"💾 Saved {saved_count} leads to database (session #{search_id}) | Total: {total_leads_extracted} leads",
                            })
                        except Exception as e:
                            await self.broadcast({
                                "type": "status",
                                "message": f"⚠️ Database save error: {str(e)[:60]}",
                            })
                        
                        await self.broadcast({
                            "type": "status",
                            "message": f"✅ Query {query_idx + 1} complete: {len(query_leads)} leads extracted | Total: {total_leads_extracted} leads",
                        })
                        
                        # Check if target reached
                        if target_leads > 0 and total_leads_extracted >= target_leads:
                            await self.broadcast({
                                "type": "status",
                                "message": f"🎯 Target reached! Extracted {total_leads_extracted} leads (target: {target_leads}). Stopping...",
                            })
                            self.stop_flag = True
                            break

                        # Save to PDF file (with retry)
                        saved = False
                        for retry in range(2):
                            try:
                                EXPORT_DIR.mkdir(parents=True, exist_ok=True)
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                safe_query = query.replace(" ", "_").replace("@", "at").replace("/", "_")[:30]
                                filename = f"leads_query{query_idx + 1}_{safe_query}_{timestamp}.pdf"
                                filepath = export_to_pdf(query_leads, query=query, filename=filename)
                                
                                await self.broadcast({
                                    "type": "status",
                                    "message": f"💾 PDF saved: {filepath}",
                                })
                                await self.broadcast({
                                    "type": "file_saved",
                                    "path": str(filepath),
                                    "query": query,
                                    "count": len(query_leads),
                                })
                                saved = True
                                break
                            except Exception as e:
                                if retry == 0:
                                    await asyncio.sleep(1)  # Retry once
                                else:
                                    await self.broadcast({
                                        "type": "status",
                                        "message": f"⚠️ PDF save error: {str(e)[:60]}",
                                    })

                        await self.broadcast({"type": "leads", "data": query_leads})
                    else:
                        await self.broadcast({
                            "type": "status",
                            "message": f"⚠️ Query {query_idx + 1}: No leads extracted",
                        })

                    await self.broadcast({"type": "status", "message": ""})
                
                except Exception as e:
                    # Catch any errors in query processing and continue
                    import traceback
                    error_msg = str(e)
                    error_trace = traceback.format_exc()
                    await self.broadcast({
                        "type": "status",
                        "message": f"❌ Query {query_idx + 1} error: {error_msg[:100]}",
                    })
                    await self.broadcast({
                        "type": "status",
                        "message": f"⚠️ Continuing to next query...",
                    })
                    # Log full error for debugging
                    print(f"Query {query_idx + 1} error: {error_trace}")
                    # Save any leads we got before the error
                    if 'query_leads' in locals() and query_leads and 'search_id' in locals() and search_id:
                        try:
                            save_leads(search_id, query_leads)
                            all_leads.extend(query_leads)
                        except Exception:
                            pass
                    continue

            # Final summary - Ensure all data is saved
            await self.broadcast({
                "type": "status",
                "message": f"🎉 Automation complete! {len(all_leads)} total leads extracted",
            })
            
            # CRITICAL: Final database save (ensure nothing is lost)
            if all_leads and self.current_session_id:
                try:
                    # Update final counts
                    from app.database.db import get_connection
                    conn = get_connection()
                    conn.execute(
                        "UPDATE searches SET num_results = ?, num_leads = ? WHERE id = ?",
                        (len(all_leads), len(all_leads), self.current_session_id)
                    )
                    conn.commit()
                    conn.close()
                    await self.broadcast({
                        "type": "status",
                        "message": f"💾 Final database update complete (session #{self.current_session_id})",
                    })
                except Exception as e:
                    await self.broadcast({
                        "type": "status",
                        "message": f"⚠️ Final DB update error: {str(e)[:60]}",
                    })
            
            # Save final combined PDF
            if all_leads:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"all_leads_{timestamp}.pdf"
                    filepath = export_to_pdf(all_leads, query="All Queries", filename=filename)
                    await self.broadcast({
                        "type": "status",
                        "message": f"💾 Final combined PDF saved: {filepath}",
                    })
                    await self.broadcast({
                        "type": "file_saved",
                        "path": str(filepath),
                        "query": "All Queries",
                        "count": len(all_leads),
                    })
                except Exception as e:
                    await self.broadcast({
                        "type": "status",
                        "message": f"⚠️ Final PDF save error: {str(e)[:60]}",
                    })

            await self.broadcast({"type": "complete", "data": all_leads})

        except Exception as e:
            error_msg = str(e)
            await self.broadcast({
                "type": "error",
                "message": f"❌ Automation error: {error_msg}",
            })
            # Save buffer on error
            if self.all_leads_buffer:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"leads_recovered_{timestamp}.pdf"
                    filepath = export_to_pdf(self.all_leads_buffer, query="Recovered Leads", filename=filename)
                    await self.broadcast({
                        "type": "status",
                        "message": f"💾 Recovered leads saved: {filepath}",
                    })
                    await self.broadcast({
                        "type": "file_saved",
                        "path": str(filepath),
                        "query": "Recovered Leads",
                        "count": len(self.all_leads_buffer),
                    })
                except Exception:
                    pass
        finally:
            # CRITICAL: Save buffer to database BEFORE closing
            final_leads = all_leads if 'all_leads' in locals() else self.all_leads_buffer
            
            if final_leads and self.current_session_id:
                try:
                    await self.broadcast({
                        "type": "status",
                        "message": f"💾 Saving {len(final_leads)} leads before closing...",
                    })
                    save_leads(self.current_session_id, final_leads)
                    await self.broadcast({
                        "type": "status",
                        "message": f"✅ Saved to database (session #{self.current_session_id})",
                    })
                except Exception as e:
                    await self.broadcast({
                        "type": "status",
                        "message": f"⚠️ Final save error: {str(e)[:60]}",
                    })
            
            # Cleanup browser (AFTER saving, BEFORE completion signal)
            cleanup_errors = []
            try:
                if self.page:
                    await self.page.close()
            except Exception as e:
                cleanup_errors.append(f"Page close: {str(e)[:30]}")
            try:
                if self.browser:
                    await self.browser.close()
            except Exception as e:
                cleanup_errors.append(f"Browser close: {str(e)[:30]}")
            try:
                if self.playwright:
                    await self.playwright.stop()
            except Exception as e:
                cleanup_errors.append(f"Playwright stop: {str(e)[:30]}")
            
            # CRITICAL: Always send completion signal, even on error
            # Set is_running to False FIRST so UI knows it's done
            self.is_running = False
            self.current_session_id = None
            
            # Send completion signal (multiple attempts)
            completion_sent = False
            for attempt in range(3):
                try:
                    await self.broadcast({
                        "type": "complete",
                        "data": final_leads if final_leads else [],
                    })
                    completion_sent = True
                    break
                except Exception as e:
                    if attempt < 2:
                        await asyncio.sleep(0.5)  # Retry
                    else:
                        # Last attempt failed - log but continue
                        print(f"Failed to send completion signal: {e}")
            
            if cleanup_errors:
                try:
                    await self.broadcast({
                        "type": "status",
                        "message": f"🔚 Browser closed (warnings: {', '.join(cleanup_errors)})",
                    })
                except Exception:
                    pass
            else:
                try:
                    await self.broadcast({"type": "status", "message": "🔚 Browser closed"})
                except Exception:
                    pass


manager = AutomationManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send ping every 30 seconds to keep connection alive
        async def ping_task():
            while True:
                await asyncio.sleep(30)
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
        
        ping_handle = asyncio.create_task(ping_task())
        
        while True:
            try:
                data = await websocket.receive_json()
                command = data.get("command")

                if command == "start":
                    if manager.is_running:
                        await websocket.send_json({
                            "type": "error",
                            "message": "⚠️ Automation already running",
                        })
                        continue
                    
                    queries = data.get("queries", [])
                    max_pages = data.get("max_pages", 10)
                    delay_pages = data.get("delay_pages", 3.0)
                    delay_actions = data.get("delay_actions", 1.0)
                    target_leads = data.get("target_leads", 0)

                    # Run automation in background
                    asyncio.create_task(manager.run_automation(
                        queries=queries,
                        max_pages=max_pages,
                        delay_between_pages=delay_pages,
                        delay_between_actions=delay_actions,
                        target_leads=target_leads,
                    ))

                elif command == "stop":
                    manager.stop_flag = True
                    manager.is_running = False  # Force stop
                    await manager.broadcast({"type": "status", "message": "🛑 Stop requested - saving all leads and stopping automation..."})
                    
                    # Save all leads in buffer before stopping
                    if manager.all_leads_buffer and manager.current_session_id:
                        try:
                            saved_count = save_leads(manager.current_session_id, manager.all_leads_buffer)
                            await manager.broadcast({
                                "type": "status",
                                "message": f"💾 Saved {saved_count} leads to database before stopping",
                            })
                        except Exception as e:
                            await manager.broadcast({
                                "type": "status",
                                "message": f"⚠️ Error saving leads on stop: {str(e)[:60]}",
                            })
                    
                    # Force completion signal with all leads
                    try:
                        await manager.broadcast({
                            "type": "complete",
                            "data": manager.all_leads_buffer if manager.all_leads_buffer else [],
                        })
                    except Exception:
                        pass
                    
            except Exception as e:
                # Log error but keep connection alive
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"WebSocket error: {str(e)[:100]}",
                    })
                except Exception:
                    break

    except WebSocketDisconnect:
        # Save buffer on disconnect
        if manager.all_leads_buffer:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"leads_disconnect_{timestamp}.pdf"
                filepath = export_to_pdf(manager.all_leads_buffer, query="Disconnected Leads", filename=filename)
                print(f"💾 Saved leads on disconnect: {filepath}")
            except Exception:
                pass
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.get("/")
async def root():
    return {"status": "Automation server running", "websocket": "/ws"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
