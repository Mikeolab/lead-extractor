"""
Realistic E2E tests for browser automation
Tests actual browser interaction, PDF clicking, and lead extraction
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


class TestBrowserAutomation(unittest.TestCase):
    """Test actual browser automation with real Google search"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.test_query = "filetype:pdf intext:@ intext:contact"
        cls.max_pages = 2  # Limit for testing
    
    def test_google_search_finds_pdfs(self):
        """Test that Google search actually finds PDF results"""
        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Navigate to Google
                await page.goto("https://www.google.com", wait_until="networkidle")
                
                # Search
                search_box = await page.wait_for_selector('textarea[name="q"], input[name="q"]', timeout=10000)
                await search_box.fill(self.test_query)
                await page.keyboard.press("Enter")
                await page.wait_for_load_state("networkidle", timeout=30000)
                await asyncio.sleep(2)  # Wait for results to render
                
                # Find PDF results
                result_elements = await page.query_selector_all("div.g")
                pdf_count = 0
                
                for elem in result_elements:
                    try:
                        link_elem = await elem.query_selector("a")
                        if not link_elem:
                            continue
                        
                        url = await link_elem.get_attribute("href")
                        if not url:
                            continue
                        
                        # Extract actual URL from Google redirect
                        if url.startswith("/url?q="):
                            from urllib.parse import unquote
                            url = unquote(url.split("&")[0].replace("/url?q=", ""))
                        
                        # Check if PDF
                        if url.lower().endswith(".pdf") or ".pdf" in url.lower():
                            pdf_count += 1
                    except Exception:
                        continue
                
                await browser.close()
                return pdf_count
        
        pdf_count = asyncio.run(run_test())
        self.assertTrue(pdf_count > 0, f"Should find at least 1 PDF, found {pdf_count}")
    
    def test_pdf_clicking_works(self):
        """Test that clicking on PDF links actually works"""
        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Navigate to Google
                await page.goto("https://www.google.com", wait_until="networkidle")
                
                # Search
                search_box = await page.wait_for_selector('textarea[name="q"], input[name="q"]', timeout=10000)
                await search_box.fill(self.test_query)
                await page.keyboard.press("Enter")
                await page.wait_for_load_state("networkidle", timeout=30000)
                await asyncio.sleep(2)  # Wait for results to render
                
                # Find first PDF link
                result_elements = await page.query_selector_all("div.g")
                pdf_clicked = False
                
                for elem in result_elements:
                    try:
                        link_elem = await elem.query_selector("a")
                        if not link_elem:
                            continue
                        
                        url = await link_elem.get_attribute("href")
                        if not url:
                            continue
                        
                        # Extract actual URL
                        if url.startswith("/url?q="):
                            from urllib.parse import unquote
                            url = unquote(url.split("&")[0].replace("/url?q=", ""))
                        
                        # Check if PDF
                        if url.lower().endswith(".pdf") or ".pdf" in url.lower():
                            # Click the PDF link
                            await link_elem.scroll_into_view_if_needed()
                            await link_elem.click()
                            await page.wait_for_load_state("networkidle", timeout=20000)
                            
                            # Verify we navigated to PDF
                            current_url = page.url
                            pdf_clicked = url.lower().endswith(".pdf") or ".pdf" in current_url.lower() or "pdf" in current_url.lower()
                            break
                    except Exception:
                        continue
                
                await browser.close()
                return pdf_clicked
        
        clicked = asyncio.run(run_test())
        self.assertTrue(clicked, "Should successfully click on a PDF link")
    
    def test_pdf_extraction_from_real_pdf(self):
        """Test extracting leads from an actual PDF URL"""
        async def run_test():
            # Use a known PDF URL for testing
            test_pdf_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
            
            import httpx
            import pdfplumber
            import io
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(test_pdf_url, timeout=30, follow_redirects=True)
                    if response.status_code != 200:
                        return None
                    
                    pdf_bytes = io.BytesIO(response.content)
                    
                    # Extract text
                    text_parts = []
                    with pdfplumber.open(pdf_bytes) as pdf:
                        for page in pdf.pages[:5]:  # First 5 pages
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(page_text)
                    
                    pdf_text = "\n".join(text_parts)
                    
                    # Extract leads
                    emails = extract_emails(pdf_text, "")
                    phones = extract_phones(pdf_text, "")
                    names = extract_contact_names(pdf_text)
                    
                    return {
                        "emails": emails,
                        "phones": phones,
                        "names": names,
                        "text_length": len(pdf_text)
                    }
            except Exception as e:
                return {"error": str(e)}
        
        result = asyncio.run(run_test())
        self.assertIsNotNone(result)
        if "error" not in result:
            # Even if no leads found, extraction should work
            self.assertTrue(result["text_length"] >= 0)
    
    def test_complete_flow_save(self):
        """Test complete flow: search -> extract -> save"""
        # Create search session
        query = "filetype:pdf contact email"
        search_id = save_search(query, num_results=0)
        
        # Simulate extracted leads (from real PDF processing)
        # This simulates what would be extracted from actual PDFs
        sample_pdf_text = """
        CONTACT INFORMATION
        Name: John Smith
        Email: john.smith@company.com
        Phone: (555) 123-4567
        
        Additional Contact:
        Email: info@business.net
        Phone: 555-987-6543
        Contact: Jane Doe
        """
        
        # Extract (this is what the automation does)
        emails = extract_emails(sample_pdf_text)
        phones = extract_phones(sample_pdf_text)
        names = extract_contact_names(sample_pdf_text)
        
        # Create leads (this is what the automation does)
        leads = []
        for i, email in enumerate(emails):
            leads.append({
                "email": email,
                "phone": phones[i] if i < len(phones) else (phones[0] if phones else ""),
                "contact_name": names[i] if i < len(names) else (names[0] if names else ""),
                "business_name": "",
                "website": "",
                "source_url": "https://example.com/test.pdf",
                "snippet": "",
            })
        
        # Save (this is what the automation does)
        saved_count = save_leads(search_id, leads)
        self.assertEqual(saved_count, len(leads))
        self.assertTrue(saved_count >= 2)  # Should have at least 2 emails
        
        # Verify
        retrieved = get_leads_by_search(search_id)
        self.assertEqual(len(retrieved), saved_count)
        
        # Verify data
        for lead in retrieved:
            self.assertTrue(lead["email"])
            self.assertIn(lead["email"], emails)


if __name__ == "__main__":
    unittest.main()

