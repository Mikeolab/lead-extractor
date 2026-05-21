"""File uploader module for external leads."""

from typing import List, Dict, Optional, Tuple
import csv
import json
import io
from pathlib import Path


def parse_text_file(content: str) -> List[str]:
    """Parse plain text file — one email per line."""
    lines = content.splitlines()
    return [line.strip() for line in lines if line.strip() and '@' in line.strip()]


def parse_csv_file(content: str) -> List[Dict[str, str]]:
    """Parse CSV file using DictReader so headers become keys."""
    try:
        reader = csv.DictReader(io.StringIO(content))
        leads = list(reader)
        if not leads:
            # Fallback: no headers row — single-column emails
            reader2 = csv.reader(io.StringIO(content))
            rows = [r for r in reader2 if r]
            leads = [{"email": row[0].strip()} for row in rows if row and '@' in row[0]]
        return leads
    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {e}")


def parse_json_file(content: str) -> List[Dict]:
    """Parse JSON — array of objects or object with leads/items/data key."""
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ['leads', 'items', 'records', 'data']:
                if key in data and isinstance(data[key], list):
                    return data[key]
            return [data]
        raise ValueError("JSON must be an array or object with a 'leads' key")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")


def parse_xlsx_file(file_bytes: bytes) -> List[Dict[str, str]]:
    """Parse first sheet of an Excel file."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes))
        sheet = wb.active
        headers = [str(c.value).strip() if c.value is not None else f"col_{i}" for i, c in enumerate(sheet[1])]
        leads = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            lead = {headers[i]: (str(v).strip() if v is not None else "") for i, v in enumerate(row)}
            lead = {k: v for k, v in lead.items() if v}
            if lead:
                leads.append(lead)
        return leads
    except ImportError:
        raise ValueError("openpyxl not installed — cannot parse Excel files.")
    except Exception as e:
        raise ValueError(f"Failed to parse Excel file: {e}")


def normalize_lead(lead_data: Dict) -> Dict[str, str]:
    """
    Map arbitrary CSV/JSON column names to standard fields.
    All matching is case-insensitive so 'Email', 'EMAIL', 'email' all work.
    """
    lc: Dict[str, str] = {}
    for k, v in lead_data.items():
        if k is not None and v is not None:
            lc[str(k).lower().strip()] = str(v).strip()

    normalized: Dict[str, str] = {}

    for key in ['email', 'e-mail', 'mail', 'email_address', 'contact_email', 'email address']:
        if key in lc and lc[key]:
            normalized['email'] = lc[key]
            break

    for key in ['business_name', 'business name', 'company', 'company_name', 'organization', 'business']:
        if key in lc and lc[key]:
            normalized['business_name'] = lc[key]
            break

    for key in ['contact_name', 'contact name', 'name', 'full name', 'contact', 'person_name', 'first_name']:
        if key in lc and lc[key]:
            normalized['contact_name'] = lc[key]
            break

    for key in ['phone', 'phone_number', 'phone number', 'telephone', 'tel', 'contact_phone']:
        if key in lc and lc[key]:
            normalized['phone'] = lc[key]
            break

    for key in ['website', 'url', 'web', 'website_url', 'site', 'source_url', 'source url']:
        if key in lc and lc[key]:
            normalized['website'] = lc[key]
            break

    # Single-column fallback
    if 'email' not in normalized and len(lc) == 1:
        v = list(lc.values())[0]
        if '@' in v:
            normalized['email'] = v

    return normalized


def upload_leads_from_file(
    file_content: bytes,
    file_name: str,
    file_type: Optional[str] = None,
) -> Tuple[List[Dict], List[str]]:
    """
    Parse leads from an uploaded file.
    Returns (leads_list, messages_list). Messages include parse stats and warnings.
    Import is intentionally permissive — email-format validation happens separately
    via the "Validate All" button, not at import time.
    """
    messages: List[str] = []
    leads: List[Dict] = []

    ext = Path(file_name).suffix.lower()
    # Determine format: prefer explicit file_type, fall back to extension
    if file_type:
        ft = file_type.lower()
    else:
        ft = {
            '.txt': 'text',
            '.csv': 'csv',
            '.tsv': 'tsv',
            '.xlsx': 'xlsx',
            '.xls': 'xlsx',
            '.json': 'json',
        }.get(ext, 'text')

    try:
        def decode(b: bytes) -> str:
            try:
                return b.decode('utf-8')
            except UnicodeDecodeError:
                return b.decode('latin-1')

        if ft in ('xlsx', 'xls') or ext in ('.xlsx', '.xls'):
            raw = parse_xlsx_file(file_content)
            leads = [normalize_lead(r) for r in raw]

        elif ft == 'csv' or ext == '.csv':
            raw = parse_csv_file(decode(file_content))
            leads = [normalize_lead(r) for r in raw]

        elif ft == 'tsv' or ext == '.tsv':
            # TSV — treat as CSV with tab delimiter
            content = decode(file_content)
            reader = csv.DictReader(io.StringIO(content), delimiter='\t')
            raw = list(reader)
            leads = [normalize_lead(r) for r in raw]

        elif ft == 'json' or ext == '.json':
            raw = parse_json_file(decode(file_content))
            leads = [
                normalize_lead(r) if isinstance(r, dict) else {"email": str(r)}
                for r in raw
            ]

        else:
            # Plain text — one email per line
            emails = parse_text_file(decode(file_content))
            leads = [{"email": e} for e in emails]

        # Drop rows with no email field at all
        leads = [l for l in leads if l.get("email")]

        if not leads:
            messages.append("No valid leads found in file (no email column/values detected)")
        else:
            messages.append(f"Parsed {len(leads)} leads from file")

    except Exception as e:
        messages.append(f"Error parsing file: {e}")

    return leads, messages
