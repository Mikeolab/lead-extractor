"""Domain filtering and statistics module."""

from typing import List, Dict, Set, Optional
from collections import Counter
import re


def extract_domain(email: str) -> Optional[str]:
    """
    Extract domain from an email address.
    
    Args:
        email: Email address
        
    Returns:
        Domain string (e.g., 'gmail.com') or None if invalid
    """
    if not email or not isinstance(email, str):
        return None
    
    email = email.strip().lower()
    
    # Extract domain part after @
    if '@' in email:
        domain = email.split('@')[-1]
        # Remove trailing/leading whitespace and common issues
        domain = domain.strip()
        
        # Validate basic domain format
        if domain and '.' in domain and len(domain) > 2:
            return domain
    
    return None


def get_domain_from_leads(leads: List[dict]) -> List[str]:
    """
    Extract all domains from a list of leads.
    
    Args:
        leads: List of lead dictionaries with 'email' field
        
    Returns:
        List of domain strings
    """
    domains = []
    for lead in leads:
        email = lead.get("email", "")
        domain = extract_domain(email)
        if domain:
            domains.append(domain)
    
    return domains


def get_domain_stats(leads: List[dict]) -> Dict[str, int]:
    """
    Get statistics about domains in leads.
    
    Args:
        leads: List of lead dictionaries
        
    Returns:
        Dictionary with domain as key and count as value, sorted by count (desc)
    """
    domains = get_domain_from_leads(leads)
    if not domains:
        return {}
    
    counter = Counter(domains)
    # Return sorted by count (descending)
    return dict(sorted(counter.items(), key=lambda x: x[1], reverse=True))


def filter_leads_by_domain(leads: List[dict], domain_filter: str) -> List[dict]:
    """
    Filter leads by domain (supports wildcards and multiple domains).
    
    Args:
        leads: List of lead dictionaries
        domain_filter: Domain filter string (e.g., 'gmail.com' or '*@gmail.com' or 'gmail.com,yahoo.com')
        
    Returns:
        Filtered list of leads
    """
    if not domain_filter or not leads:
        return leads
    
    domain_filter = domain_filter.strip().lower()
    
    # Parse multiple domains separated by comma
    filter_domains = [d.strip() for d in domain_filter.split(',')]
    
    filtered = []
    for lead in leads:
        email = lead.get("email", "").strip().lower()
        domain = extract_domain(email)
        
        if domain:
            for filter_domain in filter_domains:
                # Remove @ if present
                filter_domain = filter_domain.lstrip('@')
                
                # Support wildcards
                if '*' in filter_domain:
                    pattern = filter_domain.replace('.', r'\.').replace('*', '.*')
                    if re.match(f"^{pattern}$", domain):
                        filtered.append(lead)
                        break
                elif domain == filter_domain:
                    filtered.append(lead)
                    break
    
    return filtered


def filter_leads_by_domain_list(leads: List[dict], domains: List[str]) -> List[dict]:
    """
    Filter leads by a list of domains.
    
    Args:
        leads: List of lead dictionaries
        domains: List of domain strings to include
        
    Returns:
        Filtered list of leads
    """
    if not domains or not leads:
        return leads
    
    domains_set = {d.lower() for d in domains}
    filtered = []
    
    for lead in leads:
        email = lead.get("email", "").strip().lower()
        domain = extract_domain(email)
        
        if domain and domain in domains_set:
            filtered.append(lead)
    
    return filtered


def get_top_domains(leads: List[dict], top_n: int = 20) -> List[tuple]:
    """
    Get top N domains from leads.
    
    Args:
        leads: List of lead dictionaries
        top_n: Number of top domains to return
        
    Returns:
        List of (domain, count) tuples sorted by count (descending)
    """
    stats = get_domain_stats(leads)
    return list(stats.items())[:top_n]


def exclude_domains(leads: List[dict], exclude_domains: List[str]) -> List[dict]:
    """
    Exclude leads from specific domains.
    
    Args:
        leads: List of lead dictionaries
        exclude_domains: List of domains to exclude
        
    Returns:
        Filtered list with excluded domains removed
    """
    if not exclude_domains or not leads:
        return leads
    
    exclude_set = {d.lower() for d in exclude_domains}
    filtered = []
    
    for lead in leads:
        email = lead.get("email", "").strip().lower()
        domain = extract_domain(email)
        
        if domain and domain not in exclude_set:
            filtered.append(lead)
    
    return filtered


def group_leads_by_domain(leads: List[dict]) -> Dict[str, List[dict]]:
    """
    Group leads by their domain.
    
    Args:
        leads: List of lead dictionaries
        
    Returns:
        Dictionary with domain as key and list of leads as value
    """
    groups = {}
    
    for lead in leads:
        email = lead.get("email", "").strip().lower()
        domain = extract_domain(email)
        
        if domain:
            if domain not in groups:
                groups[domain] = []
            groups[domain].append(lead)
    
    return groups
