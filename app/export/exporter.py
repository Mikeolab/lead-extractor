"""
Export Module
Exports leads to CSV and Excel formats.
"""
from __future__ import annotations
import re
import pandas as pd
from pathlib import Path
from datetime import datetime
from email_validator import EmailNotValidError, validate_email
from app.config import EXPORT_DIR


def ensure_export_dir() -> Path:
    """Ensure the export directory exists."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    return EXPORT_DIR


# Preset column groups for filtering
COLUMN_PRESETS = {
    "Emails only": ["email"],
    "Emails + Names": ["email", "contact_name"],
    "Emails + Phones": ["email", "phone"],
    "Emails + Names + Phones": ["email", "contact_name", "phone"],
    "All fields": ["business_name", "contact_name", "email", "phone", "website", "source_url", "snippet"],
}

COLUMN_LABELS = {
    "business_name": "Business Name",
    "contact_name": "Contact Name",
    "email": "Email",
    "phone": "Phone",
    "website": "Website",
    "source_url": "Source URL",
    "snippet": "Description",
}


def leads_to_dataframe(leads: list[dict], columns: list[str] | None = None) -> pd.DataFrame:
    """Convert leads list to a clean DataFrame. If columns given, only include those."""
    if not leads:
        return pd.DataFrame()

    df = pd.DataFrame(leads)

    # Select and rename columns for export
    column_map = {
        "business_name": "Business Name",
        "contact_name": "Contact Name",
        "email": "Email",
        "phone": "Phone",
        "website": "Website",
        "source_url": "Source URL",
        "snippet": "Description",
    }

    if columns:
        avail = [c for c in columns if c in df.columns]
        df = df[avail]
    else:
        avail = [k for k in column_map if k in df.columns]
        df = df[avail]

    df = df.rename(columns={k: column_map.get(k, k) for k in df.columns if k in column_map})
    return df


def _coerce_email_string(s: str) -> str | None:
    """Strip mailto:, angle brackets, trailing punctuation — one candidate string."""
    t = (s or "").strip().replace("\n", " ").replace("\r", "")
    if not t or "@" not in t:
        return None
    if t.lower().startswith("mailto:"):
        t = t[7:].split("?")[0].strip()
    m = re.search(r"<([a-zA-Z0-9._%+\-]+@[^>\s]+)>", t)
    if m:
        t = m.group(1).strip()
    t = t.rstrip(".,;)>]\"'").strip()
    return t if "@" in t else None


def normalize_email_cell_to_addresses(raw: str | None) -> list[str]:
    """
    Parse one database `email` cell into 0..N addresses (lowercased, trailing dot stripped).
    Handles comma/space-separated lists and messy PDF extractions the same way as extraction.
    """
    if raw is None or not str(raw).strip():
        return []
    s = str(raw).strip()
    from app.extractors.email_extractor import extract_emails

    found = extract_emails(s, "")
    if found:
        return found
    coerced = _coerce_email_string(s)
    if not coerced:
        return []
    found2 = extract_emails(coerced, "")
    if found2:
        return found2
    c = coerced.lower().strip().rstrip(".")
    return [c] if "@" in c and "." in c.split("@", 1)[-1] else []


def expand_merged_leads_per_email_field(merged: list[dict]) -> list[dict]:
    """
    When a single lead row's email field contains multiple addresses, split into one row per
    address (same contact fields) so Unique / Unique valid behave intuitively.
    """
    expanded: list[dict] = []
    for l in merged:
        addrs = normalize_email_cell_to_addresses(l.get("email"))
        if not addrs:
            row = dict(l)
            row["email"] = (l.get("email") or "").strip() if isinstance(l.get("email"), str) else ""
            expanded.append(row)
            continue
        if len(addrs) == 1:
            row = dict(l)
            row["email"] = addrs[0]
            expanded.append(row)
            continue
        for addr in addrs:
            row = dict(l)
            row["email"] = addr
            expanded.append(row)
    return expanded


def filter_merged_leads_for_export(
    merged: list[dict],
    *,
    use_full: bool,
    use_validation: bool,
) -> tuple[list[dict], dict[str, int]]:
    """
    Same pipeline for Saved Leads and Live "saved sessions" merge:
    - Full: return rows as-is (no split, no dedupe).
    - Unique: split multi-address cells, dedupe by normalized email.
    - Unique valid: same as Unique plus email_validator (check_deliverability=False).
    """
    stats: dict[str, int] = {
        "merged_raw": len(merged),
        "rows_after_split": len(merged),
        "no_email_count": 0,
        "invalid_count": 0,
        "dup_count": 0,
    }
    if use_full:
        return list(merged), stats

    work = expand_merged_leads_per_email_field(merged)
    stats["rows_after_split"] = len(work)

    seen: set[str] = set()
    unique: list[dict] = []
    for l in work:
        e = (l.get("email") or "").strip()
        if not e or "@" not in e:
            stats["no_email_count"] += 1
            continue
        norm = e.lower().rstrip(".")
        if use_validation:
            try:
                validated = validate_email(norm, check_deliverability=False)
                norm = validated.email
            except EmailNotValidError:
                stats["invalid_count"] += 1
                continue
        if norm not in seen:
            seen.add(norm)
            l_copy = dict(l)
            l_copy["email"] = norm
            unique.append(l_copy)
        else:
            stats["dup_count"] += 1
    return unique, stats


def export_to_csv(leads: list[dict], filename: str = "", columns: list[str] | None = None) -> Path:
    """
    Export leads to CSV file.

    Args:
        leads: List of lead dictionaries
        filename: Optional custom filename
        columns: Optional list of columns to export (e.g. ['email'] for emails only)

    Returns:
        Path to the exported file
    """
    export_dir = ensure_export_dir()
    df = leads_to_dataframe(leads, columns=columns)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"leads_{timestamp}.csv"

    filepath = export_dir / filename
    df.to_csv(filepath, index=False, encoding="utf-8")
    return filepath


def export_to_excel(leads: list[dict], filename: str = "", columns: list[str] | None = None) -> Path:
    """
    Export leads to Excel file.

    Args:
        leads: List of lead dictionaries
        filename: Optional custom filename
        columns: Optional list of columns to export (e.g. ['email'] for emails only)

    Returns:
        Path to the exported file
    """
    export_dir = ensure_export_dir()
    df = leads_to_dataframe(leads, columns=columns)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"leads_{timestamp}.xlsx"

    filepath = export_dir / filename

    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Leads", index=False)

        # Auto-adjust column widths
        worksheet = writer.sheets["Leads"]
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).map(len).max() if len(df) > 0 else 0,
                len(col),
            )
            # Cap at 50 characters width
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)

    return filepath

