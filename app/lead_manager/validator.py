"""Email and lead validation module."""

from dataclasses import dataclass
from typing import Optional, Set
import re
from email_validator import validate_email as email_validate, EmailNotValidError

# DNS MX cache: domain → bool (has valid MX records)
_mx_cache: dict = {}


@dataclass
class ValidationResult:
    """Result of lead validation."""
    is_valid: bool
    email: Optional[str] = None
    error_message: Optional[str] = None
    domain: Optional[str] = None


def _check_mx(domain: str) -> tuple[bool, str]:
    """
    Check whether `domain` has MX records (DNS lookup).
    Results are cached per process so repeated same-domain lookups are instant.
    Returns (ok, error_msg).
    """
    if domain in _mx_cache:
        cached = _mx_cache[domain]
        return (True, "") if cached else (False, f"Domain {domain!r} has no mail servers (no MX records)")
    try:
        import dns.resolver
        dns.resolver.resolve(domain, "MX")
        _mx_cache[domain] = True
        return True, ""
    except Exception as exc:
        _mx_cache[domain] = False
        return False, f"Domain {domain!r} has no mail servers: {exc}"


def validate_email(email: str, check_deliverability: bool = True) -> ValidationResult:
    """
    Validate an email address.
    Step 1 — syntax/format check (instant).
    Step 2 — DNS MX lookup to confirm the domain actually receives mail (cached per domain).

    Pass check_deliverability=False to skip the MX step (format-only, fast).
    """
    if not email or not isinstance(email, str):
        return ValidationResult(is_valid=False, error_message="Email is empty or not a string")

    email = email.strip().lower()

    # Step 1: format
    try:
        valid = email_validate(email, check_deliverability=False)
        domain = valid.domain
        normalized = valid.email
    except EmailNotValidError as e:
        return ValidationResult(is_valid=False, email=email, error_message=str(e))

    if not check_deliverability:
        return ValidationResult(is_valid=True, email=normalized, domain=domain)

    # Step 2: DNS MX check (cached — fast for repeated domains)
    try:
        import dns.resolver  # noqa: F401 — just test import
    except ImportError:
        # dnspython not installed — fall back to format-only
        return ValidationResult(is_valid=True, email=normalized, domain=domain)

    mx_ok, mx_err = _check_mx(domain)
    if not mx_ok:
        return ValidationResult(is_valid=False, email=normalized, domain=domain, error_message=mx_err)

    return ValidationResult(is_valid=True, email=normalized, domain=domain)


def validate_lead(lead: dict) -> ValidationResult:
    """
    Validate a lead record.
    
    Args:
        lead: Dictionary with lead information (email required, rest optional)
        
    Returns:
        ValidationResult
    """
    if not isinstance(lead, dict):
        return ValidationResult(
            is_valid=False,
            error_message="Lead must be a dictionary"
        )
    
    email = lead.get("email", "").strip()
    if not email:
        return ValidationResult(
            is_valid=False,
            error_message="Lead email is required"
        )
    
    return validate_email(email)


def validate_domain(domain: str) -> bool:
    """
    Simple domain validation.
    
    Args:
        domain: Domain string to validate
        
    Returns:
        True if valid domain format
    """
    if not domain or not isinstance(domain, str):
        return False
    
    # Basic domain pattern: domain.extension
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
    return bool(re.match(pattern, domain))


def is_duplicate_email(email1: str, email2: str) -> bool:
    """
    Check if two emails are duplicates (exact match after normalization).
    
    Args:
        email1: First email
        email2: Second email
        
    Returns:
        True if emails are the same after normalization
    """
    if not email1 or not email2:
        return False
    return email1.strip().lower() == email2.strip().lower()


def is_similar_email(email1: str, email2: str, threshold: float = 0.85) -> bool:
    """
    Check if two emails are similar (fuzzy matching for detecting variations).
    
    Args:
        email1: First email
        email2: Second email
        threshold: Similarity threshold (0-1)
        
    Returns:
        True if emails are similar
    """
    if is_duplicate_email(email1, email2):
        return True
    
    # Simple similarity check - if domain and name parts are very similar
    try:
        e1_parts = email1.lower().split('@')
        e2_parts = email2.lower().split('@')
        
        if len(e1_parts) != 2 or len(e2_parts) != 2:
            return False
        
        # Check if domain is the same
        if e1_parts[1] == e2_parts[1]:
            # Check if local part is similar (e.g., john.doe vs johndoe)
            name1 = e1_parts[0].replace('.', '').replace('_', '').replace('-', '')
            name2 = e2_parts[0].replace('.', '').replace('_', '').replace('-', '')
            
            if name1 == name2:
                return True
        
        return False
    except Exception:
        return False
