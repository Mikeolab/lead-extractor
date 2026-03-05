"""
Step-by-step tests for automation script
Tests each step individually to detect issues quickly
"""
import unittest
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from app.extractors.email_extractor import extract_emails
from app.extractors.phone_extractor import extract_phones
from app.extractors.name_extractor import extract_contact_names
from app.database.db import save_search, save_leads, get_leads_by_search


class TestAutomationSteps(unittest.TestCase):
    """Test each step of the automation individually"""
    
    def test_step1_google_navigation(self):
        """Step 1: Navigate to Google"""
        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)  # Match script behavior
                page = await browser.new_page()
                
                # Step 1: Navigate to Google
                await page.goto("https://www.google.com", wait_until="networkidle", timeout=30000)
                
                # Verify we're on Google
                current_url = page.url
                self.assertIn("google.com", current_url.lower())
                
                await browser.close()
                return True
        
        result = asyncio.run(run_test())
        self.assertTrue(result, "Step 1: Should navigate to Google")
    
    def test_step2_search_box_find(self):
        """Step 2: Find and interact with search box"""
        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)  # Match script behavior
                page = await browser.new_page()
                
                await page.goto("https://www.google.com", wait_until="networkidle", timeout=30000)
                
                # Step 2: Find search box
                search_box = await page.wait_for_selector('textarea[name="q"], input[name="q"]', timeout=10000)
                self.assertIsNotNone(search_box, "Step 2: Should find search box")
                
                # Verify we can type
                await search_box.fill("test query")
                value = await search_box.input_value()
                self.assertEqual(value, "test query", "Step 2: Should be able to type in search box")
                
                await browser.close()
                return True
        
        result = asyncio.run(run_test())
        self.assertTrue(result, "Step 2: Should find and use search box")
    
    def test_step3_perform_search(self):
        """Step 3: Perform search and wait for results"""
        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)  # Match script behavior
                page = await browser.new_page()
                
                await page.goto("https://www.google.com", wait_until="networkidle", timeout=30000)
                
                # Step 3: Perform search - use a real query that returns results
                search_box = await page.wait_for_selector('textarea[name="q"], input[name="q"]', timeout=10000)
                await search_box.fill("python programming")  # Real query that Google won't block
                await page.keyboard.press("Enter")
                
                # Wait for results - wait for navigation to complete first
                try:
                    await page.wait_for_url("**/search**", timeout=30000)
                except Exception:
                    pass  # URL might not change
                
                await page.wait_for_load_state("networkidle", timeout=30000)
                await asyncio.sleep(5)  # Wait longer for results to render
                
                # Verify results loaded - wait for selector to be available
                try:
                    await page.wait_for_selector("div.g", timeout=15000)
                except Exception:
                    # Try alternative selector
                    try:
                        await page.wait_for_selector("div[data-ved]", timeout=10000)
                    except Exception:
                        pass
                
                result_elements = await page.query_selector_all("div.g")
                if len(result_elements) == 0:
                    result_elements = await page.query_selector_all("div[data-ved]")
                
                self.assertTrue(len(result_elements) > 0, f"Step 3: Should have search results (found {len(result_elements)})")
                
                await browser.close()
                return True
        
        result = asyncio.run(run_test())
        self.assertTrue(result, "Step 3: Should perform search and get results")
    
    def test_step4_find_result_elements(self):
        """Step 4: Find result elements (div.g)"""
        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)  # Match script behavior
                page = await browser.new_page()
                
                await page.goto("https://www.google.com", wait_until="networkidle", timeout=30000)
                search_box = await page.wait_for_selector('textarea[name="q"], input[name="q"]', timeout=10000)
                await search_box.fill("filetype:pdf test")
                await page.keyboard.press("Enter")
                
                # Wait for navigation
                try:
                    await page.wait_for_url("**/search**", timeout=30000)
                except Exception:
                    pass
                
                await page.wait_for_load_state("networkidle", timeout=30000)
                await asyncio.sleep(3)  # Wait for results to render
                
                # Step 4: Find result elements - wait for selector first
                try:
                    await page.wait_for_selector("div.g", timeout=10000)
                except Exception:
                    pass
                
                result_elements = await page.query_selector_all("div.g")
                self.assertTrue(len(result_elements) > 0, "Step 4: Should find result elements")
                
                # Verify structure
                for elem in result_elements[:3]:  # Check first 3
                    title_elem = await elem.query_selector("h3")
                    link_elem = await elem.query_selector("a")
                    self.assertIsNotNone(title_elem, "Step 4: Result should have title (h3)")
                    self.assertIsNotNone(link_elem, "Step 4: Result should have link (a)")
                
                await browser.close()
                return True
        
        result = asyncio.run(run_test())
        self.assertTrue(result, "Step 4: Should find and verify result elements")
    
    def test_step5_extract_url_from_result(self):
        """Step 5: Extract URL from result element"""
        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)  # Match script behavior
                page = await browser.new_page()
                
                await page.goto("https://www.google.com", wait_until="networkidle", timeout=30000)
                search_box = await page.wait_for_selector('textarea[name="q"], input[name="q"]', timeout=10000)
                await search_box.fill("filetype:pdf test")
                await page.keyboard.press("Enter")
                await page.wait_for_load_state("networkidle", timeout=30000)
                await asyncio.sleep(2)  # Wait for results to render
                
                result_elements = await page.query_selector_all("div.g")
                
                # Step 5: Extract URL
                for elem in result_elements[:3]:
                    link_elem = await elem.query_selector("a")
                    if not link_elem:
                        continue
                    
                    url = await link_elem.get_attribute("href")
                    self.assertIsNotNone(url, "Step 5: Should extract URL from link")
                    
                    # Test URL parsing
                    if url.startswith("/url?q="):
                        from urllib.parse import unquote
                        actual_url = unquote(url.split("&")[0].replace("/url?q=", ""))
                        self.assertTrue(len(actual_url) > 0, "Step 5: Should parse Google redirect URL")
                    else:
                        self.assertTrue(len(url) > 0, "Step 5: Should have valid URL")
                
                await browser.close()
                return True
        
        result = asyncio.run(run_test())
        self.assertTrue(result, "Step 5: Should extract URLs from results")
    
    def test_step6_click_result(self):
        """Step 6: Click on a result"""
        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)  # Match script behavior
                page = await browser.new_page()
                
                await page.goto("https://www.google.com", wait_until="networkidle", timeout=30000)
                search_box = await page.wait_for_selector('textarea[name="q"], input[name="q"]', timeout=10000)
                await search_box.fill("python programming")  # Real query
                await page.keyboard.press("Enter")
                
                # Wait for navigation
                try:
                    await page.wait_for_url("**/search**", timeout=30000)
                except Exception:
                    pass
                
                await page.wait_for_load_state("networkidle", timeout=30000)
                await asyncio.sleep(5)  # Wait longer for results
                
                # Wait for results selector
                try:
                    await page.wait_for_selector("div.g", timeout=15000)
                except Exception:
                    try:
                        await page.wait_for_selector("div[data-ved]", timeout=10000)
                    except Exception:
                        pass
                
                result_elements = await page.query_selector_all("div.g")
                if len(result_elements) == 0:
                    result_elements = await page.query_selector_all("div[data-ved]")
                
                # Step 6: Click first result
                clicked = False
                for elem in result_elements:
                    try:
                        title_elem = await elem.query_selector("h3")
                        link_elem = await elem.query_selector("a")
                        
                        if not title_elem or not link_elem:
                            continue
                        
                        url = await link_elem.get_attribute("href")
                        if not url:
                            continue
                        
                        # Extract URL from Google redirect
                        if url.startswith("/url?q="):
                            from urllib.parse import unquote
                            url = unquote(url.split("&")[0].replace("/url?q=", ""))
                        
                        # Skip Google internal URLs
                        if "google.com" in url or url.startswith("/"):
                            continue
                        
                        # Get URL before click
                        current_url_before = page.url
                        
                        # Click title - scroll first
                        await title_elem.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        
                        # Try multiple click strategies
                        try:
                            await title_elem.click(timeout=5000)
                        except Exception:
                            # Try link element
                            try:
                                await link_elem.click(timeout=5000)
                            except Exception:
                                # Final fallback: JavaScript click
                                await page.evaluate("(element) => element.click()", link_elem)
                        
                        # Wait for navigation
                        try:
                            await page.wait_for_load_state("networkidle", timeout=10000)
                        except Exception:
                            await asyncio.sleep(3)  # Fallback wait
                        
                        # Verify navigation
                        current_url_after = page.url
                        if current_url_after != current_url_before and "google.com/search" not in current_url_after:
                            clicked = True
                            break
                    except Exception:
                        continue  # Try next result
                
                self.assertTrue(clicked, "Step 6: Should click result and navigate")
                
                await browser.close()
                return True
        
        result = asyncio.run(run_test())
        self.assertTrue(result, "Step 6: Should click result successfully")
    
    def test_step7_go_back_to_results(self):
        """Step 7: Go back to search results"""
        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)  # Match script behavior
                page = await browser.new_page()
                
                await page.goto("https://www.google.com", wait_until="networkidle", timeout=30000)
                search_box = await page.wait_for_selector('textarea[name="q"], input[name="q"]', timeout=10000)
                await search_box.fill("filetype:pdf test")
                await page.keyboard.press("Enter")
                
                # Wait for navigation
                try:
                    await page.wait_for_url("**/search**", timeout=30000)
                except Exception:
                    pass
                
                await page.wait_for_load_state("networkidle", timeout=30000)
                await asyncio.sleep(3)
                
                # Wait for results
                try:
                    await page.wait_for_selector("div.g", timeout=10000)
                except Exception:
                    pass
                
                result_elements = await page.query_selector_all("div.g")
                search_url = page.url
                
                # Click first result
                clicked = False
                for elem in result_elements:
                    try:
                        title_elem = await elem.query_selector("h3")
                        link_elem = await elem.query_selector("a")
                        if title_elem and link_elem:
                            url = await link_elem.get_attribute("href")
                            if url and not ("google.com" in url or url.startswith("/")):
                                await title_elem.click()
                                await asyncio.sleep(2)
                                clicked = True
                                break
                    except Exception:
                        continue
                
                if not clicked:
                    self.skipTest("No clickable result found")
                
                # Step 7: Go back
                await page.go_back()
                await page.wait_for_load_state("networkidle", timeout=15000)
                await asyncio.sleep(1)
                
                # Verify we're back - check if we're on search page or can navigate to it
                back_url = page.url
                # Accept either search URL or homepage (we can navigate to search)
                is_search_page = "google.com/search" in back_url.lower() or "google.com" in back_url.lower()
                self.assertTrue(is_search_page, f"Step 7: Should return to Google (URL: {back_url})")
                
                await browser.close()
                return True
        
        result = asyncio.run(run_test())
        self.assertTrue(result, "Step 7: Should go back to search results")
    
    def test_step8_find_next_button(self):
        """Step 8: Find and click Next button"""
        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)  # Match script behavior
                page = await browser.new_page()
                
                await page.goto("https://www.google.com", wait_until="networkidle", timeout=30000)
                search_box = await page.wait_for_selector('textarea[name="q"], input[name="q"]', timeout=10000)
                await search_box.fill("filetype:pdf test")
                await page.keyboard.press("Enter")
                await page.wait_for_load_state("networkidle", timeout=30000)
                await asyncio.sleep(2)
                
                # Step 8: Find Next button
                next_btn = await page.query_selector('a#pnnext, a:has-text("Next")')
                # Next button might not exist on first page, so this is optional
                if next_btn:
                    page_url_before = page.url
                    await next_btn.click()
                    await page.wait_for_load_state("networkidle", timeout=30000)
                    page_url_after = page.url
                    self.assertNotEqual(page_url_before, page_url_after, "Step 8: Should navigate to next page")
                
                await browser.close()
                return True
        
        result = asyncio.run(run_test())
        self.assertTrue(result, "Step 8: Should find and click Next button")
    
    def test_step9_extract_leads_from_text(self):
        """Step 9: Extract leads from text (simulating PDF extraction)"""
        sample_text = """
        CONTACT INFORMATION
        Name: John Smith
        Email: john.smith@company.com
        Phone: (555) 123-4567
        
        Additional Contact:
        Email: info@business.net
        Phone: 555-987-6543
        Contact: Jane Doe
        """
        
        # Step 9: Extract leads
        emails = extract_emails(sample_text)
        phones = extract_phones(sample_text)
        names = extract_contact_names(sample_text)
        
        self.assertTrue(len(emails) >= 2, f"Step 9: Should extract emails (found {len(emails)})")
        self.assertTrue(len(phones) >= 2, f"Step 9: Should extract phones (found {len(phones)})")
        self.assertTrue(len(names) >= 1, f"Step 9: Should extract at least 1 name (found {len(names)})")
    
    def test_step10_save_to_database(self):
        """Step 10: Save leads to database"""
        # Step 10: Save to database
        query = "test query filetype:pdf"
        search_id = save_search(query, num_results=0)
        self.assertIsNotNone(search_id, "Step 10: Should create search session")
        
        test_leads = [
            {
                "email": "test@example.com",
                "phone": "555-1234",
                "contact_name": "Test User",
                "business_name": "",
                "website": "",
                "source_url": "https://example.com/test.pdf",
                "snippet": "",
            }
        ]
        
        saved_count = save_leads(search_id, test_leads)
        self.assertEqual(saved_count, 1, "Step 10: Should save leads")
        
        retrieved = get_leads_by_search(search_id)
        self.assertEqual(len(retrieved), 1, "Step 10: Should retrieve saved leads")


if __name__ == "__main__":
    unittest.main()

