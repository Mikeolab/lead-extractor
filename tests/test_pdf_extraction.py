"""
Unit tests for PDF extraction functionality
"""
import unittest
import io
from app.server.automation_server import AutomationManager
from app.extractors.email_extractor import extract_emails
from app.extractors.phone_extractor import extract_phones
from app.extractors.name_extractor import extract_contact_names


class TestPDFExtraction(unittest.TestCase):
    """Test PDF text extraction and lead extraction"""
    
    def test_extract_emails_from_text(self):
        """Test email extraction from PDF-like text"""
        pdf_text = """
        INVOICE
        Vendor: ABC Company
        Contact: mike@yahoo.com
        Phone: (555) 123-4567
        """
        emails = extract_emails(pdf_text)
        self.assertIn("mike@yahoo.com", emails)
    
    def test_extract_phones_from_text(self):
        """Test phone extraction from PDF-like text"""
        pdf_text = """
        Contact Information:
        Phone: 555-123-4567
        Mobile: (555) 987-6543
        """
        phones = extract_phones(pdf_text)
        self.assertTrue(len(phones) > 0)
    
    def test_extract_names_from_text(self):
        """Test name extraction from PDF-like text"""
        pdf_text = """
        Contact Person: John Smith
        Manager: Jane Doe
        """
        names = extract_contact_names(pdf_text)
        self.assertTrue(len(names) > 0)
    
    def test_complete_lead_extraction(self):
        """Test complete lead extraction from sample PDF text"""
        pdf_text = """
        VENDOR INVOICE
        Company: ABC Plumbing
        Contact: John Smith
        Email: john.smith@abcplumbing.com
        Phone: (555) 123-4567
        Address: 123 Main St, Houston, TX
        """
        emails = extract_emails(pdf_text)
        phones = extract_phones(pdf_text)
        names = extract_contact_names(pdf_text)
        
        self.assertTrue(len(emails) > 0)
        self.assertTrue(len(phones) > 0)
        self.assertTrue(len(names) > 0)
        
        # Should create lead with all three
        lead = {
            "email": emails[0] if emails else "",
            "phone": phones[0] if phones else "",
            "contact_name": names[0] if names else "",
        }
        self.assertTrue(lead["email"] or lead["phone"] or lead["contact_name"])


if __name__ == "__main__":
    unittest.main()

