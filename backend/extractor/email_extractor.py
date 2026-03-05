"""
Email Extractor - Extracts and validates email addresses from web content.
"""
import re
import logging
from typing import List, Set
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Email regex pattern - comprehensive but avoids false positives
EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE,
)

# Common false positive domains to filter out
BLACKLISTED_DOMAINS = {
    "example.com", "example.org", "example.net",
    "domain.com", "email.com", "your-domain.com",
    "yourcompany.com", "yourdomain.com", "company.com",
    "test.com", "test.org", "localhost.com",
    "sentry.io", "wixpress.com", "w3.org",
    "schema.org", "wordpress.org", "googleusercontent.com",
    "googleapis.com", "gstatic.com",
}

# Common false positive patterns
BLACKLISTED_PATTERNS = [
    r".*\.png$", r".*\.jpg$", r".*\.gif$", r".*\.svg$",
    r".*\.css$", r".*\.js$", r".*\.woff$",
    r".*@\d+x\.\w+$",  # image@2x.png patterns
]

BLACKLISTED_RE = [re.compile(p, re.IGNORECASE) for p in BLACKLISTED_PATTERNS]


def is_valid_email(email: str) -> bool:
    """
    Validate if an email address looks legitimate.
    
    Filters out:
    - Blacklisted domains (example.com, etc.)
    - Image/file references that look like emails
    - Very long emails (likely false positives)
    - Emails with suspicious patterns
    """
    email = email.lower().strip()
    
    # Length check
    if len(email) > 100 or len(email) < 5:
        return False
    
    # Must have @ and domain
    if "@" not in email or "." not in email.split("@")[-1]:
        return False
    
    # Check blacklisted domains
    domain = email.split("@")[-1]
    if domain in BLACKLISTED_DOMAINS:
        return False
    
    # Check blacklisted patterns
    for pattern in BLACKLISTED_RE:
        if pattern.match(email):
            return False
    
    # Reject if local part has too many dots (likely a filename)
    local_part = email.split("@")[0]
    if local_part.count(".") > 3:
        return False
    
    # Reject very common non-email patterns
    if any(x in email for x in ["noreply", "no-reply", "unsubscribe", "mailer-daemon"]):
        return False
    
    return True


def extract_emails_from_text(text: str) -> Set[str]:
    """Extract email addresses from raw text."""
    emails = set()
    
    found = EMAIL_PATTERN.findall(text)
    for email in found:
        email = email.lower().strip().rstrip(".")
        if is_valid_email(email):
            emails.add(email)
    
    return emails


def extract_emails_from_html(soup: BeautifulSoup) -> Set[str]:
    """
    Extract emails from HTML, including:
    - mailto: links
    - Text content
    - Meta tags
    - Structured data
    """
    emails = set()
    
    # 1. Extract from mailto: links (most reliable)
    for link in soup.find_all("a", href=True):
        href = link.get("href", "")
        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").split("?")[0].strip().lower()
            if is_valid_email(email):
                emails.add(email)
    
    # 2. Extract from visible text
    text = soup.get_text(separator=" ", strip=True)
    text_emails = extract_emails_from_text(text)
    emails.update(text_emails)
    
    # 3. Extract from meta tags
    for meta in soup.find_all("meta"):
        content = meta.get("content", "")
        if content:
            meta_emails = extract_emails_from_text(content)
            emails.update(meta_emails)
    
    # 4. Extract from JSON-LD structured data
    for script in soup.find_all("script", type="application/ld+json"):
        if script.string:
            ld_emails = extract_emails_from_text(script.string)
            emails.update(ld_emails)
    
    return emails


def extract_emails(text: str, soup: BeautifulSoup) -> List[str]:
    """
    Main email extraction function. Combines all methods.
    
    Returns deduplicated, sorted list of valid emails.
    """
    all_emails = set()
    
    # From HTML structure
    html_emails = extract_emails_from_html(soup)
    all_emails.update(html_emails)
    
    # From raw text (catches any missed)
    text_emails = extract_emails_from_text(text)
    all_emails.update(text_emails)
    
    result = sorted(all_emails)
    logger.debug(f"Extracted {len(result)} emails")
    return result

