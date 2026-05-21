"""Lead filtering helpers (email domains, etc.)."""

from app.filters.email_domain_rules import (
    EmailDomainRules,
    build_site_restriction_clause,
    apply_site_restriction_to_query,
    filter_leads_by_email_domains,
    parse_email_domain_allowlist,
    prepare_site_restriction_for_automation,
    site_restriction_targets_only_pdf_rare_hosts,
)

__all__ = [
    "EmailDomainRules",
    "build_site_restriction_clause",
    "apply_site_restriction_to_query",
    "filter_leads_by_email_domains",
    "parse_email_domain_allowlist",
    "prepare_site_restriction_for_automation",
    "site_restriction_targets_only_pdf_rare_hosts",
]
