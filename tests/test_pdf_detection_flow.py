"""
Test PDF detection and extraction flow
Verifies that PDFs are detected, clicked, and leads extracted
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


class TestPDFDetectionFlow(unittest.TestCase):
    """Test the complete PDF detection and extraction flow"""
    
    def test_pdf_detection_in_results(self):
        """Test that PDFs are detected in Google search results"""
        async def run_test():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                page = await browser.new_page()
                
                # Navigate and search
                await page.goto("https://www.google.com", wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)
                
                search_box = await page.wait_for_selector('textarea[name="q"], input[name="q"]', timeout=10000)
                await search_box.fill("filetype:pdf python tutorial")
                await page.keyboard.press("Enter")
                
                # Wait for results
                try:
                    await page.wait_for_url("**/search**", timeout=30000)
                except Exception:
                    pass
                await page.wait_for_load_state("networkidle", timeout=30000)
                await asyncio.sleep(5)
                
                # Find results
                try:
                    await page.wait_for_selector("div.g", timeout=15000)
                except Exception:
                    pass
                
                result_elements = await page.query_selector_all("div.g")
                if len(result_elements) == 0:
                    result_elements = await page.query_selector_all("div[data-ved]")
                
                # Check for PDFs in results
                pdf_count = 0
                for elem in result_elements:
                    try:
                        link_elem = await elem.query_selector("a")
                        if not link_elem:
                            continue
                        
                        url = await link_elem.get_attribute("href")
                        if not url:
                            continue
                        
                        # Extract URL from Google redirect
                        if url.startswith("/url?q="):
                            from urllib.parse import unquote
                            url = unquote(url.split("&")[0].replace("/url?q=", ""))
                        
                        # Check if PDF
                        if url.lower().endswith(".pdf") or ".pdf" in url.lower():
                            pdf_count += 1
                    except Exception:
                        continue
                
                await browser.close()
                return pdf_count > 0
        
        result = asyncio.run(run_test())
        self.assertTrue(result, "Should detect at least one PDF in search results")
    
    def test_pdf_extraction_workflow(self):
        """Test complete workflow: detect PDF -> extract leads -> save"""
        # Create search session
        query = "filetype:pdf contact information"
        search_id = save_search(query, num_results=0)
        
        # Simulate PDF text (what would be extracted)
        pdf_text = """
        CONTACT INFORMATION
        Company: ABC Services Inc.
        Contact Person: John Smith
        Email: john.smith@abcservices.com
        Phone: (555) 123-4567
        
        Additional Contacts:
        Email: info@abcservices.com
        Phone: 555-987-6543
        Contact: Jane Doe
        
        Email: support@abcservices.com
        Phone: (555) 555-5555
        Contact: Bob Johnson
        """
        
        # Extract leads (simulating what automation does)
        emails = extract_emails(pdf_text)
        phones = extract_phones(pdf_text)
        names = extract_contact_names(pdf_text)
        
        # Verify extraction
        self.assertTrue(len(emails) >= 3, f"Should extract at least 3 emails (found {len(emails)})")
        self.assertTrue(len(phones) >= 3, f"Should extract at least 3 phones (found {len(phones)})")
        self.assertTrue(len(names) >= 1, f"Should extract at least 1 name (found {len(names)})")
        
        # Create leads (as automation does)
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
        
        # Save leads
        saved_count = save_leads(search_id, leads)
        self.assertEqual(saved_count, len(leads), "Should save all extracted leads")
        
        # Verify saved
        retrieved = get_leads_by_search(search_id)
        self.assertEqual(len(retrieved), saved_count, "Should retrieve all saved leads")
        
        # Verify data integrity
        for lead in retrieved:
            self.assertTrue(lead["email"], "Each lead should have an email")
            self.assertIn(lead["email"], emails, "Email should match extracted emails")
    
    def test_multiple_pdf_processing(self):
        """Test processing multiple PDFs sequentially"""
        query = "filetype:pdf business contacts"
        search_id = save_search(query, num_results=0)
        
        # Simulate multiple PDFs
        pdf_texts = [
            "Contact: Alice Brown, Email: alice@company1.com, Phone: 555-1111",
            "Contact: Bob Green, Email: bob@company2.com, Phone: 555-2222",
            "Contact: Carol Blue, Email: carol@company3.com, Phone: 555-3333",
        ]
        
        all_leads = []
        for pdf_text in pdf_texts:
            emails = extract_emails(pdf_text)
            phones = extract_phones(pdf_text)
            names = extract_contact_names(pdf_text)
            
            for i, email in enumerate(emails):
                all_leads.append({
                    "email": email,
                    "phone": phones[i] if i < len(phones) else "",
                    "contact_name": names[i] if i < len(names) else "",
                    "business_name": "",
                    "website": "",
                    "source_url": f"https://example.com/pdf{len(all_leads)}.pdf",
                    "snippet": "",
                })
        
        # Save all leads
        saved_count = save_leads(search_id, all_leads)
        self.assertEqual(saved_count, len(all_leads), "Should save all leads from multiple PDFs")
        
        # Verify
        retrieved = get_leads_by_search(search_id)
        self.assertEqual(len(retrieved), len(all_leads), "Should retrieve all leads")
        self.assertEqual(len(retrieved), 3, "Should have 3 leads from 3 PDFs")


if __name__ == "__main__":
    unittest.main()

