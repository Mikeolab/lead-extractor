"""File uploader module for external leads."""

from typing import List, Dict, Optional, Tuple
import csv
import json
import io
from pathlib import Path


def parse_text_file(content: str, delimiter: str = '\n') -> List[str]:
    """
    Parse plain text file (one email per line).
    
    Args:
        content: File content as string
        delimiter: Line delimiter (default newline)
        
    Returns:
        List of email strings
    """
    lines = content.split(delimiter)
    emails = [line.strip() for line in lines if line.strip()]
    return emails


def parse_csv_file(content: str) -> List[Dict[str, str]]:
    """
    Parse CSV file. Auto-detect headers and parse into list of dictionaries.
    
    Args:
        content: CSV content as string
        
    Returns:
        List of dictionaries with lead data
    """
    try:
        # Try to parse with CSV reader
        reader = csv.DictReader(io.StringIO(content))
        leads = list(reader)
        
        if not leads:
            # If DictReader fails, try to parse as list of lists
            reader = csv.reader(io.StringIO(content))
            rows = list(reader)
            if rows:
                # Use first row as headers if available
                if len(rows) > 1:
                    headers = rows[0]
                    leads = [dict(zip(headers, row)) for row in rows[1:]]
                else:
                    # Single column, assume emails
                    leads = [{"email": row[0]} if row else {} for row in rows]
        
        return leads
    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {str(e)}")


def parse_json_file(content: str) -> List[Dict]:
    """
    Parse JSON file (should be array of objects or single object with items array).
    
    Args:
        content: JSON content as string
        
    Returns:
        List of lead dictionaries
    """
    try:
        data = json.loads(content)
        
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Try common keys for array of leads
            for key in ['leads', 'items', 'records', 'data']:
                if key in data and isinstance(data[key], list):
                    return data[key]
            # If it's a single lead object
            return [data]
        else:
            raise ValueError("JSON must be an array or object with 'leads' key")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {str(e)}")


def parse_xlsx_file(file_bytes: bytes) -> List[Dict[str, str]]:
    """
    Parse Excel file. Returns first sheet.
    
    Args:
        file_bytes: File content as bytes
        
    Returns:
        List of dictionaries with lead data
    """
    try:
        import openpyxl
        
        workbook = openpyxl.load_workbook(io.BytesIO(file_bytes))
        sheet = workbook.active
        
        # Get headers from first row
        headers = []
        for cell in sheet[1]:
            headers.append(cell.value)
        
        leads = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            lead = dict(zip(headers, row))
            # Filter out None values
            lead = {k: v for k, v in lead.items() if v is not None}
            if lead:  # Only add non-empty rows
                leads.append(lead)
        
        return leads
    except ImportError:
        raise ValueError("openpyxl not installed. Cannot parse Excel files.")
    except Exception as e:
        raise ValueError(f"Failed to parse Excel file: {str(e)}")


def normalize_lead(lead_data: Dict) -> Dict[str, str]:
    """
    Normalize lead data to standard format.
    
    Standard fields: email, business_name, contact_name, phone, website
    
    Args:
        lead_data: Lead dictionary (possibly with non-standard keys)
        
    Returns:
        Normalized lead dictionary
    """
    normalized = {}
    
    # Common email column names
    email_keys = ['email', 'e-mail', 'mail', 'email_address', 'contact_email']
    for key in email_keys:
        if key in lead_data:
            normalized['email'] = str(lead_data[key]).strip()
            break
    
    # Business name variations
    business_keys = ['business_name', 'company', 'company_name', 'organization', 'business']
    for key in business_keys:
        if key in lead_data and key not in normalized:
            normalized['business_name'] = str(lead_data[key]).strip()
            break
    
    # Contact name variations
    contact_keys = ['contact_name', 'name', 'contact', 'person_name', 'first_name']
    for key in contact_keys:
        if key in lead_data and key not in normalized:
            normalized['contact_name'] = str(lead_data[key]).strip()
            break
    
    # Phone variations
    phone_keys = ['phone', 'phone_number', 'telephone', 'tel', 'contact_phone']
    for key in phone_keys:
        if key in lead_data and key not in normalized:
            normalized['phone'] = str(lead_data[key]).strip()
            break
    
    # Website variations
    website_keys = ['website', 'url', 'web', 'domain', 'website_url']
    for key in website_keys:
        if key in lead_data and key not in normalized:
            normalized['website'] = str(lead_data[key]).strip()
            break
    
    # If only email is provided (from text file)
    if 'email' not in normalized and len(lead_data) == 1:
        first_value = list(lead_data.values())[0]
        if isinstance(first_value, str):
            normalized['email'] = first_value.strip()
    
    return normalized


def upload_leads_from_file(
    file_content: bytes,
    file_name: str,
    file_type: Optional[str] = None
) -> Tuple[List[Dict], List[str]]:
    """
    Upload and parse leads from file.
    
    Supports: .txt, .csv, .xlsx, .json
    
    Args:
        file_content: File content as bytes
        file_name: Original filename
        file_type: File type override (e.g., 'text/csv'). Auto-detected from filename if None.
        
    Returns:
        Tuple of (parsed leads list, error/warning messages list)
    """
    errors = []
    leads = []
    
    # Determine file type
    if file_type:
        # Use provided type
        content_type = file_type.lower()
    else:
        # Auto-detect from extension
        ext = Path(file_name).suffix.lower()
        ext_map = {
            '.txt': 'text/plain',
            '.csv': 'text/csv',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.json': 'application/json',
        }
        content_type = ext_map.get(ext, 'text/plain')
    
    try:
        if 'text' in content_type or content_type == 'text/plain':
            # Parse as text (one email per line)
            try:
                text_content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                text_content = file_content.decode('latin-1')
            
            emails = parse_text_file(text_content)
            leads = [{"email": email} for email in emails]
            
        elif 'csv' in content_type:
            # Parse as CSV
            try:
                text_content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                text_content = file_content.decode('latin-1')
            
            csv_leads = parse_csv_file(text_content)
            leads = [normalize_lead(lead) for lead in csv_leads]
            
        elif 'spreadsheet' in content_type or 'excel' in content_type or file_name.endswith('.xlsx'):
            # Parse as Excel
            xlsx_leads = parse_xlsx_file(file_content)
            leads = [normalize_lead(lead) for lead in xlsx_leads]
            
        elif 'json' in content_type:
            # Parse as JSON
            try:
                text_content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                text_content = file_content.decode('latin-1')
            
            json_leads = parse_json_file(text_content)
            leads = [normalize_lead(lead) if isinstance(lead, dict) else {"email": str(lead)} for lead in json_leads]
        
        else:
            # Default to text parsing
            try:
                text_content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                text_content = file_content.decode('latin-1')
            
            emails = parse_text_file(text_content)
            leads = [{"email": email} for email in emails]
        
        # Clean up leads - remove empty ones
        leads = [lead for lead in leads if lead and lead.get("email")]
        
        if not leads:
            errors.append("No valid leads found in file")
        else:
            errors.append(f"Parsed {len(leads)} leads from file")
        
        return leads, errors
        
    except Exception as e:
        errors.append(f"Error parsing file: {str(e)}")
        return [], errors
