"""
Lead Extractor Pro - Live Browser Automation
Streamlit UI that connects to FastAPI WebSocket server for real-time browser visualization.
"""
from __future__ import annotations

import os
import streamlit as st
import pandas as pd
import json
import sys
import threading
import time
import websocket
from queue import Queue, Empty
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

# Thread-safe ref for WebSocket (Stop button). Session state must NOT be touched from WS thread.
_ws_client_ref = [None]

from app.config import (
    APP_NAME, APP_VERSION, LICENSE_KEY, LICENSE_SECRET, EXPORT_DIR,
    WEBSOCKET_URL, AUTOMATION_SERVER_URL, PROJECT_ROOT,
    BRAND_SHORT, BRAND_TAGLINE, BRAND_GLYPH,
)
from app.license.validator import validate_license
from app.license.activation_ui import check_license, show_activation_dialog, show_license_status
from app.database.db import (
    get_all_leads,
    get_lead_stats,
    get_searches_for_queries,
    get_leads_by_search,
    maybe_prune_stale_searches,
    delete_leads_by_ids,
)
from app.export.exporter import (
    export_to_csv,
    export_to_excel,
    COLUMN_PRESETS,
    leads_to_dataframe,
    filter_merged_leads_for_export,
)
from app.export.pdf_exporter import export_to_pdf
from app.config_manager import load_settings, save_settings
from app.utils.download_ui import download_button_with_fallback
from app.lead_manager import (
    upload_leads_from_file,
    save_external_leads,
    get_external_leads,
    get_domain_statistics,
    delete_external_leads,
    compare_with_extracted_leads,
)
from app.lead_manager.validator import validate_email
from app.lead_manager.domain_filter import filter_leads_by_domain, get_domain_stats


# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon=BRAND_GLYPH,
    layout="wide",
    initial_sidebar_state="collapsed",  # NEXUS: sidebar starts hidden, top strip carries status
)

# Delete lead/search data older than LEADS_RETENTION_DAYS (default 30); runs at most once / 24h
try:
    maybe_prune_stale_searches(interval_hours=24.0)
except Exception:
    pass

# ─── NEXUS Design System ─────────────────────────────────────────────────────
# Two themes — NEXUS dark (default) and ATLAS light. Active theme's CSS vars
# are injected directly into :root so the toggle works reliably regardless of
# Streamlit's iframe sandboxing (a JS-driven [data-theme] attribute can't reach
# the parent DOM from a markdown-injected <script>).
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

# Theme variables — selected at render time based on session state
if st.session_state.theme == "light":
    _theme_vars = """
        --bg:           #F8FAFC;
        --bg-elev:      #FFFFFF;
        --surface:      #FFFFFF;
        --surface-2:    #F1F5F9;
        --surface-3:    #E2E8F0;
        --border:       #E2E8F0;
        --border-soft:  #EDF2F7;
        --primary:      #4F46E5;
        --primary-hov:  #4338CA;
        --primary-dim:  #6366F1;
        --accent:       #0891B2;
        --accent-dim:   #0E7490;
        --success:      #059669;
        --warning:      #D97706;
        --danger:       #DC2626;
        --danger-hov:   #B91C1C;
        --text-1:       #0F172A;
        --text-2:       #475569;
        --text-3:       #94A3B8;
        --shadow-card:  0 1px 3px rgba(15,23,42,0.06), 0 4px 12px rgba(15,23,42,0.04);
        --shadow-btn:   0 4px 12px rgba(79, 70, 229, 0.18);
        --glow-input:   0 0 0 3px rgba(79, 70, 229, 0.18);
    """
    # Hardcoded hex fallbacks for button chrome — bypass CSS-var resolution on baseweb elements
    _btn_bg     = "#F1F5F9"
    _btn_bg_hov = "#E2E8F0"
    _btn_text   = "#0F172A"
    _btn_border = "#E2E8F0"
