"""
End-to-end tests for lead extraction automation
Tests the full flow: search -> find PDFs -> extract leads -> save
"""
import unittest
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.db import save_search, save_leads, get_leads_by_search, get_recent_searches
from app.extractors.email_extractor import extract_emails
from app.extractors.phone_extractor import extract_phones
from app.extractors.name_extractor import extract_contact_names


class TestE2E(unittest.TestCase):
    """End-to-end tests"""
    
    def test_database_save_and_retrieve(self):
        """Test saving and retrieving leads from database"""
        # Create test search
        search_id = save_search("test query filetype:pdf", num_results=0)
        self.assertIsNotNone(search_id)
        
        # Create test leads
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
        
        # Save leads
        saved_count = save_leads(search_id, test_leads)
        self.assertEqual(saved_count, 1)
        
        # Retrieve leads
        retrieved = get_leads_by_search(search_id)
        self.assertEqual(len(retrieved), 1)
        self.assertEqual(retrieved[0]["email"], "test@example.com")
    
    def test_extraction_pipeline(self):
        """Test the complete extraction pipeline"""
        # Sample PDF text (simulating extracted text)
        pdf_text = """
        INVOICE #12345
        Vendor: ABC Company
        Contact: John Smith
        Email: john.smith@abc.com
        Phone: (555) 123-4567
        Date: 2024-01-15
        """
        
        # Extract leads
        emails = extract_emails(pdf_text)
        phones = extract_phones(pdf_text)
        names = extract_contact_names(pdf_text)
        
        # Verify extraction
        self.assertTrue(len(emails) > 0)
        self.assertTrue(len(phones) > 0)
        self.assertTrue(len(names) > 0)
        
        # Create lead structure
        leads = []
        if emails:
            for i, email in enumerate(emails):
                leads.append({
                    "email": email,
                    "phone": phones[i] if i < len(phones) else (phones[0] if phones else ""),
                    "contact_name": names[i] if i < len(names) else (names[0] if names else ""),
                    "business_name": "",
                    "website": "",
                    "source_url": "https://test.com/invoice.pdf",
                    "snippet": "",
                })
        
        # Verify lead structure
        self.assertTrue(len(leads) > 0)
        self.assertTrue(leads[0]["email"])
        self.assertTrue(leads[0]["phone"] or leads[0]["contact_name"])
    
    def test_session_tracking(self):
        """Test session-based tracking"""
        # Create multiple searches (sessions)
        search1 = save_search("query 1 filetype:pdf")
        search2 = save_search("query 2 filetype:pdf")
        
        # Save leads to each
        save_leads(search1, [{"email": "test1@example.com", "phone": "", "contact_name": "", "business_name": "", "website": "", "source_url": "", "snippet": ""}])
        save_leads(search2, [{"email": "test2@example.com", "phone": "", "contact_name": "", "business_name": "", "website": "", "source_url": "", "snippet": ""}])
        
        # Verify sessions are separate
        leads1 = get_leads_by_search(search1)
        leads2 = get_leads_by_search(search2)
        
        self.assertEqual(len(leads1), 1)
        self.assertEqual(len(leads2), 1)
        self.assertNotEqual(leads1[0]["email"], leads2[0]["email"])


if __name__ == "__main__":
    unittest.main()

