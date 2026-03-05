"""
PDF Export Module
Creates professional PDF reports from extracted leads.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime
try:
    from fpdf import FPDF
except ImportError:
    # Fallback for fpdf2 package
    try:
        from fpdf2 import FPDF
    except ImportError:
        raise ImportError("Please install fpdf2: pip install fpdf2")
from app.config import EXPORT_DIR, APP_NAME


def _sanitize(text: str) -> str:
    """Replace non-latin-1 characters for PDF compatibility."""
    replacements = {
        "\u2014": "-",  # em dash
        "\u2013": "-",  # en dash
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
        "\u2026": "...",  # ellipsis
        "\u2022": "*",  # bullet
        "\u00a0": " ",  # non-breaking space
        "\u200b": "",   # zero-width space
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Fallback: replace any remaining non-latin-1 chars
    return text.encode("latin-1", errors="replace").decode("latin-1")


class LeadsPDF(FPDF):
    """Custom PDF class with header/footer."""

    def __init__(self, title: str = "Lead Extraction Report"):
        super().__init__(orientation="L", format="A4")  # Landscape for more columns
        self.report_title = _sanitize(title)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(30, 60, 150)
        self.cell(0, 10, APP_NAME, ln=False, align="L")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, datetime.now().strftime("%Y-%m-%d %H:%M"), ln=True, align="R")
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(50, 50, 50)
        self.cell(0, 8, self.report_title, ln=True, align="L")
        self.set_draw_color(30, 60, 150)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), self.w - 10, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def add_summary(self, total: int, with_email: int, with_phone: int, query: str):
        """Add a summary section at the top."""
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(240, 244, 255)
        self.set_text_color(30, 60, 150)
        self.cell(0, 8, _sanitize(f"  Search Query: {query}"), ln=True, fill=True)
        self.ln(2)

        self.set_font("Helvetica", "", 9)
        self.set_text_color(50, 50, 50)
        stats = [
            f"Total Leads: {total}",
            f"With Email: {with_email}",
            f"With Phone: {with_phone}",
            f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        ]
        self.cell(0, 6, "  |  ".join(stats), ln=True)
        self.ln(5)

    def add_leads_table(self, leads: list[dict]):
        """Add leads as a formatted table."""
        # Column widths (landscape A4 = ~277mm usable)
        col_widths = {
            "Business Name": 55,
            "Contact": 40,
            "Email": 60,
            "Phone": 38,
            "Website": 55,
            "Snippet": 0,  # Will be calculated
        }
        used = sum(col_widths.values())
        col_widths["Snippet"] = max(self.w - 20 - used, 25)

        columns = list(col_widths.keys())
        widths = [col_widths[c] for c in columns]

        # Header row
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(30, 60, 150)
        self.set_text_color(255, 255, 255)
        for col, w in zip(columns, widths):
            self.cell(w, 7, f" {col}", border=1, fill=True)
        self.ln()

        # Data rows
        self.set_font("Helvetica", "", 7)
        self.set_text_color(30, 30, 30)

        for i, lead in enumerate(leads):
            # Alternate row colors
            if i % 2 == 0:
                self.set_fill_color(250, 250, 255)
            else:
                self.set_fill_color(255, 255, 255)

            row_data = [
                _sanitize(lead.get("business_name", "")[:35]),
                _sanitize(lead.get("contact_name", "")[:25]),
                _sanitize(lead.get("email", "")[:40]),
                _sanitize(lead.get("phone", "")[:22]),
                _sanitize(lead.get("website", "")[:35]),
                _sanitize(lead.get("snippet", "")[:40]),
            ]

            max_h = 6
            for val, w in zip(row_data, widths):
                self.cell(w, max_h, f" {val}", border=1, fill=True)
            self.ln()


def export_to_pdf(leads: list[dict], query: str = "", filename: str = "") -> Path:
    """
    Export leads to a professional PDF report.

    Args:
        leads: List of lead dictionaries
        query: The search query used
        filename: Optional custom filename

    Returns:
        Path to the exported file
    """
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"leads_{timestamp}.pdf"

    filepath = EXPORT_DIR / filename

    # Create PDF
    pdf = LeadsPDF(title=f"Lead Extraction Report - {query}" if query else "Lead Extraction Report")
    pdf.alias_nb_pages()
    pdf.add_page()

    # Summary
    total = len(leads)
    with_email = sum(1 for l in leads if l.get("email"))
    with_phone = sum(1 for l in leads if l.get("phone"))
    pdf.add_summary(total, with_email, with_phone, query or "All Leads")

    # Table
    if leads:
        pdf.add_leads_table(leads)

    pdf.output(str(filepath))
    return filepath

