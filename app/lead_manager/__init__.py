"""Lead Manager Module - Handles external lead uploads, validation, and filtering."""

from .uploader import upload_leads_from_file
from .validator import validate_email, validate_lead, ValidationResult
from .domain_filter import extract_domain, get_domain_stats
from .lead_manager import (
    save_external_leads,
    get_external_leads,
    get_external_leads_by_domain,
    compare_with_extracted_leads,
    get_domain_statistics,
    delete_external_leads,
)

__all__ = [
    "upload_leads_from_file",
    "validate_email",
    "validate_lead",
    "ValidationResult",
    "extract_domain",
    "get_domain_stats",
    "save_external_leads",
    "get_external_leads",
    "get_external_leads_by_domain",
    "compare_with_extracted_leads",
    "get_domain_statistics",
    "delete_external_leads",
]
