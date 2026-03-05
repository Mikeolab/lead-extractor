"""
End-to-end test for search and save functionality
Tests the actual search -> extract -> save flow
"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.db import save_search, save_leads, get_leads_by_search, get_recent_searches, get_lead_stats
from app.extractors.email_extractor import extract_emails
from app.extractors.phone_extractor import extract_phones
from app.extractors.name_extractor import extract_contact_names, extract_names_from_email


class TestSearchAndSave(unittest.TestCase):
    """Test search and save functionality"""
    
    def test_search_creates_session(self):
        """Test that search creates a session"""
        query = "test query filetype:pdf"
        search_id = save_search(query, num_results=0)
        
        self.assertIsNotNone(search_id)
        self.assertIsInstance(search_id, int)
        
        # Verify session exists
        searches = get_recent_searches(limit=10)
        found = [s for s in searches if s["id"] == search_id]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["query"], query)
    
    def test_save_leads_to_session(self):
        """Test saving leads to a session"""
        # Create search session
        query = "plumbers in california filetype:pdf"
        search_id = save_search(query, num_results=0)
        
        # Create sample leads (simulating extracted from PDF)
        leads = [
            {
                "email": "contact@plumbing.com",
                "phone": "(555) 123-4567",
                "contact_name": "John Smith",
                "business_name": "",
                "website": "",
                "source_url": "https://example.com/invoice.pdf",
                "snippet": "",
            },
            {
                "email": "info@plumbers.com",
                "phone": "555-987-6543",
                "contact_name": "Jane Doe",
                "business_name": "",
                "website": "",
                "source_url": "https://example.com/quote.pdf",
                "snippet": "",
            }
        ]
        
        # Save leads
        saved_count = save_leads(search_id, leads)
        self.assertEqual(saved_count, 2)
        
        # Verify leads were saved
        retrieved = get_leads_by_search(search_id)
        self.assertEqual(len(retrieved), 2)
        self.assertEqual(retrieved[0]["email"], "contact@plumbing.com")
        self.assertEqual(retrieved[1]["email"], "info@plumbers.com")
    
    def test_extract_and_save_pipeline(self):
        """Test complete extract -> save pipeline"""
        # Simulate PDF text extraction
        pdf_text = """
        VENDOR INVOICE
        Company: ABC Plumbing Services
        Contact: Mike Johnson
        Email: mike@abcplumbing.com
        Phone: (555) 123-4567
        
        Additional Contact:
        Email: support@abcplumbing.com
        Phone: 555-987-6543
        Contact Person: Sarah Williams
        """
        
        # Extract leads
        emails = extract_emails(pdf_text)
        phones = extract_phones(pdf_text)
        names = extract_contact_names(pdf_text)
        
        # Verify extraction worked
        self.assertTrue(len(emails) >= 2)
        self.assertTrue(len(phones) >= 2)
        self.assertTrue(len(names) >= 1)
        
        # Create search session
        query = "plumbing services filetype:pdf"
        search_id = save_search(query, num_results=0)
        
        # Create lead structure
        leads = []
        for i, email in enumerate(emails):
            leads.append({
                "email": email,
                "phone": phones[i] if i < len(phones) else (phones[0] if phones else ""),
                "contact_name": names[i] if i < len(names) else (names[0] if names else ""),
                "business_name": "",
                "website": "",
                "source_url": "https://example.com/invoice.pdf",
                "snippet": "",
            })
        
        # Save leads
        saved_count = save_leads(search_id, leads)
        self.assertEqual(saved_count, len(leads))
        self.assertTrue(saved_count >= 2)
        
        # Verify saved
        retrieved = get_leads_by_search(search_id)
        self.assertEqual(len(retrieved), saved_count)
        
        # Verify data integrity
        for lead in retrieved:
            self.assertTrue(lead["email"])  # All should have email
            self.assertTrue(lead["email"] in emails)  # Should match extracted emails
    
    def test_example_query_save(self):
        """Test with the actual example query"""
        # Example query from user
        query = "mike@yahoo.com + sbcglobal.net + Vendor invoice + bellsouth.net + pdf"
        
        # Create session
        search_id = save_search(query, num_results=0)
        
        # Simulate extracted PDF text
        pdf_text = """
        VENDOR INVOICE
        Invoice #: INV-2024-001
        
        Vendor: ABC Services
        Contact: Mike Johnson
        Email: mike@yahoo.com
        Phone: (555) 123-4567
        
        Billing Contact:
        Email: billing@sbcglobal.net
        Phone: 555-987-6543
        Contact: Jane Smith
        
        Client Contact:
        Email: client@bellsouth.net
        Phone: (555) 555-5555
        """
        
        # Extract
        emails = extract_emails(pdf_text)
        phones = extract_phones(pdf_text)
        names = extract_contact_names(pdf_text)
        
        # Verify extraction
        self.assertIn("mike@yahoo.com", emails)
        self.assertTrue(len(emails) >= 2)
        self.assertTrue(len(phones) >= 2)
        
        # Create leads
        leads = []
        for i, email in enumerate(emails):
            leads.append({
                "email": email,
                "phone": phones[i] if i < len(phones) else (phones[0] if phones else ""),
                "contact_name": names[i] if i < len(names) else (names[0] if names else ""),
                "business_name": "",
                "website": "",
                "source_url": "https://example.com/vendor_invoice.pdf",
                "snippet": "",
            })
        
        # Save
        saved_count = save_leads(search_id, leads)
        self.assertEqual(saved_count, len(leads))
        
        # Verify
        retrieved = get_leads_by_search(search_id)
        self.assertEqual(len(retrieved), saved_count)
        
        # Check stats
        stats = get_lead_stats()
        self.assertTrue(stats["total_searches"] > 0)
        self.assertTrue(stats["total_leads"] > 0)
    
    def test_multiple_sessions(self):
        """Test multiple search sessions don't interfere"""
        # Create multiple sessions
        query1 = "query 1 filetype:pdf"
        query2 = "query 2 filetype:pdf"
        
        search1 = save_search(query1)
        search2 = save_search(query2)
        
        # Save different leads to each
        leads1 = [{"email": "test1@example.com", "phone": "555-1111", "contact_name": "Test 1", "business_name": "", "website": "", "source_url": "", "snippet": ""}]
        leads2 = [{"email": "test2@example.com", "phone": "555-2222", "contact_name": "Test 2", "business_name": "", "website": "", "source_url": "", "snippet": ""}]
        
        save_leads(search1, leads1)
        save_leads(search2, leads2)
        
        # Verify they're separate
        retrieved1 = get_leads_by_search(search1)
        retrieved2 = get_leads_by_search(search2)
        
        self.assertEqual(len(retrieved1), 1)
        self.assertEqual(len(retrieved2), 1)
        self.assertNotEqual(retrieved1[0]["email"], retrieved2[0]["email"])


if __name__ == "__main__":
    unittest.main()

