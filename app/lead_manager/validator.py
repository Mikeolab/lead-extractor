"""Email and lead validation module."""

from dataclasses import dataclass
from typing import Optional
import re
from email_validator import validate_email as email_validate, EmailNotValidError


@dataclass
class ValidationResult:
    """Result of lead validation."""
    is_valid: bool
    email: Optional[str] = None
    error_message: Optional[str] = None
    domain: Optional[str] = None


def validate_email(email: str) -> ValidationResult:
    """
    Validate an email address.
    
    Args:
        email: Email address to validate
        
    Returns:
        ValidationResult with validation status
    """
    if not email or not isinstance(email, str):
        return ValidationResult(
            is_valid=False,
            error_message="Email is empty or not a string"
        )
    
    email = email.strip().lower()
    
    try:
        # Use email_validator for comprehensive validation
        valid = email_validate(email, check_deliverability=False)
        domain = valid.domain
        return ValidationResult(
            is_valid=True,
            email=valid.email,
            domain=domain
        )
    except EmailNotValidError as e:
        return ValidationResult(
            is_valid=False,
            email=email,
            error_message=str(e)
        )


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
