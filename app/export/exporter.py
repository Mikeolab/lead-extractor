"""
Export Module
Exports leads to CSV and Excel formats.
"""
from __future__ import annotations
import pandas as pd
from pathlib import Path
from datetime import datetime
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

