"""
Unit tests for extractors (email, phone, name)
"""
import unittest
from app.extractors.email_extractor import extract_emails
from app.extractors.phone_extractor import extract_phones
from app.extractors.name_extractor import extract_contact_names, extract_names_from_email


class TestEmailExtractor(unittest.TestCase):
    def test_extract_simple_email(self):
        text = "Contact us at john@company.com"
        emails = extract_emails(text)
        self.assertIn("john@company.com", emails)

    def test_extract_multiple_emails(self):
        text = "Email: john@company.com or jane@business.net"
        emails = extract_emails(text)
        self.assertIn("john@company.com", emails)
        self.assertIn("jane@business.net", emails)

    def test_filter_junk_emails(self):
        text = "noreply@example.com admin@wordpress.com"
        emails = extract_emails(text)
        self.assertEqual(len(emails), 0)  # Should filter junk

    def test_extract_from_pdf_text(self):
        pdf_text = """
        Invoice
        Contact: mike@yahoo.com
        Phone: 555-1234
        """
        emails = extract_emails(pdf_text)
        self.assertIn("mike@yahoo.com", emails)


class TestPhoneExtractor(unittest.TestCase):
    def test_extract_us_phone(self):
        text = "Call us at (555) 123-4567"
        phones = extract_phones(text)
        self.assertTrue(len(phones) > 0)
        self.assertIn("555", phones[0])

    def test_extract_formatted_phone(self):
        text = "Phone: 555-123-4567 or 555.123.4567"
        phones = extract_phones(text)
        self.assertTrue(len(phones) > 0)

    def test_filter_dates(self):
        text = "Date: 2024-01-15 Phone: 555-1234"
        phones = extract_phones(text)
        # Should not extract date as phone
        for phone in phones:
            self.assertNotIn("2024", phone)


class TestNameExtractor(unittest.TestCase):
    def test_extract_contact_name(self):
        text = "Contact Person: John Smith"
        names = extract_contact_names(text)
        self.assertTrue(len(names) > 0)
        self.assertIn("John Smith", names)

    def test_extract_from_email(self):
        email = "john.smith@example.com"
        name = extract_names_from_email(email)
        self.assertEqual(name, "John Smith")

    def test_extract_multiple_names(self):
        text = "Owner: Jane Doe Manager: Bob Johnson"
        names = extract_contact_names(text)
        self.assertTrue(len(names) >= 1)


if __name__ == "__main__":
    unittest.main()

