"""
Integration tests - Test with example query
"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.extractors.email_extractor import extract_emails
from app.extractors.phone_extractor import extract_phones
from app.extractors.name_extractor import extract_contact_names


class TestIntegration(unittest.TestCase):
    """Integration tests with example query"""
    
    def test_example_query_extraction(self):
        """Test extraction with example query text"""
        # Example query: "mike@yahoo.com + sbcglobal.net + Vendor invoice + bellsouth.net + pdf"
        # Simulate PDF text that might be found
        sample_pdf_text = """
        VENDOR INVOICE
        Invoice Number: INV-2024-001
        
        Vendor Information:
        Company: ABC Services Inc.
        Contact: Mike Johnson
        Email: mike@yahoo.com
        Phone: (555) 123-4567
        Address: 123 Main Street, Houston, TX 77001
        
        Billing Information:
        Client: XYZ Corporation
        Contact: Jane Smith
        Email: jane.smith@bellsouth.net
        Phone: 555-987-6543
        
        Service Details:
        Description: Plumbing services
        Amount: $1,500.00
        Date: February 13, 2024
        """
        
        # Extract leads
        emails = extract_emails(sample_pdf_text)
        phones = extract_phones(sample_pdf_text)
        names = extract_contact_names(sample_pdf_text)
        
        # Verify we found expected data
        self.assertIn("mike@yahoo.com", emails)
        self.assertIn("jane.smith@bellsouth.net", emails)
        self.assertTrue(len(phones) >= 2)
        self.assertTrue(len(names) >= 2)
        
        # Verify lead creation
        leads = []
        for email in emails:
            leads.append({
                "email": email,
                "phone": phones[0] if phones else "",
                "contact_name": names[0] if names else "",
            })
        
        self.assertEqual(len(leads), 2)
        self.assertTrue(all(lead["email"] for lead in leads))
    
    def test_pdf_text_variations(self):
        """Test extraction with different PDF text formats"""
        formats = [
            # Format 1: Structured
            """
            Contact Information
            Name: John Doe
            Email: john@company.com
            Phone: 555-1234
            """,
            # Format 2: Inline
            "Reach us at john@company.com or call 555-1234. Contact John Doe.",
            # Format 3: List
            """
            - Email: jane@test.com
            - Phone: (555) 987-6543
            - Contact: Jane Smith
            """,
        ]
        
        for pdf_text in formats:
            emails = extract_emails(pdf_text)
            phones = extract_phones(pdf_text)
            names = extract_contact_names(pdf_text)
            
            # Should find at least email or phone or name
            self.assertTrue(len(emails) > 0 or len(phones) > 0 or len(names) > 0)


if __name__ == "__main__":
    unittest.main()