else:
    _theme_vars = """
        --bg:           #0F0F1A;
        --bg-elev:      #0A0A14;
        --surface:      #17172A;
        --surface-2:    #1E1E35;
        --surface-3:    #252540;
        --border:       #2E2E50;
        --border-soft:  #232340;
        --primary:      #6366F1;
        --primary-hov:  #818CF8;
        --primary-dim:  #4F46E5;
        --accent:       #22D3EE;
        --accent-dim:   #0891B2;
        --success:      #10B981;
        --warning:      #F59E0B;
        --danger:       #EF4444;
        --danger-hov:   #DC2626;
        --text-1:       #F1F5F9;
        --text-2:       #94A3B8;
        --text-3:       #64748B;
        --shadow-card:  0 1px 0 rgba(255,255,255,0.04) inset, 0 8px 24px rgba(0,0,0,0.3);
        --shadow-btn:   0 4px 12px rgba(99, 102, 241, 0.25);
        --glow-input:   0 0 0 3px rgba(99, 102, 241, 0.25);
    """
    # Hardcoded hex fallbacks for button chrome — bypass CSS-var resolution on baseweb elements
    _btn_bg     = "#1E1E35"
    _btn_bg_hov = "#252540"
    _btn_text   = "#F1F5F9"
    _btn_border = "#2E2E50"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* ── Active theme tokens (swapped via session_state.theme) ───────────── */
    :root, html, body, .stApp {{
        {_theme_vars}
    }}

    /* ── Hide Streamlit chrome ───────────────────────────────────────────── */
    #MainMenu, footer, header {{ visibility: hidden; }}

    /* ── App-wide ────────────────────────────────────────────────────────── */
    html, body, [class*="css"] {{
        font-family: 'Plus Jakarta Sans', -apple-system, system-ui, sans-serif !important;
        background: var(--bg) !important;
        color: var(--text-1) !important;
    }}
    .stApp {{ background: var(--bg) !important; }}
    .block-container {{ padding-top: 0.5rem !important; max-width: 1280px; }}

    /* Typography */
    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: var(--text-1) !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em;
    }}
    p, span, label, div {{ color: var(--text-1); }}
    .stCaption, .caption, [data-testid="stCaptionContainer"] {{
        color: var(--text-2) !important;
        font-size: 0.82rem !important;
    }}
    /* Scope code styling to text content only — don't leak into form inputs */
    .stMarkdown code, .stMarkdown pre, .stMarkdown kbd,
    p code, li code, span code, h1 code, h2 code, h3 code {{
        font-family: 'JetBrains Mono', 'Menlo', monospace !important;
        background: var(--bg-elev) !important;
        color: var(--accent) !important;
        border-radius: 4px;
        padding: 1px 6px;
        font-size: 0.85em;
    }}

    /* ── Brand ───────────────────────────────────────────────────────────── */
    .nexus-brand {{
        display: flex;
        align-items: center;
        gap: 10px;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }}
    .nexus-glyph {{
        font-size: 1.4rem;
        color: var(--accent);
        text-shadow: 0 0 12px rgba(34, 211, 238, 0.6);
        animation: nexus-pulse 3s ease-in-out infinite;
    }}
    @keyframes nexus-pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.7; }}
    }}
    .nexus-brand-name {{
        font-size: 1.1rem;
        font-weight: 800;
        color: var(--text-1);
        letter-spacing: 0.04em;
    }}
    .nexus-brand-tag {{
        font-size: 0.72rem;
        color: var(--text-2);
        font-weight: 500;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }}

    /* Page titles */
    .app-title {{
        font-size: 1.65rem !important;
        font-weight: 800 !important;
        color: var(--text-1) !important;
        margin: 4px 0 2px 0 !important;
        letter-spacing: -0.02em;
    }}
    .app-subtitle {{
        color: var(--text-2) !important;
        font-size: 0.88rem !important;
        margin: -2px 0 16px 0 !important;
        font-weight: 500;
    }}

    /* ── Top status strip ────────────────────────────────────────────────── */
    .nexus-topbar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 16px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        margin-bottom: 14px;
        box-shadow: var(--shadow-card);
    }}
    .nexus-chip {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 10px;
        background: var(--surface-2);
        border: 1px solid var(--border);
        border-radius: 999px;
        font-size: 0.75rem;
        color: var(--text-2);
        font-weight: 500;
    }}
    .nexus-chip-dot {{
        width: 7px; height: 7px; border-radius: 50%;
        background: var(--text-3);
    }}
    .nexus-chip-dot.live    {{ background: var(--accent); box-shadow: 0 0 0 3px rgba(34, 211, 238, 0.2); animation: live-dot-pulse 1.4s ease-in-out infinite; }}
    .nexus-chip-dot.success {{ background: var(--success); }}
    .nexus-chip-dot.warn    {{ background: var(--warning); }}
    .nexus-chip-dot.danger  {{ background: var(--danger); }}

    /* ── Cards ───────────────────────────────────────────────────────────── */
    .nexus-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 14px;
        box-shadow: var(--shadow-card);
    }}
    .nexus-card-label {{
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--text-2);
        margin-bottom: 8px;
    }}
    .nexus-card-accent {{
        border-top: 2px solid var(--primary);
    }}

    /* ── Buttons — hardcoded hex so Streamlit's baseweb/config.toml values
          (which can survive CSS-var resolution failures) never win ─────── */
    body .stApp .stButton > button,
    body .stApp .stDownloadButton > button,
    .stApp .stButton > button,
    .stApp .stDownloadButton > button,
    div[data-testid="stButton"] > button,
    div[data-testid="stDownloadButton"] > button {{
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        transition: all 0.15s ease !important;
        border: 1px solid {_btn_border} !important;
        background: {_btn_bg} !important;
        background-color: {_btn_bg} !important;
        background-image: none !important;
        color: {_btn_text} !important;
        -webkit-text-fill-color: {_btn_text} !important;
        box-shadow: none !important;
    }}
    body .stApp .stButton > button *,
    body .stApp .stDownloadButton > button *,
    .stApp .stButton > button *,
    .stApp .stDownloadButton > button *,
    div[data-testid="stButton"] > button *,
    div[data-testid="stDownloadButton"] > button * {{
        color: {_btn_text} !important;
        -webkit-text-fill-color: {_btn_text} !important;
        background: transparent !important;
        background-color: transparent !important;
    }}
    body .stApp .stButton > button:hover,
    body .stApp .stDownloadButton > button:hover,
    .stApp .stButton > button:hover,
    .stApp .stDownloadButton > button:hover,
    div[data-testid="stButton"] > button:hover,
    div[data-testid="stDownloadButton"] > button:hover {{
        background: {_btn_bg_hov} !important;
        background-color: {_btn_bg_hov} !important;
        background-image: none !important;
        border-color: var(--primary) !important;
        color: {_btn_text} !important;
        -webkit-text-fill-color: {_btn_text} !important;
    }}
    .stApp .stButton > button[kind="primary"],
    .stApp .stDownloadButton > button[kind="primary"] {{
        background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%) !important;
        background-color: var(--primary) !important;
        border: none !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        box-shadow: var(--shadow-btn) !important;
    }}
    .stApp .stButton > button[kind="primary"] *,
    .stApp .stDownloadButton > button[kind="primary"] * {{
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        background: transparent !important;
    }}
    .stApp .stButton > button[kind="primary"]:hover,
    .stApp .stDownloadButton > button[kind="primary"]:hover {{
        filter: brightness(1.12);
        transform: translateY(-1px);
    }}
    .stApp .stButton > button[disabled] {{ opacity: 0.4 !important; cursor: not-allowed !important; }}

    /* ── Tooltips (Streamlit baseweb tooltips show as white otherwise) ───── */
    [data-baseweb="tooltip"],
    [role="tooltip"] {{
        background: var(--surface-3) !important;
        background-color: var(--surface-3) !important;
        color: var(--text-1) !important;
        -webkit-text-fill-color: var(--text-1) !important;
        border: 1px solid var(--border) !important;
        border-radius: 6px !important;
        box-shadow: var(--shadow-card) !important;
        font-size: 0.78rem !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        padding: 6px 10px !important;
    }}
    [data-baseweb="tooltip"] *,
    [role="tooltip"] * {{
        color: var(--text-1) !important;
        -webkit-text-fill-color: var(--text-1) !important;
        background: transparent !important;
    }}

    /* ── Inputs (strong selectors so Streamlit defaults don't win) ───────── */
    .stTextInput input,
    .stTextArea textarea,
    .stNumberInput input,
    .stSelectbox [data-baseweb="select"] > div,
    .stDateInput input {{
        background: var(--surface-2) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-1) !important;
        border-radius: 8px !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        -webkit-text-fill-color: var(--text-1) !important;  /* Safari/WebKit fix */
        caret-color: var(--primary) !important;
    }}
    .stTextArea textarea {{
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.9rem !important;
        color: var(--text-1) !important;
        -webkit-text-fill-color: var(--text-1) !important;
        line-height: 1.55 !important;
    }}
    .stTextArea textarea::placeholder,
    .stTextInput input::placeholder,
    .stNumberInput input::placeholder {{
        color: var(--text-3) !important;
        -webkit-text-fill-color: var(--text-3) !important;
        opacity: 0.8 !important;
    }}
    .stTextInput input:focus,
    .stTextArea textarea:focus,
    .stNumberInput input:focus {{
        border-color: var(--primary) !important;
        box-shadow: var(--glow-input) !important;
        outline: none !important;
    }}
    /* Streamlit wraps inputs in baseweb containers — force their bg too */
    [data-baseweb="input"],
    [data-baseweb="textarea"],
    [data-baseweb="select"],
    [data-baseweb="base-input"] {{
        background: var(--surface-2) !important;
    }}
    [data-baseweb="input"] *,
    [data-baseweb="textarea"] *,
    [data-baseweb="select"] *,
    [data-baseweb="base-input"] * {{
        color: var(--text-1) !important;
        background-color: transparent !important;
    }}
    /* Number input +/- buttons (these stubbornly stay dark otherwise) */
    .stNumberInput button,
    .stNumberInput [data-testid="stNumberInputStepDown"],
    .stNumberInput [data-testid="stNumberInputStepUp"] {{
        background: var(--surface-3) !important;
        color: var(--text-1) !important;
        border-color: var(--border) !important;
    }}
    .stNumberInput button:hover {{
        background: var(--primary) !important;
        color: #FFFFFF !important;
    }}
    /* Checkboxes & radios */
    .stCheckbox label, .stRadio label {{ color: var(--text-1) !important; }}
    /* Selectbox dropdown */
    [data-baseweb="popover"] {{ background: var(--surface) !important; }}
    [data-baseweb="popover"] * {{ color: var(--text-1) !important; }}

    /* ── Metrics ─────────────────────────────────────────────────────────── */
    [data-testid="stMetric"] {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 14px 16px;
        box-shadow: var(--shadow-card);
    }}
    [data-testid="stMetricLabel"] {{
        color: var(--text-2) !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }}
    [data-testid="stMetricValue"] {{
        color: var(--text-1) !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 1.9rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
    }}

    /* ── Progress bar ────────────────────────────────────────────────────── */
    .stProgress > div > div > div > div {{
        background: linear-gradient(90deg, var(--primary), var(--accent)) !important;
    }}
    .stProgress > div > div > div {{ background: var(--surface-2) !important; }}

    /* ── Activity log ────────────────────────────────────────────────────── */
    .activity-log {{
        background: var(--bg-elev);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 12px 14px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.76rem;
        color: var(--accent);
        max-height: 400px;
        overflow-y: auto;
        line-height: 1.5;
        white-space: pre-wrap;
    }}
    .activity-log::-webkit-scrollbar {{ width: 6px; }}
    .activity-log::-webkit-scrollbar-track {{ background: transparent; }}
    .activity-log::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}

    /* ── Live extraction status bar ──────────────────────────────────────── */
    .extraction-status-bar {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 14px 18px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-left: 3px solid var(--accent);
        border-radius: 10px;
        margin-bottom: 12px;
        font-size: 0.92rem;
        color: var(--text-1);
        box-shadow: var(--shadow-card);
    }}
    .extraction-status-bar code {{
        background: var(--bg-elev) !important;
        color: var(--accent) !important;
        padding: 4px 10px;
        font-size: 0.85em;
    }}
    .live-dot {{
        width: 10px;
        height: 10px;
        background: var(--accent);
        border-radius: 50%;
        flex-shrink: 0;
        box-shadow: 0 0 0 3px rgba(34, 211, 238, 0.22);
        animation: live-dot-pulse 1.4s ease-in-out infinite;
    }}
    @keyframes live-dot-pulse {{
        0%, 100% {{ opacity: 1; transform: scale(1); }}
        50%      {{ opacity: 0.55; transform: scale(0.9); }}
    }}

    /* ── Tabs ────────────────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        background: var(--surface);
        padding: 6px;
        border-radius: 10px;
        border: 1px solid var(--border);
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent !important;
        color: var(--text-2) !important;
        border-radius: 6px !important;
        padding: 8px 16px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        border: none !important;
    }}
    .stTabs [aria-selected="true"] {{
        background: var(--surface-2) !important;
        color: var(--text-1) !important;
    }}

    /* ── Expanders ───────────────────────────────────────────────────────── */
    [data-testid="stExpander"] {{
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
    }}
    [data-testid="stExpander"] summary {{
        color: var(--text-1) !important;
        font-weight: 600 !important;
    }}

    /* ── Sidebar (collapsed by default; when expanded gets NEXUS treatment) ─ */
    [data-testid="stSidebar"] {{
        background: var(--surface) !important;
        border-right: 1px solid var(--border);
    }}
    [data-testid="stSidebar"] * {{ color: var(--text-1); }}

    /* ── Alerts (success/info/warning/error) ─────────────────────────────── */
    [data-testid="stAlert"] {{
        border-radius: 10px !important;
        border: 1px solid var(--border) !important;
        background: var(--surface) !important;
    }}
    [data-testid="stAlert"] * {{ color: var(--text-1) !important; }}

    /* Radio (horizontal nav uses this) */
    .stRadio [role="radiogroup"] label {{
        background: var(--surface-2) !important;
        color: var(--text-1) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px;
        padding: 6px 14px;
        margin-right: 6px;
        font-weight: 600;
        font-size: 0.85rem;
    }}
    .stRadio [role="radiogroup"] label:has(input:checked) {{
        background: linear-gradient(135deg, var(--primary), var(--accent)) !important;
        border-color: transparent !important;
        color: #FFFFFF !important;
    }}
    .stRadio [role="radiogroup"] label:has(input:checked) * {{ color: #FFFFFF !important; }}

    /* File uploader */
    [data-testid="stFileUploader"] section {{
        background: var(--surface) !important;
        border: 1px dashed var(--border) !important;
        border-radius: 10px;
    }}
    [data-testid="stFileUploader"] section * {{ color: var(--text-1) !important; }}

    /* Checkbox squares */
    .stCheckbox [data-baseweb="checkbox"] {{ color: var(--text-1) !important; }}

    /* ── Dataframe ───────────────────────────────────────────────────────── */
    [data-testid="stDataFrame"] {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
    }}

    /* ── Browser screenshot frame ────────────────────────────────────────── */
    .browser-view {{
        border: 1px solid var(--border);
        border-radius: 10px;
        background: var(--bg-elev);
        padding: 6px;
    }}

    /* ── Misc cleanup ────────────────────────────────────────────────────── */
    hr, [data-testid="stDivider"] {{
        border-color: var(--border) !important;
        background: var(--border) !important;
        opacity: 0.6;
    }}
    .top-nav, .bottom-nav, .nav-button {{ display: none !important; }}  /* old nav hidden */
    .extraction-meta  {{ color: var(--text-2); font-size: 0.82rem; }}
    .extraction-detail {{
        font-size: 0.78rem;
        color: var(--text-2);
        margin: -4px 0 10px 0;
        padding-left: 19px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}

    /* ── Button click feedback (instant visual response) ─────────────── */
    .stApp .stButton > button:active,
    .stApp .stDownloadButton > button:active {{
        transform: scale(0.97) !important;
        opacity: 0.85 !important;
        transition: transform 0.05s ease, opacity 0.05s ease !important;
    }}
    .stApp .stButton > button[kind="primary"]:active {{
        transform: scale(0.97) translateY(0) !important;
        filter: brightness(0.92) !important;
    }}

    /* ── Spinner theming ─────────────────────────────────────────────── */
    .stSpinner > div {{
        border-top-color: var(--primary) !important;
    }}
    [data-testid="stSpinnerContainer"],
    .stSpinner {{
        color: var(--text-2) !important;
    }}
    [data-testid="stStatusWidget"] {{
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text-2) !important;
    }}

    /* ── Toast / notification styling ─────────────────────────────────── */
    [data-testid="stToast"] {{
        background: var(--surface) !important;
        color: var(--text-1) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        box-shadow: var(--shadow-card) !important;
    }}
    [data-testid="stToast"] * {{
        color: var(--text-1) !important;
    }}

    /* ── Smooth transitions for interactive elements ──────────────────── */
    .stRadio [role="radiogroup"] label {{
        transition: all 0.12s ease !important;
        cursor: pointer;
    }}
    .stRadio [role="radiogroup"] label:hover {{
        background: var(--surface-3) !important;
        border-color: var(--primary-dim) !important;
    }}
    .stRadio [role="radiogroup"] label:active {{
        transform: scale(0.97);
    }}

    /* ── Running / Streamlit rerun overlay ─────────────────────────────── */
    [data-testid="stAppViewBlockContainer"][data-stale="true"] {{
        opacity: 0.55;
        pointer-events: none;
        transition: opacity 0.15s ease;
    }}
</style>
""", unsafe_allow_html=True)


# ─── Session State ───────────────────────────────────────────────────────────
if "activity_log" not in st.session_state:
    st.session_state.activity_log = []
if "extracted_leads" not in st.session_state:
    st.session_state.extracted_leads = []
if "current_screenshot" not in st.session_state:
    st.session_state.current_screenshot = None
if "is_running" not in st.session_state:
    st.session_state.is_running = False
if "websocket_connected" not in st.session_state:
    st.session_state.websocket_connected = False
if "settings" not in st.session_state:
    st.session_state.settings = load_settings()
if "last_update" not in st.session_state:
    st.session_state.last_update = 0
if "needs_refresh" not in st.session_state:
    st.session_state.needs_refresh = False
if "current_lead_count" not in st.session_state:
    st.session_state.current_lead_count = 0
if "target_lead_count" not in st.session_state:
    st.session_state.target_lead_count = 0
if "saved_files" not in st.session_state:
    st.session_state.saved_files = []
if "server_checked" not in st.session_state:
    st.session_state.server_checked = False
if "current_page" not in st.session_state:
    st.session_state.current_page = "🔍 Live Extractor"
if "search_engine" not in st.session_state:
    st.session_state.search_engine = st.session_state.settings.get("search_engine", "duckduckgo")
if "live_queries_for_sessions" not in st.session_state:
    st.session_state.live_queries_for_sessions = []
if "live_search_site_domains" not in st.session_state:
    st.session_state.live_search_site_domains = st.session_state.settings.get("search_site_domains", "")
if "live_email_domain_allowlist" not in st.session_state:
    st.session_state.live_email_domain_allowlist = st.session_state.settings.get("email_domain_allowlist", "")
if "query_current" not in st.session_state:
    st.session_state.query_current = ""
if "query_progress_idx" not in st.session_state:
    st.session_state.query_progress_idx = 0
if "query_total" not in st.session_state:
    st.session_state.query_total = 0
if "emails_collected" not in st.session_state:
    st.session_state.emails_collected = 0
if "ext_leads_last_imported" not in st.session_state:
    st.session_state.ext_leads_last_imported = 0
if "ext_validation_results" not in st.session_state:
    st.session_state.ext_validation_results = None
if "extracted_validation_results" not in st.session_state:
    st.session_state.extracted_validation_results = None


def _run_validation_with_progress(leads: list) -> dict:
    """
    Validate + deduplicate a list of lead dicts.
    Phase 1: parallel DNS MX pre-fetch for all unique domains (20 threads).
    Phase 2: per-email format+MX check using the warm cache (fast).
    Returns a results dict compatible with both tabs.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from app.lead_manager.validator import _check_mx, validate_email as _vld

    bar = st.progress(0, text="Phase 1/2: finding unique domains…")
    status = st.empty()

    # Pre-filter: only leads that actually have an email address.
    # Leads without emails are skipped but counting them in "total" would make
    # the metrics misleading (valid + dup + invalid ≠ checked).
    leads_with_email = [l for l in leads if "@" in (l.get("email") or "")]
    no_email_count = len(leads) - len(leads_with_email)
    total = len(leads_with_email)

    # Extract unique domains for Phase 1
    unique_domains: list = []
    seen_d: set = set()
    for lead in leads_with_email:
        domain = (lead.get("email") or "").strip().lower().split("@", 1)[1]
        if domain not in seen_d:
            seen_d.add(domain)
            unique_domains.append(domain)

    n_domains = len(unique_domains)
    status.caption(
        f"Found {n_domains} unique domain(s) across {total:,} leads"
        + (f" ({no_email_count:,} skipped — no email)" if no_email_count else "")
        + " — checking mail servers…"
    )

    # Phase 1: parallel MX lookups
    completed = 0
    if unique_domains:
        with ThreadPoolExecutor(max_workers=25) as pool:
            futures = {pool.submit(_check_mx, d): d for d in unique_domains}
            for fut in as_completed(futures):
                completed += 1
                bar.progress(
                    completed / n_domains * 0.5,
                    text=f"Phase 1/2: checked {completed}/{n_domains} domains…",
                )

    # Phase 2: validate each lead using cached MX results
    valid_ids, invalid_ids, dup_ids = [], [], []
    valid_leads_data, invalid_detail = [], []
    seen_emails: set = set()

    bar.progress(0.5, text="Phase 2/2: validating emails…")
    UPDATE_EVERY = max(1, total // 200)  # update bar ~200 times

    for i, lead in enumerate(leads_with_email):
        email = (lead.get("email") or "").strip().lower()
        if email in seen_emails:
            dup_ids.append(lead.get("id"))
        else:
            seen_emails.add(email)
            result = _vld(email)
            if result.is_valid:
                valid_ids.append(lead.get("id"))
                valid_leads_data.append(lead)
            else:
                invalid_ids.append(lead.get("id"))
                invalid_detail.append(f"{email} — {result.error_message}")

        if i % UPDATE_EVERY == 0:
            pct = 0.5 + (i / total) * 0.5 if total else 1.0
            bar.progress(pct, text=f"Phase 2/2: {i+1:,} / {total:,} validated…")

    bar.progress(1.0, text="Done!")
    status.empty()

    return {
        "valid_ids": valid_ids,
        "invalid_ids": invalid_ids,
        "dup_ids": dup_ids,
        "valid_leads_data": valid_leads_data,
        "invalid_detail": invalid_detail,
        "valid_count": len(valid_ids),
        "invalid_count": len(invalid_ids),
        "dup_count": len(dup_ids),
        "total_checked": total,
        "no_email_count": no_email_count,
    }


def _render_validation_results(vr: dict, dl_key_prefix: str) -> None:
    """Render the validation results panel (shared by both tabs)."""
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Checked", f"{vr['total_checked']:,}")
    mc2.metric("✅ Valid unique", f"{vr['valid_count']:,}")
    mc3.metric("🔁 Duplicates", f"{vr['dup_count']:,}")
    mc4.metric("❌ Invalid", f"{vr['invalid_count']:,}")
    if vr.get("no_email_count"):
        st.caption(f"ℹ️ {vr['no_email_count']:,} row(s) had no email address and were excluded from validation.")

    if vr["invalid_detail"]:
        with st.expander(f"Show {vr['invalid_count']:,} invalid email(s)"):
            st.code("\n".join(vr["invalid_detail"][:500]))

    removable = len(vr["invalid_ids"]) + len(vr["dup_ids"])
    if removable:
        st.info(
            f"**{removable:,} rows can be removed** — "
            f"{vr['dup_count']:,} duplicates + {vr['invalid_count']:,} invalid. "
            f"After cleaning: **{vr['valid_count']:,} unique valid leads**."
        )

    act1, act2 = st.columns(2)
    with act1:
        if vr["valid_leads_data"]:
            vdf = pd.DataFrame(vr["valid_leads_data"])
            vcols = [c for c in ["email", "domain", "contact_name", "business_name", "phone"] if c in vdf.columns]
            download_button_with_fallback(
                f"⬇️ Download valid only ({vr['valid_count']:,})",
                data=vdf[vcols].to_csv(index=False).encode(),
                file_name="leads_valid_unique.csv",
                mime="text/csv",
                key=f"{dl_key_prefix}_dl_valid",
            )
    with act2:
        if vr["valid_leads_data"]:
            download_button_with_fallback(
                "⬇️ Download all (no filter)",
                data=pd.DataFrame(vr["valid_leads_data"] + []).to_csv(index=False).encode(),
                file_name="leads_all.csv",
                mime="text/csv",
                key=f"{dl_key_prefix}_dl_all",
            )


def generate_queries(footprints: list, patterns: list, locations: list) -> list:
    """Cross-product: footprint × @pattern × location → list of search query strings."""
    queries = []
    for fp in footprints:
        fp = fp.strip()
        if not fp:
            continue
        for pat in patterns:
            pat = pat.strip().lstrip("@")
            if not pat:
                continue
            for loc in locations:
                loc = loc.strip()
                if not loc:
                    continue
                q = f'{fp} "@{pat}" {loc}'
                queries.append(q)
    return queries


# ─── WebSocket Client (URL from app.config, supports local + cloud) ───────────
# CRITICAL: WebSocket callbacks run in a background thread. They must NOT touch
# st.session_state directly - that causes "missing ScriptRunContext" and connection drops.
# Instead, put updates in a queue; main thread drains it and updates session state.


def websocket_client(
    queries: List[str],
    max_pages: int,
    delay_pages: float,
    delay_actions: float,
    msg_queue: Queue,
    target_leads: int,
    search_engine: str,
    headless: bool,
    batch_reload: bool = False,
    email_domain_allowlist: str = "",
    search_site_domains: str = "",
):
    """Connect to WebSocket server. Callbacks put updates in msg_queue (no session state)."""
    def on_message(ws, message):
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            if msg_type == "status":
                msg_queue.put(("status", data.get("message", "")))
            elif msg_type == "screenshot":
                msg_queue.put(("screenshot", data.get("data", "")))
            elif msg_type == "ping":
                pass
            elif msg_type == "leads":
                msg_queue.put(("leads", data.get("data", [])))
            elif msg_type == "lead_count":
                msg_queue.put(("lead_count", (data.get("count", 0), data.get("target", 0))))
            elif msg_type == "query_progress":
                msg_queue.put(("query_progress", {
                    "current_query": data.get("current_query", ""),
                    "current": data.get("current", 0),
                    "total": data.get("total", 0),
                }))
            elif msg_type == "file_saved":
                msg_queue.put(("file_saved", {
                    "path": data.get("path", ""),
                    "query": data.get("query", ""),
                    "count": data.get("count", 0),
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                }))
            elif msg_type == "complete":
                msg_queue.put(("complete", data.get("data", [])))
            elif msg_type == "error":
                msg_queue.put(("error", data.get("message", "")))
        except Exception as e:
            msg_queue.put(("status", f"❌ Error: {str(e)}"))

    def on_error(ws, error):
        msg_queue.put(("error", str(error)))
        msg_queue.put(("closed", None))

    def on_close(ws, close_status_code, close_msg):
        msg_queue.put(("closed", None))

    def on_open(ws):
        _ws_client_ref[0] = ws
        msg_queue.put(("connected", None))
        ws.send(json.dumps({
            "command": "start",
            "queries": queries,
            "max_pages": max_pages,
            "delay_pages": delay_pages,
            "delay_actions": delay_actions,
            "target_leads": target_leads,
            "search_engine": search_engine,
            "headless": headless,
            "reload_between_queries": batch_reload,
            "email_domain_allowlist": email_domain_allowlist,
            "search_site_domains": search_site_domains,
        }))

    try:
        _ws_client_ref[0] = None
        ws = websocket.WebSocketApp(
            WEBSOCKET_URL,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open,
        )
        ws.run_forever()
    except Exception as e:
        msg_queue.put(("error", str(e)))
        msg_queue.put(("closed", None))
    finally:
        msg_queue.put(("closed", None))  # Ensure UI updates when thread exits
        _ws_client_ref[0] = None


def run_websocket_client(
    queries: List[str],
    max_pages: int,
    delay_pages: float,
    delay_actions: float,
    msg_queue: Queue,
    target_leads: int,
    search_engine: str,
    headless: bool,
    batch_reload: bool = False,
    email_domain_allowlist: str = "",
    search_site_domains: str = "",
):
    """Run WebSocket client in background thread."""
    websocket_client(
        queries,
        max_pages,
        delay_pages,
        delay_actions,
        msg_queue,
        target_leads,
        search_engine,
        headless,
        batch_reload,
        email_domain_allowlist,
        search_site_domains,
    )


def drain_ws_queue(msg_queue: Queue) -> bool:
    """Process queued WebSocket updates on main thread. Returns True if needs rerun."""
    if msg_queue is None:
        return False
    changed = False
    while True:
        try:
            item = msg_queue.get_nowait()
        except Empty:
            break
        msg_type, data = item
        if msg_type == "status":
            st.session_state.activity_log.append(data)
            if len(st.session_state.activity_log) > 200:
                st.session_state.activity_log = st.session_state.activity_log[-200:]
            changed = True
        elif msg_type == "screenshot" and data:
            if not hasattr(st.session_state, 'last_screenshot_update'):
                st.session_state.last_screenshot_update = 0
            now = time.time()
            if (now - st.session_state.last_screenshot_update) >= 0.5:  # Update every 0.5s for responsive Live View
                st.session_state.current_screenshot = data
                st.session_state.last_screenshot_update = now
                st.session_state.needs_refresh = True
                st.session_state.last_update = now
                changed = True
        elif msg_type == "leads":
            # Only update lead buffers while a run is actively in progress.
            # If stop was already clicked, discard stale in-flight messages so
            # the counter freezes immediately rather than continuing to climb.
            if st.session_state.get("is_running"):
                st.session_state.extracted_leads.extend(data)
                st.session_state.current_lead_count = len(st.session_state.extracted_leads)
                st.session_state.needs_refresh = True
                st.session_state.last_update = time.time()
                changed = True
        elif msg_type == "lead_count":
            if st.session_state.get("is_running"):
                st.session_state.current_lead_count, st.session_state.target_lead_count = data
                st.session_state.emails_collected = data[0]
                st.session_state.needs_refresh = True
                st.session_state.last_update = time.time()
                changed = True
        elif msg_type == "query_progress":
            st.session_state.query_current = data.get("current_query", "")
            st.session_state.query_progress_idx = data.get("current", 0)
            st.session_state.query_total = data.get("total", 0)
            st.session_state.needs_refresh = True
            changed = True
        elif msg_type == "file_saved":
            st.session_state.saved_files.append(data)
            st.session_state.activity_log.append(f"💾 File saved: {data['path']} ({data['count']} leads)")
            changed = True
        elif msg_type == "complete":
            if data:
                st.session_state.extracted_leads = data
            st.session_state.activity_log.append("🎉 Automation completed!")
            st.session_state.is_running = False
            st.session_state.query_current = "✅ Done"
            st.session_state.needs_refresh = True
            st.session_state.last_update = time.time()
            st.session_state._terminal_rerun = True
            changed = True
        elif msg_type == "error":
            st.session_state.activity_log.append(f"❌ {data}")
            if "fatal" in str(data).lower() or "crash" in str(data).lower():
                st.session_state.is_running = False
                st.session_state._terminal_rerun = True
            st.session_state.needs_refresh = True
            changed = True
        elif msg_type == "connected":
            st.session_state.websocket_connected = True
            st.session_state.activity_log.append("✅ Connected — automation starting...")
            changed = True
        elif msg_type == "closed":
            st.session_state.websocket_connected = False
            st.session_state.is_running = False
            st.session_state._terminal_rerun = True
            changed = True
    return changed


def _escape_html(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _render_live_panel_content(*, extracting: bool):
    """Browser screenshot + activity log + optional extraction banner."""
    if extracting:
        n = len(st.session_state.get("extracted_leads", []))
        last = ""
        if st.session_state.activity_log:
            last = str(st.session_state.activity_log[-1])
        st.markdown(
            '<div class="extraction-status-bar">'
            '<span class="live-dot"></span>'
            "<strong>Extracting</strong>"
            f'<span class="extraction-meta">{n} lead(s) collected · live updates</span>'
            "</div>",
            unsafe_allow_html=True,
        )
        if last:
            st.markdown(
                f'<div class="extraction-detail" title="{_escape_html(last)}">'
                f"{_escape_html(last)}</div>",
                unsafe_allow_html=True,
            )

    col_browser, col_log = st.columns([1.2, 0.8])
    with col_browser:
        st.markdown("### 🖥️ Live Browser View")
        if st.session_state.current_screenshot:
            st.image(
                f"data:image/png;base64,{st.session_state.current_screenshot}",
                use_container_width=True,
                caption="Live browser automation",
            )
        else:
            st.info("👆 Click **Start** to see live browser automation…")
    with col_log:
        st.markdown("### 📋 Activity Log")
        log_text = "\n".join(st.session_state.activity_log[-50:])
        st.markdown(f'<div class="activity-log">{_escape_html(log_text)}</div>', unsafe_allow_html=True)


@st.fragment(run_every=timedelta(seconds=1.15))
def _live_automation_fragment():
    """Refresh only this block while automation runs — avoids full-page Streamlit flashes."""
    q = st.session_state.get("ws_message_queue")
    if q:
        drain_ws_queue(q)
    if st.session_state.pop("_terminal_rerun", False):
        st.rerun()
    if not st.session_state.is_running:
        return

    # Status dashboard inside fragment so metrics update every 1.15s during a run
    q_current = st.session_state.get("query_current", "")
    q_idx = st.session_state.get("query_progress_idx", 0)
    q_total = st.session_state.get("query_total", 1)
    emails_col = st.session_state.get("emails_collected", 0)
    if q_current:
        st.markdown(
            f'<div class="extraction-status-bar"><span class="live-dot"></span>'
            f'<strong>Now running:</strong> <code>{_escape_html(q_current)}</code></div>',
            unsafe_allow_html=True,
        )
    dash_c1, dash_c2 = st.columns(2)
    with dash_c1:
        st.metric("Collected emails", emails_col)
    with dash_c2:
        st.metric("Progress", f"{q_idx} / {q_total} queries")
        if q_total > 0:
            st.progress(min(1.0, q_idx / q_total))
        if st.session_state.extracted_leads:
            _dl_df = leads_to_dataframe(st.session_state.extracted_leads)
            download_button_with_fallback(
                "⬇️ Download collected",
                data=_dl_df.to_csv(index=False).encode(),
                file_name="leads_in_progress.csv",
                mime="text/csv",
                key="dl_mid_run",
            )

    _render_live_panel_content(extracting=True)


def _render_live_query_sessions_panel():
    """Show all DB sessions matching the current / last-run query text(s) for merge, validate, export."""
    qs = list(st.session_state.get("live_queries_for_sessions") or [])
    if not qs:
        qi = (st.session_state.get("query_input") or "").strip()
        bq = st.session_state.get("batch_queries") or ""
        if bq.strip():
            qs = [x.strip() for x in bq.split("\n") if x.strip()][:10]
        elif qi:
            qs = [qi]
    if not qs:
        return

    try:
        matches = get_searches_for_queries(qs, limit=60)
    except Exception as e:
        st.caption(f"Could not load saved sessions: {e}")
        return

    if not matches:
        return

    st.divider()
    st.markdown("### 📚 Saved sessions for this query")
    st.caption(
        "Every run that used the same query text (after normalization). "
        "Select sessions, choose **Export mode** (same rules as Saved Leads), then **download or save** manually — "
        "nothing is exported automatically."
    )

    options = []
    opt_to_sid = {}
    for s in matches:
        sid = s["id"]
        n = s.get("num_leads", 0) or 0
        qshort = str(s.get("query", ""))[:52] + ("…" if len(str(s.get("query", ""))) > 52 else "")
        ts = str(s.get("created_at", ""))[:19]
        label = f"#{sid} · {n} leads · {ts} · {qshort}"
        options.append(label)
        opt_to_sid[label] = sid

    picked = st.multiselect(
        "Select sessions to merge",
        options=options,
        default=[],
        key="live_page_session_multiselect",
    )
    if not picked:
        st.info(
            "Select one or more sessions above. "
            "**Export mode** uses the same code as Saved Leads: **Full** = all rows as stored; "
            "**Unique** / **Unique valid** split cells that list several emails, then dedupe (and validate). "
            "If you still see one row, check the breakdown — often the other rows were **duplicates** of the same address."
        )
        return

    selected_ids = [opt_to_sid[l] for l in picked if l in opt_to_sid]
    merged: list[dict] = []
    for sid in selected_ids:
        for row in get_leads_by_search(sid):
            lead = {
                "business_name": row.get("business_name", ""),
                "contact_name": row.get("contact_name", ""),
                "email": row.get("email", ""),
                "phone": row.get("phone", ""),
                "website": row.get("website", ""),
                "source_url": row.get("source_url", ""),
                "snippet": row.get("snippet", ""),
                "_session_id": sid,
            }
            merged.append(lead)

    st.metric("Merged leads (raw, selected sessions)", len(merged))

    st.text_area(
        "Optional: email domain filter before download (one per line, same rules as Live allowlist)",
        height=68,
        key="live_export_email_domains",
        help="Applied only to this export. Examples: `gmail.com`, `@outlook.com`, `*.edu`. Leave empty to skip.",
    )
    export_mode = st.radio(
        "Export mode",
        [
            "Full (all leads, no dedup)",
            "Unique (dedup only, any email with @)",
            "Unique valid (dedup + strict validation)",
        ],
        key="live_query_export_mode",
        help="Same engine as Saved Leads. Multi-address cells are split before dedupe/validation.",
    )
    use_full = "Full" in export_mode
    use_validation = "valid" in export_mode.lower()
    _live_dom = (st.session_state.get("live_export_email_domains") or "").strip()

    export_leads, ex_stats = filter_merged_leads_for_export(
        merged,
        use_full=use_full,
        use_validation=use_validation,
        email_domain_allowlist=_live_dom if _live_dom else None,
    )

    if use_full:
        _dom = ex_stats.get("domain_filtered_count", 0)
        _full_msg = f"📋 {len(export_leads)} leads (full, no dedup)"
        if _dom:
            _full_msg += f" — {_dom} row(s) removed by domain filter"
        st.info(_full_msg)
    else:
        if use_validation:
            st.success(
                f"✅ {len(export_leads)} unique valid leads "
                f"(from {ex_stats['merged_raw']} merged rows → {ex_stats['rows_after_split']} after splitting multi-email cells)"
            )
        else:
            st.success(
                f"✅ {len(export_leads)} unique leads "
                f"(from {ex_stats['merged_raw']} merged rows → {ex_stats['rows_after_split']} after split, dedup only)"
            )
        with st.expander("📊 Breakdown (why rows were excluded)"):
            if ex_stats["rows_after_split"] != ex_stats["merged_raw"]:
                st.markdown(
                    f"- **Rows after splitting cells:** {ex_stats['rows_after_split']} "
                    f"(some rows listed several addresses in one email field)"
                )
            st.markdown(f"- **No usable email:** {ex_stats['no_email_count']}")
            if use_validation:
                st.markdown(f"- **Invalid format:** {ex_stats['invalid_count']} (failed `email_validator`, same as Saved Leads)")
            st.markdown(f"- **Duplicate email:** {ex_stats['dup_count']}")
            if ex_stats.get("domain_filtered_count", 0):
                st.markdown(f"- **Domain filter (export):** {ex_stats['domain_filtered_count']}")

    if not export_leads:
        st.warning(
            "No leads to preview or export — selected sessions may be empty, or **Unique valid** removed all rows. "
            "Try **Full** or **Unique (dedup only)**."
        )
        return

    preset = st.selectbox(
        "Filter columns to show/export",
        list(COLUMN_PRESETS.keys()),
        key="live_sess_preset",
    )
    export_cols = COLUMN_PRESETS[preset]

    dfm = pd.DataFrame(export_leads)
    show_cols = [c for c in export_cols if c in dfm.columns]
    if not show_cols:
        show_cols = [c for c in dfm.columns if c != "_session_id"]
    st.dataframe(dfm[show_cols], use_container_width=True, hide_index=True)

    st.markdown("**Download / save (manual only):**")
    e1, e2, e3 = st.columns(3)
    csv_bytes = leads_to_dataframe(export_leads, columns=export_cols).to_csv(index=False).encode()
    with e1:
        download_button_with_fallback(
            "⬇️ Download CSV",
            data=csv_bytes,
            file_name="merged_sessions.csv",
            mime="text/csv",
            key="live_sess_dl_csv",
        )
    with e2:
        if st.button("📄 Save CSV", key="live_sess_save_csv"):
            path = export_to_csv(
                export_leads,
                f"merged_live_{len(export_leads)}_leads.csv",
                columns=export_cols,
            )
            st.toast(f"Saved → {Path(str(path)).name}", icon="📄")
    with e3:
        if st.button("📊 Save Excel", key="live_sess_save_xlsx"):
            path = export_to_excel(
                export_leads,
                f"merged_live_{len(export_leads)}_leads.xlsx",
                columns=export_cols,
            )
            st.toast(f"Saved → {Path(str(path)).name}", icon="📊")


# ─── License Check ───────────────────────────────────────────────────────────
# License checking is now handled by activation_ui module

# Internal API values for automation (unchanged); UI labels stay vendor-neutral
_SEARCH_ENGINE_OPTIONS = ["duckduckgo", "google"]


def _search_provider_label(internal: str) -> str:
    if internal == "duckduckgo":
        return "Standard (recommended)"
    return "Alternative (may prompt for verification)"


def _search_provider_help() -> str:
    return (
        "Standard runs with fewer interruptions. "
        "Alternative may request human verification after repeated use."
    )


# ─── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar():
    """NEXUS sidebar — collapsed by default. Shows deeper details when user expands it."""
    with st.sidebar:
        st.markdown(
            f"""<div class="nexus-brand" style="margin-bottom:8px;">
                <span class="nexus-glyph" style="font-size:1.3rem;">{BRAND_GLYPH}</span>
                <div style="display:flex; flex-direction:column; line-height:1;">
                    <span class="nexus-brand-name">{BRAND_SHORT}</span>
                    <span class="nexus-brand-tag">v{APP_VERSION}</span>
                </div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.divider()

        # Show license status (from activation_ui)
        show_license_status()

        # Show user info if available
        if st.session_state.get("user"):
            user = st.session_state.user
            st.caption(f"User: {user.get('username', 'Unknown')}")
            st.caption(f"Plan: {user.get('plan', 'Unknown').upper()}")

        st.divider()

        st.markdown("### Engine")
        if "search_engine" not in st.session_state:
            st.session_state.search_engine = "duckduckgo"
        search_engine = st.selectbox(
            "Search provider",
            _SEARCH_ENGINE_OPTIONS,
            format_func=_search_provider_label,
            index=0 if st.session_state.search_engine == "duckduckgo" else 1,
            key="sidebar_search_engine",
            help=_search_provider_help(),
        )
        st.session_state.search_engine = search_engine
        if search_engine == "google":
            st.caption("Alternative provider may request verification after heavy use.")
        # Check server status
        if not st.session_state.server_checked:
            try:
                import httpx
                resp = httpx.get(f"{AUTOMATION_SERVER_URL.rstrip('/')}/", timeout=2)
                if resp.status_code == 200:
                    st.session_state.websocket_connected = True
                st.session_state.server_checked = True
            except Exception:
                st.session_state.websocket_connected = False
                st.session_state.server_checked = True
        
        if st.session_state.websocket_connected:
            st.success("✅ Server Connected")
        else:
            st.warning("⚠️ Server Not Connected")
            st.caption("Server should auto-start. If not, check terminal.")
        st.divider()

        st.markdown("### 📊 Stats")
        try:
            stats = get_lead_stats()
            st.metric("Searches", stats["total_searches"])
            st.metric("Leads", stats["total_leads"])
            st.metric("Emails", stats["unique_emails"])
            st.caption("All sessions")
            _ret = int(os.environ.get("LEADS_RETENTION_DAYS", "30"))
            if _ret > 0:
                st.caption(f"🗑️ Auto-delete sessions older than {_ret} days (LEADS_RETENTION_DAYS)")
        except Exception:
            st.caption("No data yet")


# ─── Top Navigation (single widget key = source of truth; avoids mixed tabs) ─
NAV_OPTIONS = ["🔍 Live Extractor", "📋 Saved Leads", "⚙️ Settings"]


def render_bottom_navigation():
    """
    NEXUS top status strip: brand + nav + status chips + theme toggle.
    (Function name kept for backward compatibility with main() call site.)
    """
    # Status chips data
    is_connected = bool(st.session_state.get("websocket_connected"))
    is_running = bool(st.session_state.get("is_running"))
    user = st.session_state.get("user") or {}
    plan = (user.get("plan") or "FREE").upper()
    try:
        stats = get_lead_stats()
        total_leads = int(stats.get("total_leads", 0))
    except Exception:
        total_leads = 0

    server_dot = "live" if is_running else ("success" if is_connected else "danger")
    server_lbl = "Running" if is_running else ("Connected" if is_connected else "Offline")
    theme_icon = "☀" if st.session_state.theme == "dark" else "☾"

    # Brand + status chips (HTML strip — visual only)
    st.markdown(f"""
    <div class="nexus-topbar">
      <div class="nexus-brand">
        <span class="nexus-glyph">{BRAND_GLYPH}</span>
        <div style="display:flex; flex-direction:column; line-height:1;">
          <span class="nexus-brand-name">{BRAND_SHORT}</span>
          <span class="nexus-brand-tag">{BRAND_TAGLINE}</span>
        </div>
      </div>
      <div style="display:flex; gap:8px; align-items:center;">
        <span class="nexus-chip"><span class="nexus-chip-dot {server_dot}"></span>{server_lbl}</span>
        <span class="nexus-chip">📧 {total_leads:,} leads</span>
        <span class="nexus-chip">🔐 {plan}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Nav radio + theme toggle row
    nav_col, theme_col = st.columns([5, 1])
    with nav_col:
        if "top_nav_radio" not in st.session_state:
            init = st.session_state.get("current_page")
            st.session_state.top_nav_radio = init if init in NAV_OPTIONS else NAV_OPTIONS[0]
        if st.session_state.top_nav_radio not in NAV_OPTIONS:
            st.session_state.top_nav_radio = NAV_OPTIONS[0]
        st.radio(
            label="Navigation",
            options=NAV_OPTIONS,
            horizontal=True,
            key="top_nav_radio",
            label_visibility="collapsed",
        )
        st.session_state.current_page = st.session_state.top_nav_radio
    with theme_col:
        if st.button(f"{theme_icon}  Theme", key="nexus_theme_toggle", use_container_width=True,
                     help="Toggle between NEXUS dark and ATLAS light"):
            st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
            st.rerun()


# ─── Main Extractor Page ─────────────────────────────────────────────────────
def render_extractor_page():
    import platform, subprocess
    q = st.session_state.get("ws_message_queue")
    drain_ws_queue(q)

    st.markdown('<p class="app-title">Live Extraction</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="app-subtitle">Build a query matrix from three lists. NEXUS runs every combination automatically and harvests leads in real time.</p>',
        unsafe_allow_html=True,
    )

    # ── Settings (collapsed) ─────────────────────────────────────────────────
    with st.expander("⚙️ Settings", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Automation**")
            max_pages = st.number_input(
                "Max pages per query", min_value=1, max_value=500,
                value=int(st.session_state.settings.get("max_pages", 10)), step=1,
                key="ext_max_pages",
            )
            st.session_state.settings["max_pages"] = max_pages
            delay_pages = st.number_input(
                "Delay between pages (s)", min_value=0.0, max_value=10.0, value=3.0, step=0.5,
                key="ext_delay_pages",
            )
            delay_actions = st.number_input(
                "Action delay (s)", min_value=0.0, max_value=5.0, value=1.0, step=0.1,
                key="ext_delay_actions",
            )
        with col2:
            st.markdown("**Connection**")
            headless_live = st.checkbox(
                "Run headless (no browser window)",
                value=bool(st.session_state.settings.get("headless", False)),
                key="live_headless",
            )
            st.session_state.settings["headless"] = headless_live
            target_leads = st.number_input(
                "Target lead count (0 = no limit)", min_value=0, max_value=500000,
                value=int(st.session_state.get("target_lead_count", 0)), step=500,
                key="ext_target_leads",
            )
            st.session_state.target_lead_count = target_leads
        st.markdown("**Domain targeting**")
        st.text_area(
            "Restrict search to these websites (optional, one per line)",
            height=80, key="live_search_site_domains",
            help="e.g. state.gov · university.edu. Do NOT list google.com/facebook.com.",
        )
        st.text_area(
            "Only keep leads with email on these domains (optional)",
            height=80, key="live_email_domain_allowlist",
            help="e.g. gmail.com | @company.org | *.edu",
        )

    st.divider()

    # ── Query Builder — three panels ─────────────────────────────────────────
    st.markdown("### Query Builder")
    st.caption(
        "Fill each column — every combination of **Footprint × @Pattern × Location** becomes one search query. "
        "Queries run automatically in sequence."
    )

    col_fp, col_pat, col_loc = st.columns(3)
    with col_fp:
        st.markdown("**Site Footprint**")
        footprint_text = st.text_area(
            "footprint", height=160, label_visibility="collapsed", key="qb_footprint",
            placeholder="Pilot\nWrestler\nStartups\nNon-profit\nChurch",
        )
    with col_pat:
        st.markdown("**@ Patterns**")
        patterns_text = st.text_area(
            "patterns", height=160, label_visibility="collapsed", key="qb_patterns",
            placeholder="@comcast.net\n@gmail.com\n@yahoo.com\n@outlook.com",
        )
    with col_loc:
        st.markdown("**Location / Role**")
        locations_text = st.text_area(
            "locations", height=160, label_visibility="collapsed", key="qb_locations",
            placeholder="Governors\nScientist\nhuman resources\nChicago\nTexas",
        )

    footprints = [l.strip() for l in footprint_text.split("\n") if l.strip()]
    patterns = [l.strip() for l in patterns_text.split("\n") if l.strip()]
    locations = [l.strip() for l in locations_text.split("\n") if l.strip()]
    total_queries = len(footprints) * len(patterns) * len(locations)

    # ── Query count + inline controls ───────────────────────────────────────
    col_count, col_ctrl = st.columns([2, 1])
    with col_count:
        if total_queries > 0:
            st.success(
                f"**{len(footprints)} × {len(patterns)} × {len(locations)} = {total_queries:,} queries** ready"
            )
        else:
            st.info("Add at least one entry in each column to generate queries.")
    with col_ctrl:
        delay_queries = st.number_input(
            "Delay between queries (s)", min_value=0, max_value=99, value=0, step=1,
            key="qb_delay_queries",
        )
        remove_dupes = st.checkbox("Remove duplicates", value=True, key="qb_remove_dupes")

    # ── Action buttons ────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        start_btn = st.button(
            "▶ Start", type="primary", use_container_width=True,
            disabled=st.session_state.is_running or total_queries == 0,
        )
    with c2:
        stop_btn = st.button("■ Stop", use_container_width=True, disabled=not st.session_state.is_running)
    with c3:
        clear_btn = st.button("Clear", use_container_width=True)
    with c4:
        check_srv_clicked = st.button("Check server", use_container_width=True)

    if clear_btn:
        st.session_state.activity_log = []
        st.session_state.extracted_leads = []
        st.session_state.current_screenshot = None
        st.session_state.query_current = ""
        st.session_state.query_progress_idx = 0
        st.session_state.query_total = 0
        st.session_state.emails_collected = 0
        st.rerun()

    if stop_btn:
        st.session_state.is_running = False
        # Flush every pending message from the queue NOW so the counter freezes
        # immediately — stale lead_count / leads updates are discarded.
        _stop_q = st.session_state.get("ws_message_queue")
        if _stop_q:
            try:
                while True:
                    _stop_q.get_nowait()
            except Empty:
                pass
        # 1. Try WebSocket stop command (fast path)
        ws = _ws_client_ref[0] if _ws_client_ref else None
        if ws:
            try:
                ws.send(json.dumps({"command": "stop"}))
                st.session_state.activity_log.append("Stop sent to automation service.")
            except Exception as e:
                st.session_state.activity_log.append(f"WS stop failed ({str(e)[:40]}), trying HTTP…")
                ws = None
        # 2. Always also hit the HTTP /stop endpoint — this cancels the asyncio
        #    Task directly on the server, guaranteeing the background run halts
        #    even if the WebSocket connection was already closed.
        try:
            import httpx
            httpx.post(f"{AUTOMATION_SERVER_URL.rstrip('/')}/stop", timeout=3)
        except Exception:
            pass  # Server not reachable — WS stop is sufficient if it worked
        if not ws:
            st.session_state.activity_log.append("Stop signal sent via HTTP.")
        st.rerun()

    if start_btn:
        queries = generate_queries(footprints, patterns, locations)
        if not queries:
            st.warning("Need at least one entry in each column (Footprint, @Pattern, Location).")
        else:
            # Flush any leftover messages from the previous run before resetting
            # state, so stale lead_count updates can't bleed into the new run.
            _old_q = st.session_state.get("ws_message_queue")
            if _old_q:
                try:
                    while True:
                        _old_q.get_nowait()
                except Empty:
                    pass

            st.session_state.is_running = True
            st.session_state.extracted_leads = []
            st.session_state.activity_log = []
            st.session_state.current_screenshot = None
            st.session_state.saved_files = []
            st.session_state.query_current = ""
            st.session_state.query_progress_idx = 0
            st.session_state.query_total = len(queries)
            st.session_state.emails_collected = 0

            msg_queue = Queue()
            st.session_state.ws_message_queue = msg_queue
            _target = st.session_state.get("target_lead_count", 0)
            _engine = st.session_state.get("search_engine", "duckduckgo")
            _headless = bool(st.session_state.settings.get("headless", False))
            _delay_p = float(delay_queries) if delay_queries > 0 else float(delay_pages)
            thread = threading.Thread(
                target=run_websocket_client,
                args=(
                    queries,
                    int(max_pages),
                    _delay_p,
                    float(delay_actions),
                    msg_queue,
                    int(_target),
                    _engine,
                    _headless,
                    False,
                    str(st.session_state.get("live_email_domain_allowlist", "") or ""),
                    str(st.session_state.get("live_search_site_domains", "") or ""),
                ),
                daemon=True,
            )
            thread.start()
            st.session_state.live_queries_for_sessions = list(queries[:10])
            st.rerun()

    if check_srv_clicked:
        try:
            import httpx
            with st.spinner("Checking server…"):
                resp = httpx.get(f"{AUTOMATION_SERVER_URL.rstrip('/')}/", timeout=2)
            if resp.status_code == 200:
                st.session_state.websocket_connected = True
                st.session_state.server_checked = True
                st.success("Server is running.")
            else:
                st.error("Server returned an error.")
        except Exception as e:
            st.session_state.websocket_connected = False
            st.error(f"Server not reachable: {str(e)[:50]}")

    # ── Live Status Dashboard ─────────────────────────────────────────────────
    # Shown here only when NOT running (final / "Done" state after completion).
    # During a run this block lives inside _live_automation_fragment() so it
    # updates every 1.15 s without a full-page rerun.
    is_running = st.session_state.is_running
    q_current = st.session_state.get("query_current", "")
    q_idx = st.session_state.get("query_progress_idx", 0)
    q_total = st.session_state.get("query_total", total_queries or 1)
    emails_col = st.session_state.get("emails_collected", 0)

    if not is_running and q_current:
        st.divider()
        dash_c1, dash_c2 = st.columns(2)
        with dash_c1:
            st.markdown(
                f'<div class="extraction-status-bar">'
                f'<strong>Last run:</strong> <code>{_escape_html(q_current)}</code></div>',
                unsafe_allow_html=True,
            )
            st.metric("Collected emails", emails_col)
        with dash_c2:
            st.metric("Progress", f"{q_idx} / {q_total} queries")
            if q_total > 0:
                st.progress(min(1.0, q_idx / q_total))
            if st.session_state.extracted_leads:
                _dl_df = leads_to_dataframe(st.session_state.extracted_leads)
                download_button_with_fallback(
                    "⬇️ Download collected",
                    data=_dl_df.to_csv(index=False).encode(),
                    file_name="leads_in_progress.csv",
                    mime="text/csv",
                    key="dl_mid_run_page",
                )

    # ── Connection status bar ────────────────────────────────────────────────
    status_text = "🔄 Running..." if is_running else "Ready"
    status_text += " | ✅ Connected" if st.session_state.websocket_connected else " | ⚠️ Not Connected"
    st.markdown(f'<div class="status-bar">{status_text}</div>', unsafe_allow_html=True)

    # ── Platform launch helpers ──────────────────────────────────────────────
    proj = Path(__file__).resolve().parent.parent
    if platform.system() == "Darwin":
        if st.button("Launch in Terminal (visible browser)", key="launch_terminal"):
            try:
                cmd = f"cd {proj} && python3 launch_app_simple.py"
                subprocess.run(["osascript", "-e", f'tell application "Terminal" to do script "{cmd}"'], check=False, timeout=5)
                st.success("Terminal opened.")
            except Exception as e:
                st.error(f"Could not open Terminal: {e}")
    elif platform.system() == "Windows":
        if st.button("Launch in CMD (visible browser)", key="launch_cmd"):
            try:
                subprocess.Popen(["cmd", "/k", f'cd /d "{proj}" && python launch_app_windows.py'], cwd=str(proj), creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0)
                st.success("Command Prompt opened.")
            except Exception as e:
                st.error(f"Could not open Command Prompt: {e}")

    # ── Live Browser View + Activity Log ────────────────────────────────────
    st.divider()
    if is_running:
        _live_automation_fragment()
    else:
        _render_live_panel_content(extracting=False)

    if st.session_state.pop("_terminal_rerun", False):
        st.rerun()

    # ── Saved sessions for same query set ───────────────────────────────────
    _render_live_query_sessions_panel()

    # ── Results Table ────────────────────────────────────────────────────────
    if st.session_state.extracted_leads:
        st.divider()
        leads_list = st.session_state.extracted_leads
        em = sum(1 for l in leads_list if l.get("email"))
        ph = sum(1 for l in leads_list if l.get("phone"))
        nm = sum(1 for l in leads_list if l.get("contact_name"))

        st.markdown(f"### 📊 Extracted Leads ({len(leads_list):,})")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total", len(leads_list))
        m2.metric("📧 Emails", em)
        m3.metric("📞 Phones", ph)
        m4.metric("👤 Names", nm)

        df = pd.DataFrame(leads_list)
        if not df.empty:
            preset = st.selectbox("Filter columns", list(COLUMN_PRESETS.keys()), key="live_preset")
            display_cols = [c for c in COLUMN_PRESETS[preset] if c in df.columns] or ["contact_name", "phone", "email"]
            st.dataframe(df[display_cols], use_container_width=True, hide_index=True,
                column_config={
                    "contact_name": st.column_config.TextColumn("👤 Name", width="medium"),
                    "phone": st.column_config.TextColumn("📞 Phone", width="medium"),
                    "email": st.column_config.TextColumn("📧 Email", width="large"),
                    "business_name": st.column_config.TextColumn("Business", width="medium"),
                })
            st.divider()
            export_cols = COLUMN_PRESETS[preset]
            e1, e2, e3, e4 = st.columns(4)
            with e1:
                if st.button("📄 CSV", use_container_width=True, key="exp_csv"):
                    path = export_to_csv(leads_list, columns=export_cols)
                    st.toast(f"Saved → {Path(str(path)).name}", icon="📄")
            with e2:
                if st.button("📊 Excel", use_container_width=True, key="exp_xlsx"):
                    path = export_to_excel(leads_list, columns=export_cols)
                    st.toast(f"Saved → {Path(str(path)).name}", icon="📊")
            with e3:
                if st.button("📕 PDF", use_container_width=True, key="exp_pdf"):
                    path = export_to_pdf(leads_list, query='Batch Results')
                    st.toast(f"Saved → {Path(str(path)).name}", icon="📕")
            with e4:
                download_button_with_fallback(
                    "⬇️ Download",
                    data=leads_to_dataframe(leads_list, columns=export_cols).to_csv(index=False).encode(),
                    file_name="leads.csv", mime="text/csv", key="exp_dl_csv",
                )


# ─── Saved Leads Page ───────────────────────────────────────────────────────
def render_saved_leads_page():
    st.markdown('<p class="app-title">Leads</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="app-subtitle">Validate, merge, and export every lead NEXUS has collected — plus any external lists you upload.</p>',
        unsafe_allow_html=True,
    )

    tab_extracted, tab_upload = st.tabs(["📥 Extracted Leads", "📤 Upload & Validate External Leads"])

    # ════════════════════════════════════════════════════════════════════════════
    # TAB A — Extracted Leads (existing functionality, unchanged)
    # ════════════════════════════════════════════════════════════════════════════
    with tab_extracted:
        from app.database.db import get_recent_searches, get_leads_by_search
        searches = get_recent_searches(limit=50)

        if not searches:
            st.info("No searches found. Run some queries first!")
        else:
            if "saved_leads_selected_ids" not in st.session_state:
                st.session_state.saved_leads_selected_ids = set()
            if "saved_leads_column_preset" not in st.session_state:
                st.session_state.saved_leads_column_preset = "Emails + Names + Phones"

            st.markdown("### 🔗 Merge & Export Multiple Sessions")
            st.caption(
                "Select sessions to merge, filter columns, and download. "
                "One **Start** = one saved session."
            )

            sessions_by_date: dict = {}
            for session in searches:
                date_str = str(session.get("created_at", ""))[:10] if session.get("created_at") else "Unknown"
                sessions_by_date.setdefault(date_str, []).append(session)

            for date_str in sorted(sessions_by_date.keys(), reverse=True):
                with st.expander(f"📅 {date_str} ({len(sessions_by_date[date_str])} sessions)", expanded=False):
                    for session in sessions_by_date[date_str]:
                        sid = session["id"]
                        q_label = str(session.get("query", ""))[:50] + ("..." if len(str(session.get("query", ""))) > 50 else "")
                        n = session.get("num_leads", 0)
                        is_sel = st.checkbox(
                            f"Session #{sid}: {q_label} ({n} leads)",
                            value=sid in st.session_state.saved_leads_selected_ids,
                            key=f"sel_{sid}",
                        )
                        if is_sel:
                            st.session_state.saved_leads_selected_ids.add(sid)
                        else:
                            st.session_state.saved_leads_selected_ids.discard(sid)

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("✅ Select All", key="saved_select_all"):
                    st.session_state.saved_leads_selected_ids = {s["id"] for s in searches}
                    st.rerun()
            with c2:
                if st.button("❌ Clear selection", key="saved_clear"):
                    st.session_state.saved_leads_selected_ids = set()
                    st.rerun()
            with c3:
                if st.button("📅 Today Only", key="saved_today"):
                    today = datetime.now().strftime("%Y-%m-%d")
                    st.session_state.saved_leads_selected_ids = {
                        s["id"] for s in searches if str(s.get("created_at", "")).startswith(today)
                    }
                    st.rerun()

            if st.session_state.saved_leads_selected_ids:
                all_merged = []
                for sid in st.session_state.saved_leads_selected_ids:
                    for lead in get_leads_by_search(sid):
                        lead_copy = dict(lead)
                        lead_copy["_session_id"] = sid
                        all_merged.append(lead_copy)

                st.text_area(
                    "Optional: email domain filter before download (one per line)",
                    height=68, key="saved_export_email_domains",
                    help="Examples: `gmail.com`, `*.gov`, `@company.com`. Leave empty to skip.",
                )
                export_mode = st.radio(
                    "Export mode",
                    ["Full (all leads, no dedup)", "Unique (dedup only, any email with @)", "Unique valid (dedup + strict validation)"],
                    key="saved_export_mode",
                )
                use_full = "Full" in export_mode
                use_validation = "valid" in export_mode.lower()
                _saved_dom = (st.session_state.get("saved_export_email_domains") or "").strip()

                export_leads, ex_stats = filter_merged_leads_for_export(
                    all_merged, use_full=use_full, use_validation=use_validation,
                    email_domain_allowlist=_saved_dom if _saved_dom else None,
                )

                if use_full:
                    _doms = ex_stats.get("domain_filtered_count", 0)
                    _fmsg = f"📋 {len(export_leads)} leads (full, no dedup)"
                    if _doms:
                        _fmsg += f" — {_doms} row(s) removed by domain filter"
                    st.info(_fmsg)
                else:
                    label = "unique valid" if use_validation else "unique"
                    st.success(
                        f"✅ {len(export_leads)} {label} leads "
                        f"(from {ex_stats['merged_raw']} rows → {ex_stats['rows_after_split']} after split)"
                    )
                    with st.expander("📊 Breakdown"):
                        st.markdown(f"- **No email:** {ex_stats['no_email_count']}")
                        if use_validation:
                            st.markdown(f"- **Invalid format:** {ex_stats['invalid_count']}")
                        st.markdown(f"- **Duplicate:** {ex_stats['dup_count']}")
                        if ex_stats.get("domain_filtered_count", 0):
                            st.markdown(f"- **Domain filter:** {ex_stats['domain_filtered_count']}")

                preset = st.selectbox("Filter columns", list(COLUMN_PRESETS.keys()), key="saved_preset")
                st.session_state.saved_leads_column_preset = preset
                cols = [c for c in COLUMN_PRESETS[preset] if c in (export_leads[0].keys() if export_leads else [])] or list(COLUMN_PRESETS[preset])
                df_merged = pd.DataFrame(export_leads)
                show_cols = [c for c in cols if c in df_merged.columns]
                if not df_merged.empty:
                    st.dataframe(df_merged[show_cols] if show_cols else df_merged, use_container_width=True, hide_index=True)

                st.markdown("**Download merged:**")
                e1, e2, e3 = st.columns(3)
                with e1:
                    download_button_with_fallback(
                        "⬇️ CSV", key="dl_merged_csv", mime="text/csv",
                        data=leads_to_dataframe(export_leads, columns=COLUMN_PRESETS[preset]).to_csv(index=False).encode(),
                        file_name="merged_leads.csv",
                    )
                with e2:
                    if st.button("📄 Save CSV", key="save_merged_csv"):
                        p = export_to_csv(export_leads, f'merged_{len(export_leads)}_leads.csv', columns=COLUMN_PRESETS[preset])
                        st.toast(f"Saved → {Path(str(p)).name}", icon="📄")
                with e3:
                    if st.button("📊 Save Excel", key="save_merged_xlsx"):
                        p = export_to_excel(export_leads, f'merged_{len(export_leads)}_leads.xlsx', columns=COLUMN_PRESETS[preset])
                        st.toast(f"Saved → {Path(str(p)).name}", icon="📊")

                # ── Validate merged leads ─────────────────────────────────────
                st.divider()
                st.markdown("**Validate & deduplicate merged leads:**")
                st.caption("DNS MX check per domain + dedup. Finds invalid emails and removes duplicates from DB.")

                _val_placeholder = st.empty()  # Progress bar renders here
                if st.button("✅ Validate & Deduplicate merged leads", key="ext_validate_btn"):
                    if export_leads:
                        with _val_placeholder.container():
                            st.session_state.extracted_validation_results = _run_validation_with_progress(export_leads)
                        st.rerun()
                    else:
                        st.warning("No leads to validate. Select at least one session above.")

                evr = st.session_state.extracted_validation_results
                if evr:
                    st.divider()
                    _render_validation_results(evr, dl_key_prefix="ext_saved")

                    # Allow removal of invalid + duplicate rows from the leads DB
                    ext_removable = [i for i in (evr["invalid_ids"] + evr["dup_ids"]) if i is not None]
                    ext_ra, ext_rb = st.columns(2)
                    with ext_ra:
                        if ext_removable and st.button(
                            f"🧹 Remove {len(ext_removable):,} dupes & invalid from DB",
                            key="ext_remove_invalid", type="primary",
                        ):
                            with st.spinner(f"Removing {len(ext_removable):,} rows…"):
                                deleted = delete_leads_by_ids(ext_removable)
                            st.success(f"{deleted:,} rows removed from extracted leads DB.")
                            st.session_state.extracted_validation_results = None
                            st.rerun()
                    with ext_rb:
                        if st.button("✖ Clear results", key="ext_clear_vr"):
                            st.session_state.extracted_validation_results = None
                            st.rerun()

            st.divider()
            st.markdown("### 🔍 Individual Sessions")
            single_preset = st.selectbox("Export columns (per session)", list(COLUMN_PRESETS.keys()), key="single_preset")
            single_cols = COLUMN_PRESETS[single_preset]
            for search in searches:
                search_id = search["id"]
                query = search["query"]
                num_leads = search["num_leads"]
                created_at = search["created_at"]
                with st.expander(f"Session #{search_id}: {query[:60]}{'...' if len(query) > 60 else ''} ({num_leads} leads) — {created_at}"):
                    leads = get_leads_by_search(search_id)
                    if leads:
                        df = pd.DataFrame(leads)
                        avail = [c for c in ["contact_name", "phone", "email"] if c in df.columns]
                        st.dataframe(df[avail], use_container_width=True, hide_index=True,
                            column_config={
                                "contact_name": st.column_config.TextColumn("👤 Name", width="medium"),
                                "phone": st.column_config.TextColumn("📞 Phone", width="medium"),
                                "email": st.column_config.TextColumn("📧 Email", width="large"),
                            })
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            download_button_with_fallback("⬇️ CSV", key=f"dl_{search_id}", mime="text/csv",
                                data=leads_to_dataframe(leads, columns=single_cols).to_csv(index=False).encode(),
                                file_name=f"session_{search_id}.csv")
                        with col2:
                            if st.button("📄 Save CSV", key=f"csv_{search_id}"):
                                p = export_to_csv(leads, f'session_{search_id}', columns=single_cols)
                                st.toast(f"Saved → {Path(str(p)).name}", icon="📄")
                        with col3:
                            if st.button("📊 Save Excel", key=f"xlsx_{search_id}"):
                                p = export_to_excel(leads, f'session_{search_id}', columns=single_cols)
                                st.toast(f"Saved → {Path(str(p)).name}", icon="📊")
                    else:
                        st.caption("No leads found for this session.")

    # ════════════════════════════════════════════════════════════════════════════
    # TAB B — Upload & Validate External Leads
    # ════════════════════════════════════════════════════════════════════════════
    with tab_upload:
        st.markdown("### 📤 Upload Personal Leads")
        st.caption("Import your own lead list. Supports `.txt` (one email per line), `.csv`, `.xlsx`, `.json`.")

        # ── Upload widget ────────────────────────────────────────────────────
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["txt", "csv", "xlsx", "json", "xls", "tsv"],
            help="TXT: one email per line · CSV/XLSX: auto-detects Email column · JSON: array or {leads:[...]}",
        )

        if uploaded_file:
            file_bytes = uploaded_file.read()
            file_name = uploaded_file.name
            st.info(f"📄 {file_name} — {len(file_bytes):,} bytes")

            if st.checkbox("Preview file content", value=False, key="ul_preview_toggle"):
                try:
                    if file_name.lower().endswith((".txt", ".tsv", ".csv", ".json")):
                        preview_text = file_bytes.decode("utf-8", errors="ignore")
                        st.code("\n".join(preview_text.splitlines()[:15]), language="text")
                    else:
                        st.caption("Binary file — preview not available")
                except Exception as ex:
                    st.caption(f"Preview error: {ex}")

            if st.button("⬆️ Import leads", type="primary", key="ul_import_btn"):
                with st.spinner("Parsing and importing…"):
                    try:
                        leads_parsed, parse_msgs = upload_leads_from_file(file_bytes, file_name)
                        if not leads_parsed:
                            st.warning("No leads found in file. Check the format and try again.")
                            for m in parse_msgs:
                                st.caption(m)
                        else:
                            saved_count, save_msgs = save_external_leads(
                                leads_parsed, source="manual_upload", file_name=file_name
                            )
                            dupes = sum(1 for m in save_msgs if "already exists" in m)
                            st.success(
                                f"✅ {saved_count} leads imported from {file_name}"
                                + (f" · {dupes} skipped (duplicates)" if dupes else "")
                            )
                            for m in parse_msgs:
                                if m:
                                    st.caption(m)
                            st.session_state.ext_leads_last_imported = saved_count
                            st.rerun()
                    except Exception as ex:
                        st.error(f"Import failed: {ex}")

        st.divider()

        # ── Totals + Domain Breakdown ────────────────────────────────────────
        try:
            domain_stats = get_domain_statistics()
        except Exception:
            domain_stats = {}

        total_ext = sum(domain_stats.values()) if domain_stats else 0

        if total_ext:
            st.metric("Total external leads stored", f"{total_ext:,}")
            st.markdown("**Domain breakdown** (top 30):")
            df_domains = pd.DataFrame(
                [{"Domain": d, "Count": c} for d, c in list(domain_stats.items())[:30]]
            )
            st.dataframe(
                df_domains, use_container_width=True, hide_index=True,
                column_config={
                    "Domain": st.column_config.TextColumn("📧 Domain", width="large"),
                    "Count": st.column_config.NumberColumn("Leads", width="small"),
                },
            )
        else:
            st.info("No external leads imported yet. Upload a file above.")

        if not total_ext:
            return

        st.divider()
        st.markdown("### 🔍 Filter, Browse & Validate")

        # ── Controls row ─────────────────────────────────────────────────────
        fc1, fc2, fc3 = st.columns([3, 2, 2])
        with fc1:
            domain_filter_input = st.text_input(
                "Filter by domain",
                key="ul_domain_filter",
                placeholder="e.g. gmail.com — leave empty for all",
            )
        with fc2:
            page_size = st.selectbox(
                "Leads per page", [50, 100, 200, 500], index=1, key="ul_page_size"
            )
        with fc3:
            # Total matching count for pagination
            try:
                _all = get_external_leads(limit=100_000, domain_filter=domain_filter_input.strip() or None)
                match_total = len(_all)
            except Exception:
                match_total = 0
            max_page = max(1, (match_total + page_size - 1) // page_size)
            page_num = st.number_input(
                f"Page (1 – {max_page})",
                min_value=1, max_value=max_page, value=1, step=1, key="ul_page_num",
            )

        offset = (page_num - 1) * page_size
        try:
            ext_leads = get_external_leads(
                limit=page_size, offset=offset,
                domain_filter=domain_filter_input.strip() or None,
            )
        except Exception:
            ext_leads = []

        if match_total:
            first = offset + 1
            last = min(offset + page_size, match_total)
            st.caption(
                f"Showing leads **{first:,} – {last:,}** of **{match_total:,}**"
                + (f" matching `{domain_filter_input}`" if domain_filter_input else "")
            )

        # ── Action buttons ────────────────────────────────────────────────────
        btn_c1, btn_c2, btn_c3 = st.columns(3)
        with btn_c1:
            validate_all_clicked = st.button(
                "✅ Validate & Deduplicate", key="ul_validate_btn",
                help="DNS MX check per domain + dedup. Progress bar shows live status.",
            )
        with btn_c2:
            dup_check_clicked = st.button("🔗 Check duplicates vs extracted", key="ul_dup_check")
        with btn_c3:
            clear_clicked = st.button("🗑️ Clear all external leads", key="ul_clear_all", type="secondary")

        # ── Run validation with progress bar ─────────────────────────────────
        if validate_all_clicked:
            check_leads = _all if match_total else []
            if check_leads:
                st.session_state.ext_validation_results = _run_validation_with_progress(check_leads)
                st.rerun()

        # ── Show persistent validation results ───────────────────────────────
        vr = st.session_state.ext_validation_results
        if vr:
            st.divider()
            _render_validation_results(vr, dl_key_prefix="ul_ext")

            removable_ids = [i for i in (vr["invalid_ids"] + vr["dup_ids"]) if i is not None]
            ra, rb = st.columns(2)
            with ra:
                if removable_ids and st.button(
                    f"🧹 Remove {len(removable_ids):,} dupes & invalid from DB",
                    key="ul_remove_invalid", type="primary",
                ):
                    with st.spinner(f"Removing {len(removable_ids):,} rows…"):
                        deleted, _ = delete_external_leads(removable_ids)
                    st.success(f"{deleted:,} rows removed. {vr['valid_count']:,} unique valid leads remain.")
                    st.session_state.ext_validation_results = None
                    st.rerun()
            with rb:
                if st.button("✖ Clear results", key="ul_clear_vr"):
                    st.session_state.ext_validation_results = None
                    st.rerun()

        # ── Duplicate check ───────────────────────────────────────────────────
        if dup_check_clicked:
            check_leads = _all[:5000] if match_total else []
            dupes = []
            with st.spinner("Checking duplicates…"):
                for lead in check_leads:
                    email = lead.get("email", "")
                    if email:
                        match = compare_with_extracted_leads(email)
                        if match and match.get("found"):
                            dupes.append(f"{email} → found in session #{match.get('lead_id')}")
            if dupes:
                st.warning(f"Found {len(dupes)} duplicate(s) in your extracted leads DB:")
                with st.expander("Show duplicates"):
                    st.code("\n".join(dupes[:200]))
            else:
                st.success("No duplicates found — these leads are unique vs your extracted leads.")

        # ── Clear all ────────────────────────────────────────────────────────
        if clear_clicked:
            try:
                all_ids = [l["id"] for l in _all if l.get("id")]
                if all_ids:
                    with st.spinner(f"Clearing {len(all_ids):,} leads…"):
                        deleted, _ = delete_external_leads(all_ids)
                    st.success(f"Deleted {deleted} external lead(s).")
                    st.session_state.ext_validation_results = None
                    st.rerun()
            except Exception as ex:
                st.error(f"Delete failed: {ex}")

        st.divider()

        # ── Lead table (current page) ─────────────────────────────────────────
        if ext_leads:
            df_ext = pd.DataFrame(ext_leads)
            show_cols = [c for c in ["email", "domain", "contact_name", "business_name", "phone", "source"] if c in df_ext.columns]
            st.dataframe(
                df_ext[show_cols] if show_cols else df_ext,
                use_container_width=True, hide_index=True,
                column_config={
                    "email": st.column_config.TextColumn("📧 Email", width="large"),
                    "domain": st.column_config.TextColumn("Domain", width="medium"),
                    "contact_name": st.column_config.TextColumn("Name", width="medium"),
                    "business_name": st.column_config.TextColumn("Business", width="medium"),
                },
            )

        # ── Export (entire filtered set) ───────────────────────────────────────
        if match_total:
            dl_data = (pd.DataFrame(_all).to_csv(index=False) if _all else "").encode()
            download_button_with_fallback(
                f"⬇️ Download all filtered ({match_total:,} leads)", key="ul_dl_csv",
                data=dl_data, mime="text/csv",
                file_name=f"external_leads{'_' + domain_filter_input if domain_filter_input else ''}.csv",
            )
        else:
            st.info("No external leads match your filter.")


# ─── Settings Page ────────────────────────────────────────────────────────────
def render_settings_page():
    """Render settings page"""
    st.markdown('<p class="app-title">Settings</p>', unsafe_allow_html=True)
    st.markdown('<p class="app-subtitle">Search engine, pacing, and runtime preferences.</p>', unsafe_allow_html=True)

    st.markdown("### Search provider")
    search_engine = st.selectbox(
        "Default provider for extraction",
        _SEARCH_ENGINE_OPTIONS,
        format_func=_search_provider_label,
        index=0 if st.session_state.get("search_engine", "duckduckgo") == "duckduckgo" else 1,
        key="settings_search_engine",
        help=_search_provider_help(),
    )
    st.session_state.search_engine = search_engine
    if search_engine == "google":
        st.info("Alternative provider may show verification prompts on repeated runs.")
    else:
        st.success("Standard provider selected.")

    st.divider()

    # ── Automation Settings ─────────────────────────────────────────────────
    st.markdown("### ⚙️ Automation")
    settings = st.session_state.settings
    col1, col2 = st.columns(2)
    with col1:
        max_pages = st.number_input("Max Pages per Query", min_value=1, max_value=500, value=int(settings.get("max_pages", 10)), step=1, key="set_max_pages")
        delay_pages = st.number_input("Delay Between Pages (s)", min_value=0.0, max_value=10.0, value=float(settings.get("delay_pages", 2.0)), step=0.5, key="set_delay_pages")
    with col2:
        delay_actions = st.number_input("Action Delay (s)", min_value=0.0, max_value=5.0, value=float(settings.get("delay_actions", 1.0)), step=0.1, key="set_delay_actions")
        headless = st.checkbox(
            "🖥️ Run headless (no browser window)",
            value=bool(settings.get("headless", False)),
            key="set_headless",
            help="Use when the automation window doesn't pop up. Activity still shows in logs; PDFs and emails are extracted normally."
        )

    # Save button
    if st.button("💾 Save Settings", type="primary", key="save_settings_btn"):
        new_settings = dict(settings)
        new_settings["search_engine"] = search_engine
        new_settings["max_pages"] = max_pages
        new_settings["delay_pages"] = delay_pages
        new_settings["delay_actions"] = delay_actions
        new_settings["headless"] = headless
        save_settings(new_settings)
        st.session_state.settings = load_settings()
        st.toast("Settings saved", icon="✅")
        st.rerun()

    st.divider()
    st.caption("Server status and stats are available in the sidebar.")


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    # ── License gate ──────────────────────────────────────────────────────────
    # show_activation_dialog() renders the full activation UI and returns True
    # only after the user successfully enters and saves a valid key.
    # st.stop() prevents any app content from rendering below.
    is_valid, user = check_license()

    if not is_valid:
        show_activation_dialog()
        st.stop()
        return  # unreachable but keeps linters happy
    
    # Render sidebar (always visible)
    render_sidebar()

    # Render navigation bar at page top
    render_bottom_navigation()
    st.markdown("---")

    # Render current page based on navigation
    current_page = st.session_state.current_page

    if current_page == "🔍 Live Extractor":
        render_extractor_page()
    elif current_page == "📋 Saved Leads":
        render_saved_leads_page()
    elif current_page == "⚙️ Settings":
        render_settings_page()


if __name__ == "__main__":
    main()
