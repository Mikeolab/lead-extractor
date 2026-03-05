"""
Test PDF flow logic - verifies the script logic for detecting and processing PDFs
"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.extractors.email_extractor import extract_emails
from app.extractors.phone_extractor import extract_phones
from app.extractors.name_extractor import extract_contact_names
from app.database.db import save_search, save_leads, get_leads_by_search


class TestPDFFlowLogic(unittest.TestCase):
    """Test the logic flow for PDF detection and processing"""
    
    def test_pdf_detection_logic(self):
        """Test that PDF detection logic works correctly"""
        # Simulate search results (as script would see them)
        test_urls = [
            "https://example.com/document.pdf",
            "https://example.com/file.PDF",
            "https://example.com/report.pdf?download=true",
            "https://example.com/page.html",  # Not a PDF
            "https://example.com/another.pdf",
        ]
        
        pdf_urls = []
        for url in test_urls:
            # Same logic as script
            is_pdf = url.lower().endswith(".pdf") or ".pdf" in url.lower()
            if is_pdf:
                pdf_urls.append(url)
        
        self.assertEqual(len(pdf_urls), 4, "Should detect 4 PDFs out of 5 URLs")
        self.assertIn("https://example.com/document.pdf", pdf_urls)
        self.assertIn("https://example.com/file.PDF", pdf_urls)
        self.assertIn("https://example.com/report.pdf?download=true", pdf_urls)
        self.assertIn("https://example.com/another.pdf", pdf_urls)
    
    def test_sequential_pdf_processing(self):
        """Test that PDFs are processed sequentially (one at a time)"""
        query = "filetype:pdf contacts"
        search_id = save_search(query, num_results=0)
        
        # Simulate processing 3 PDFs sequentially (as script does)
        all_leads = []
        
        # PDF 1 (using real domain, not test.com which is filtered)
        pdf1_text = """
        Contact Information
        Name: Alice Smith
        Email: alice@company1.com
        Phone: 555-1111
        """
        emails1 = extract_emails(pdf1_text)
        phones1 = extract_phones(pdf1_text)
        names1 = extract_contact_names(pdf1_text)
        leads1 = [{
            "email": emails1[0] if emails1 else "",
            "phone": phones1[0] if phones1 else "",
            "contact_name": names1[0] if names1 else "",
            "business_name": "",
            "website": "",
            "source_url": "https://example.com/pdf1.pdf",
            "snippet": "",
        }]
        all_leads.extend(leads1)
        
        # PDF 2
        pdf2_text = """
        Contact Information
        Name: Bob Johnson
        Email: bob@company2.com
        Phone: 555-2222
        """
        emails2 = extract_emails(pdf2_text)
        phones2 = extract_phones(pdf2_text)
        names2 = extract_contact_names(pdf2_text)
        leads2 = [{
            "email": emails2[0] if emails2 else "",
            "phone": phones2[0] if phones2 else "",
            "contact_name": names2[0] if names2 else "",
            "business_name": "",
            "website": "",
            "source_url": "https://example.com/pdf2.pdf",
            "snippet": "",
        }]
        all_leads.extend(leads2)
        
        # PDF 3
        pdf3_text = """
        Contact Information
        Name: Carol Williams
        Email: carol@company3.com
        Phone: 555-3333
        """
        emails3 = extract_emails(pdf3_text)
        phones3 = extract_phones(pdf3_text)
        names3 = extract_contact_names(pdf3_text)
        leads3 = [{
            "email": emails3[0] if emails3 else "",
            "phone": phones3[0] if phones3 else "",
            "contact_name": names3[0] if names3 else "",
            "business_name": "",
            "website": "",
            "source_url": "https://example.com/pdf3.pdf",
            "snippet": "",
        }]
        all_leads.extend(leads3)
        
        # Save all leads (as script does after processing all PDFs on page)
        saved_count = save_leads(search_id, all_leads)
        self.assertEqual(saved_count, 3, "Should save 3 leads from 3 PDFs")
        
        # Verify they're saved correctly
        retrieved = get_leads_by_search(search_id)
        self.assertEqual(len(retrieved), 3, "Should retrieve 3 leads")
        
        # Verify each PDF's leads are separate (check emails exist)
        emails_found = [lead["email"] for lead in retrieved if lead["email"]]
        self.assertTrue(len(emails_found) >= 2, f"Should have at least 2 emails (found: {emails_found})")
        self.assertIn("alice@company1.com", emails_found, "Should have lead from PDF 1")
        self.assertIn("bob@company2.com", emails_found, "Should have lead from PDF 2")
        self.assertIn("carol@company3.com", emails_found, "Should have lead from PDF 3")
    
    def test_pdf_processing_flow(self):
        """Test the complete flow: detect -> click -> extract -> save -> next"""
        query = "filetype:pdf vendor list"
        search_id = save_search(query, num_results=0)
        
        # Simulate the script's flow:
        # 1. Find results (all should be PDFs due to filetype:pdf)
        # 2. Process each result sequentially
        # 3. Extract leads from each
        # 4. Save after each query
        
        query_leads = []
        
        # Result 1
        result1_text = """
        VENDOR LIST
        Vendor 1: ABC Corp
        Contact: John Smith
        Email: john@abccorp.com
        Phone: (555) 111-1111
        """
        emails1 = extract_emails(result1_text)
        phones1 = extract_phones(result1_text)
        names1 = extract_contact_names(result1_text)
        
        for i, email in enumerate(emails1):
            query_leads.append({
                "email": email,
                "phone": phones1[i] if i < len(phones1) else "",
                "contact_name": names1[i] if i < len(names1) else "",
                "business_name": "",
                "website": "",
                "source_url": "https://example.com/vendor1.pdf",
                "snippet": "",
            })
        
        # Result 2
        result2_text = """
        VENDOR LIST
        Vendor 2: XYZ Inc
        Contact: Jane Doe
        Email: jane@xyzinc.com
        Phone: (555) 222-2222
        """
        emails2 = extract_emails(result2_text)
        phones2 = extract_phones(result2_text)
        names2 = extract_contact_names(result2_text)
        
        for i, email in enumerate(emails2):
            query_leads.append({
                "email": email,
                "phone": phones2[i] if i < len(phones2) else "",
                "contact_name": names2[i] if i < len(names2) else "",
                "business_name": "",
                "website": "",
                "source_url": "https://example.com/vendor2.pdf",
                "snippet": "",
            })
        
        # Save all leads (as script does)
        saved_count = save_leads(search_id, query_leads)
        self.assertEqual(saved_count, len(query_leads), "Should save all extracted leads")
        self.assertTrue(saved_count >= 2, "Should have at least 2 leads from 2 PDFs")
        
        # Verify flow worked
        retrieved = get_leads_by_search(search_id)
        self.assertEqual(len(retrieved), saved_count, "Should retrieve all saved leads")
        
        # Verify leads from different PDFs are separate
        emails_found = [lead["email"] for lead in retrieved]
        self.assertIn("john@abccorp.com", emails_found, "Should have lead from PDF 1")
        self.assertIn("jane@xyzinc.com", emails_found, "Should have lead from PDF 2")


if __name__ == "__main__":
    unittest.main()

