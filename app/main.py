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

from app.config import APP_NAME, APP_VERSION, LICENSE_KEY, LICENSE_SECRET, EXPORT_DIR, WEBSOCKET_URL, AUTOMATION_SERVER_URL, PROJECT_ROOT
from app.license.validator import validate_license
from app.license.activation_ui import check_license, show_activation_dialog, show_license_status
from app.database.db import (
    get_all_leads,
    get_lead_stats,
    get_searches_for_queries,
    get_leads_by_search,
    maybe_prune_stale_searches,
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
from app.email.email_ui import render_email_sender_page


# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Delete lead/search data older than LEADS_RETENTION_DAYS (default 30); runs at most once / 24h
try:
    maybe_prune_stale_searches(interval_hours=24.0)
except Exception:
    pass

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container { padding-top: 1rem; }

    .app-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #e94560;
        margin-bottom: 0;
    }
    .app-subtitle {
        color: #8888a0;
        font-size: 0.85rem;
        margin-top: -5px;
    }

    .activity-log {
        background: #0a0a14;
        border: 2px solid #333350;
        border-radius: 6px;
        padding: 10px 14px;
        font-family: 'Menlo', 'Consolas', monospace;
        font-size: 0.75rem;
        color: #a0a0c0;
        max-height: 400px;
        overflow-y: auto;
        line-height: 1.4;
        white-space: pre-wrap;
    }

    .status-bar {
        background: linear-gradient(135deg, #1e1e2e, #2a2a3e);
        border: 1px solid #333350;
        border-radius: 4px;
        padding: 6px 12px;
        font-family: monospace;
        font-size: 0.85rem;
        color: #e0e0e0;
    }

    .browser-view {
        border: 2px solid #333350;
        border-radius: 8px;
        background: #000;
        padding: 8px;
    }

    .top-nav {
        position: sticky;
        top: 0;
        z-index: 999;
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px;
        border-radius: 10px;
        background: linear-gradient(90deg, #f3f7ff, #e8efff);
        border: 1px solid #d1ddff;
        margin-bottom: 10px;
    }

    .top-nav button {
        background: #ffffff;
        border: 1px solid #b4c6eb;
        border-radius: 6px;
        color: #2f4f84;
        font-weight: 600;
        padding: 8px 12px;
        min-width: 80px;
    }

    .top-nav button:focus, .top-nav button:hover {
        background: #e4eafc;
        border-color: #7490d7;
    }

    .top-nav button.active {
        background: #2f65d4;
        border-color: #1f3f96;
        color: white;
    }
    
    .bottom-nav {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(135deg, #1e1e2e, #2a2a3e);
        border-top: 2px solid #333350;
        padding: 12px 20px;
        display: flex;
        justify-content: center;
        gap: 20px;
        z-index: 999;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.3);
    }
    
    .nav-button {
        padding: 10px 20px;
        background: #2a2a3e;
        border: 1px solid #444460;
        border-radius: 6px;
        color: #a0a0c0;
        cursor: pointer;
        font-size: 0.9rem;
        transition: all 0.2s;
    }
    
    .nav-button:hover {
        background: #333350;
        border-color: #555570;
        color: #e0e0e0;
    }
    
    .nav-button.active {
        background: #e94560;
        border-color: #e94560;
        color: white;
        font-weight: 600;
    }
    
    .main-content {
        padding-bottom: 80px;
    }

    /* Live extraction — compact status (no full-page flash) */
    .extraction-status-bar {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 14px;
        background: linear-gradient(90deg, #eef2ff 0%, #f8fafc 100%);
        border: 1px solid #c7d2fe;
        border-radius: 8px;
        margin-bottom: 10px;
        font-size: 0.9rem;
        color: #1e293b;
    }
    .live-dot {
        width: 9px;
        height: 9px;
        background: #2563eb;
        border-radius: 50%;
        flex-shrink: 0;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.25);
        animation: live-dot-pulse 1.4s ease-in-out infinite;
    }
    @keyframes live-dot-pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.45; transform: scale(0.92); }
    }
    .extraction-meta {
        color: #64748b;
        font-size: 0.82rem;
    }
    .extraction-detail {
        font-size: 0.78rem;
        color: #475569;
        margin: -4px 0 10px 0;
        padding-left: 19px;
        max-width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
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


# ─── WebSocket Client (URL from app.config, supports local + cloud) ───────────
# CRITICAL: WebSocket callbacks run in a background thread. They must NOT touch
# st.session_state directly - that causes "missing ScriptRunContext" and connection drops.
# Instead, put updates in a queue; main thread drains it and updates session state.


def websocket_client(queries: List[str], max_pages: int, delay_pages: float, delay_actions: float,
                    msg_queue: Queue, target_leads: int, search_engine: str, headless: bool,
                    batch_reload: bool = False):
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


def run_websocket_client(queries: List[str], max_pages: int, delay_pages: float, delay_actions: float,
                        msg_queue: Queue, target_leads: int, search_engine: str, headless: bool,
                        batch_reload: bool = False):
    """Run WebSocket client in background thread."""
    websocket_client(queries, max_pages, delay_pages, delay_actions, msg_queue, target_leads, search_engine, headless, batch_reload)


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
            st.session_state.extracted_leads.extend(data)
            st.session_state.current_lead_count = len(st.session_state.extracted_leads)
            st.session_state.needs_refresh = True
            st.session_state.last_update = time.time()
            changed = True
        elif msg_type == "lead_count":
            st.session_state.current_lead_count, st.session_state.target_lead_count = data
            st.session_state.needs_refresh = True
            st.session_state.last_update = time.time()
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

    export_leads, ex_stats = filter_merged_leads_for_export(
        merged, use_full=use_full, use_validation=use_validation
    )

    if use_full:
        st.info(f"📋 {len(export_leads)} leads (full, no dedup)")
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
        st.download_button(
            "⬇️ Download CSV",
            data=csv_bytes,
            file_name="merged_sessions.csv",
            mime="text/csv",
            key="live_sess_dl_csv",
        )
    with e2:
        if st.button("📄 Save CSV to exports folder", key="live_sess_save_csv"):
            path = export_to_csv(
                export_leads,
                f"merged_live_{len(export_leads)}_leads.csv",
                columns=export_cols,
            )
            st.success(f"Saved: {path}")
    with e3:
        if st.button("📊 Save Excel to exports folder", key="live_sess_save_xlsx"):
            path = export_to_excel(
                export_leads,
                f"merged_live_{len(export_leads)}_leads.xlsx",
                columns=export_cols,
            )
            st.success(f"Saved: {path}")


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
    """Render sidebar with app info and stats"""
    with st.sidebar:
        st.markdown(f"## 🎯 {APP_NAME}")
        st.caption(f"v{APP_VERSION}")
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
NAV_OPTIONS = ["🔍 Live Extractor", "📋 Saved Leads", "📧 Email Sender", "⚙️ Settings"]


def render_bottom_navigation():
    """Top nav: Streamlit 1.40+ uses st.rerun (not experimental_rerun). Radio key drives current_page."""
    st.markdown('<div class="top-nav"></div>', unsafe_allow_html=True)

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


# ─── Main Extractor Page ─────────────────────────────────────────────────────
def render_extractor_page():
    # Drain queue without full-page rerun while running (live UI uses st.fragment)
    q = st.session_state.get("ws_message_queue")
    drain_ws_queue(q)

    st.markdown('<p class="app-title">Live extraction</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="app-subtitle">Search results and PDF processing run in the browser. Open Settings below when you need to tune behavior.</p>',
        unsafe_allow_html=True,
    )

    # ── Settings (collapsed by default) ─────────────────────────────────────
    with st.expander("Settings", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Automation**")
            max_pages = st.number_input(
                "Max pages per query",
                min_value=1,
                max_value=500,
                value=int(st.session_state.settings.get("max_pages", 10)),
                step=1,
                help="Higher values scan more result pages per query variant. Use larger numbers for very high volume targets.",
            )
            st.session_state.settings["max_pages"] = max_pages
            delay_pages = st.number_input(
                "Delay between pages (seconds)",
                min_value=0.0,
                max_value=10.0,
                value=3.0,
                step=0.5,
            )
            delay_actions = st.number_input(
                "Action delay (seconds)",
                min_value=0.0,
                max_value=5.0,
                value=1.0,
                step=0.1,
            )

        with col2:
            st.markdown("**Connection**")
            st.caption("**Search provider** is set in the left sidebar under **Engine**.")
            headless_live = st.checkbox(
                "Run headless (no browser window)",
                value=bool(st.session_state.settings.get("headless", False)),
                key="live_headless",
                help="No visible browser window. Activity still appears in the log; extraction continues normally.",
            )
            st.session_state.settings["headless"] = headless_live
            if headless_live:
                st.caption("Headless mode: log and lead counts still update live.")
            server_url = st.text_input("Server URL", value=WEBSOCKET_URL, help="WebSocket endpoint for the automation service")
            auto_save = st.checkbox("Save results to database", value=True)
            target_leads = st.number_input(
                "Target lead count (0 = no limit)",
                min_value=0,
                max_value=500000,
                value=int(st.session_state.get("target_lead_count", 0)),
                step=500,
                help="Optional cap. Additional query phrases may be used automatically when results are below the soft threshold. 0 leaves volume uncapped.",
            )
            st.session_state.target_lead_count = target_leads

    st.divider()

    # ── Query input (Start immediately follows) ───────────────────────────
    st.markdown("### Search query")
    st.caption(
        "Only **PDF** links from results are processed. `filetype:pdf` is applied automatically when you omit it. "
        "Describe **who or what** and **where** (or sector); extra phrases are added automatically when results are thin."
    )
    query_input = st.text_area(
        "Query",
        height=70,
        label_visibility="collapsed",
        placeholder=(
            "Example: nonprofit chamber of commerce members Denver Colorado\n"
            "Organization type, audience or role, and location — adjust as needed."
        ),
        key="query_input",
    )

    with st.expander("Batch mode (multiple queries)", expanded=False):
        st.text_area(
            "Up to 10 queries (one per line)",
            height=150,
            placeholder=(
                "rotary club officers Seattle Washington\n"
                "HOA board of directors contact Austin Texas\n"
                "small business association membership roster Chicago Illinois"
            ),
            key="batch_queries",
            help="When this box has text, it replaces the single query above. Reload between queries is recommended for reliability.",
        )
        st.checkbox(
            "Reload browser between each query",
            value=True,
            key="batch_reload",
            help="Closes and restarts the browser after each line — reduces stuck sessions on long batches.",
        )

    _batch_raw = (st.session_state.get("batch_queries") or "").strip()
    batch_mode = bool(_batch_raw) and any(line.strip() for line in _batch_raw.split("\n"))

    # ── Controls (immediately after query / batch) ──────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        start_btn = st.button("Start", type="primary", use_container_width=True, disabled=st.session_state.is_running)
    with c2:
        stop_btn = st.button("Stop", use_container_width=True, disabled=not st.session_state.is_running)
    with c3:
        clear_btn = st.button("Clear", use_container_width=True)
    with c4:
        check_srv_clicked = st.button("Check server", use_container_width=True)

    if clear_btn:
        st.session_state.activity_log = []
        st.session_state.extracted_leads = []
        st.session_state.current_screenshot = None
        st.rerun()

    if stop_btn:
        st.session_state.is_running = False
        ws = _ws_client_ref[0] if _ws_client_ref else None
        if ws:
            try:
                if hasattr(ws, "send"):
                    ws.send(json.dumps({"command": "stop"}))
                    st.session_state.activity_log.append("Stop sent to automation service.")
                else:
                    st.session_state.activity_log.append("Stop requested (connection closing).")
            except Exception as e:
                st.session_state.activity_log.append(f"Stop requested ({str(e)[:50]}).")
        else:
            st.session_state.activity_log.append("Stopped (no active connection).")
        st.rerun()

    if start_btn:
        btxt = st.session_state.get("batch_queries") or ""
        queries: List[str] = []
        if batch_mode and btxt.strip():
            queries = [q.strip() for q in btxt.split("\n") if q.strip()][:10]
            if len([q for q in btxt.split("\n") if q.strip()]) > 10:
                st.warning("Only the first 10 queries will run.")
        else:
            qi = (st.session_state.get("query_input") or "").strip()
            if qi:
                queries = [qi]

        if not queries:
            st.warning("Enter a search query, or add lines under Batch mode.")
        else:
            st.session_state.is_running = True
            st.session_state.extracted_leads = []
            st.session_state.activity_log = []
            st.session_state.current_screenshot = None
            st.session_state.saved_files = []

            msg_queue = Queue()
            st.session_state.ws_message_queue = msg_queue
            target_leads = st.session_state.get("target_lead_count", 0)
            search_engine = st.session_state.get("search_engine", "duckduckgo")
            headless = bool(st.session_state.settings.get("headless", False))
            batch_reload = bool(batch_mode and st.session_state.get("batch_reload", True))
            thread = threading.Thread(
                target=run_websocket_client,
                args=(queries, max_pages, delay_pages, delay_actions, msg_queue, target_leads, search_engine, headless, batch_reload),
                daemon=True,
            )
            thread.start()
            st.session_state.live_queries_for_sessions = list(queries)
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
            st.caption("Ensure the automation service is running.")

    # ── Status Bar with Real-time Lead Count ─────────────────────────────
    status_text = "Ready" if not st.session_state.is_running else "🔄 Running..."
    if st.session_state.websocket_connected:
        status_text += " | ✅ Connected"
    else:
        status_text += " | ⚠️ Not Connected"
    
    # Add real-time lead count
    current_count = st.session_state.get("current_lead_count", 0)
    target_count = st.session_state.get("target_lead_count", 0)
    if current_count > 0:
        if target_count > 0:
            status_text += f" | 📊 Leads: {current_count}/{target_count}"
        else:
            status_text += f" | 📊 Leads: {current_count}"
    
    st.markdown(f'<div class="status-bar">{status_text}</div>', unsafe_allow_html=True)
    
    # Real-time lead count display (prominent)
    if st.session_state.is_running and current_count > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Current Leads", current_count)
        with col2:
            if target_count > 0:
                remaining = max(0, target_count - current_count)
                st.metric("🎯 Target", target_count, delta=f"{remaining} remaining" if remaining > 0 else "Reached!")
            else:
                st.metric("🎯 Target", "No limit")
        with col3:
            if target_count > 0 and current_count > 0:
                progress = min(100, (current_count / target_count) * 100)
                st.progress(progress / 100)
                st.caption(f"{progress:.1f}% complete")

    # ── Browser visibility tip (platform-specific) ─────────────────────────
    import platform
    if platform.system() == "Darwin":
        st.info(
            "**Browser window not visible?** Open **Settings** and enable **Run headless**, or launch from Terminal with "
            "`START_LEAD_EXTRACTOR.command` for a visible browser window."
        )
    elif platform.system() == "Windows":
        st.info(
            "**Browser window not visible?** Open **Settings** and enable **Run headless**, or use **Launch in CMD** below."
        )

    # ── Launch in Terminal/CMD (for visible browser) ───────────────────────
    import subprocess
    proj = Path(__file__).resolve().parent.parent
    if platform.system() == "Darwin":
        if st.button("Launch in Terminal (visible browser)", key="launch_terminal", help="Opens macOS Terminal if the in-app browser does not appear"):
            try:
                cmd = f"cd {proj} && python3 launch_app_simple.py"
                script = f'tell application "Terminal" to do script "{cmd}"'
                subprocess.run(["osascript", "-e", script], check=False, timeout=5)
                st.success("Terminal opened. Use the app there — the browser will pop up when you click Start.")
            except Exception as e:
                st.error(f"Could not open Terminal: {e}")
    elif platform.system() == "Windows":
        if st.button("Launch in CMD (visible browser)", key="launch_cmd", help="Opens Command Prompt if the in-app browser does not appear"):
            try:
                proj_str = str(proj).replace("'", "''")  # Escape for cmd
                subprocess.Popen(
                    ["cmd", "/k", f'cd /d "{proj}" && python launch_app_windows.py'],
                    cwd=str(proj),
                    creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0,
                )
                st.success("Command Prompt opened. Use the app there — the browser will pop up when you click Start.")
            except Exception as e:
                st.error(f"Could not open Command Prompt: {e}")

    # ── Live Browser View & Activity Log (fragment = no whole-screen blink) ─
    if st.session_state.is_running:
        _live_automation_fragment()
    else:
        _render_live_panel_content(extracting=False)

    if st.session_state.pop("_terminal_rerun", False):
        st.rerun()

    # ── Saved sessions for same query (merge / validate / download here) ───
    _render_live_query_sessions_panel()

    # ── Saved Files Display ─────────────────────────────────────────────────
    if st.session_state.saved_files:
        st.divider()
        st.markdown("### 💾 Saved Files")
        for file_info in st.session_state.saved_files:
            with st.expander(f"📄 {Path(file_info['path']).name} - {file_info['count']} leads ({file_info['timestamp']})"):
                st.code(file_info['path'], language=None)
                st.caption(f"Query: {file_info['query']}")

    # ── Results Table ──────────────────────────────────────────────────────
    if st.session_state.extracted_leads:
        st.divider()
        st.markdown(f"### 📊 Extracted Leads ({len(st.session_state.extracted_leads)})")

        em = sum(1 for l in st.session_state.extracted_leads if l.get("email"))
        ph = sum(1 for l in st.session_state.extracted_leads if l.get("phone"))
        nm = sum(1 for l in st.session_state.extracted_leads if l.get("contact_name"))

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total", len(st.session_state.extracted_leads))
        m2.metric("📧 Emails", em)
        m3.metric("📞 Phones", ph)
        m4.metric("👤 Names", nm)

        df = pd.DataFrame(st.session_state.extracted_leads)
        if not df.empty:
            # Column filter: show only selected fields
            preset = st.selectbox("Filter columns", list(COLUMN_PRESETS.keys()), key="live_preset")
            display_cols = [c for c in COLUMN_PRESETS[preset] if c in df.columns]
            if not display_cols:
                display_cols = ["contact_name", "phone", "email"]

            st.dataframe(
                df[display_cols], use_container_width=True, hide_index=True,
                column_config={
                    "contact_name": st.column_config.TextColumn("👤 Name", width="medium"),
                    "phone": st.column_config.TextColumn("📞 Phone", width="medium"),
                    "email": st.column_config.TextColumn("📧 Email", width="large"),
                    "business_name": st.column_config.TextColumn("Business", width="medium"),
                },
            )

            # Export buttons (use filtered columns for CSV/Excel)
            st.divider()
            export_cols = COLUMN_PRESETS[preset]
            e1, e2, e3, e4 = st.columns(4)
            with e1:
                if st.button("📄 CSV", use_container_width=True, key="exp_csv"):
                    path = export_to_csv(st.session_state.extracted_leads, columns=export_cols)
                    st.success(f"✅ {path}")
            with e2:
                if st.button("📊 Excel", use_container_width=True, key="exp_xlsx"):
                    path = export_to_excel(st.session_state.extracted_leads, columns=export_cols)
                    st.success(f"✅ {path}")
            with e3:
                if st.button("📕 PDF", use_container_width=True, key="exp_pdf"):
                    path = export_to_pdf(st.session_state.extracted_leads, query="Batch Results")
                    st.success(f"✅ {path}")
            with e4:
                csv_data = leads_to_dataframe(st.session_state.extracted_leads, columns=export_cols).to_csv(index=False)
                st.download_button("⬇️ Download", data=csv_data, file_name="leads.csv", mime="text/csv", use_container_width=True)


# ─── Saved Leads Page ───────────────────────────────────────────────────────
def render_saved_leads_page():
    st.markdown('<p class="app-title">📋 Saved Leads</p>', unsafe_allow_html=True)
    
    from app.database.db import get_recent_searches, get_leads_by_search
    searches = get_recent_searches(limit=50)
    
    if not searches:
        st.info("No searches found. Run some queries first!")
        return
    
    # Initialize session selection
    if "saved_leads_selected_ids" not in st.session_state:
        st.session_state.saved_leads_selected_ids = set()
    if "saved_leads_column_preset" not in st.session_state:
        st.session_state.saved_leads_column_preset = "Emails + Names + Phones"
    
    st.markdown("### 🔗 Merge & Export Multiple Sessions")
    st.caption(
        "Select sessions to merge, filter columns, and download or send to Email Sender. "
        "**Live runs** (new builds): one **Start** = one saved session — auto query-variations no longer create extra rows."
    )
    
    # Session multi-select
    sessions_by_date = {}
    for session in searches:
        date_str = str(session.get("created_at", ""))[:10] if session.get("created_at") else "Unknown"
        if date_str not in sessions_by_date:
            sessions_by_date[date_str] = []
        sessions_by_date[date_str].append(session)
    
    for date_str in sorted(sessions_by_date.keys(), reverse=True):
        with st.expander(f"📅 {date_str} ({len(sessions_by_date[date_str])} sessions)", expanded=False):
            for session in sessions_by_date[date_str]:
                sid = session["id"]
                query = str(session.get("query", ""))[:50] + ("..." if len(str(session.get("query", ""))) > 50 else "")
                n = session.get("num_leads", 0)
                is_sel = st.checkbox(
                    f"Session #{sid}: {query} ({n} leads)",
                    value=sid in st.session_state.saved_leads_selected_ids,
                    key=f"sel_{sid}",
                )
                if is_sel:
                    st.session_state.saved_leads_selected_ids.add(sid)
                else:
                    st.session_state.saved_leads_selected_ids.discard(sid)
    
    # Quick actions
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("✅ Select All", key="saved_select_all"):
            st.session_state.saved_leads_selected_ids = {s["id"] for s in searches}
            st.rerun()
    with c2:
        if st.button("❌ Clear", key="saved_clear"):
            st.session_state.saved_leads_selected_ids = set()
            st.rerun()
    with c3:
        if st.button("📅 Today Only", key="saved_today"):
            today = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
            st.session_state.saved_leads_selected_ids = {
                s["id"] for s in searches
                if str(s.get("created_at", "")).startswith(today)
            }
            st.rerun()
    
    # Merge, filter, download
    if st.session_state.saved_leads_selected_ids:
        all_merged = []
        for sid in st.session_state.saved_leads_selected_ids:
            for lead in get_leads_by_search(sid):
                lead_copy = dict(lead)
                lead_copy["_session_id"] = sid
                all_merged.append(lead_copy)

        # Export mode: Full | Unique (dedup only) | Unique valid (dedup + validation)
        export_mode = st.radio(
            "Export mode",
            [
                "Full (all leads, no dedup)",
                "Unique (dedup only, any email with @)",
                "Unique valid (dedup + strict validation)",
            ],
            key="saved_export_mode",
            help="Full = everything. Unique = dedupe by email. Unique valid = dedupe + format validation.",
        )
        use_full = "Full" in export_mode
        use_validation = "valid" in export_mode.lower()

        export_leads, ex_stats = filter_merged_leads_for_export(
            all_merged, use_full=use_full, use_validation=use_validation
        )

        if use_full:
            st.info(f"📋 {len(export_leads)} leads (full, no dedup)")
        else:
            if use_validation:
                st.success(
                    f"✅ {len(export_leads)} unique valid leads "
                    f"(from {ex_stats['merged_raw']} rows → {ex_stats['rows_after_split']} after splitting multi-email cells)"
                )
            else:
                st.success(
                    f"✅ {len(export_leads)} unique leads "
                    f"(from {ex_stats['merged_raw']} rows → {ex_stats['rows_after_split']} after split, dedup only)"
                )
            with st.expander("📊 Breakdown (why leads were excluded)"):
                if ex_stats["rows_after_split"] != ex_stats["merged_raw"]:
                    st.markdown(
                        f"- **Rows after splitting cells:** {ex_stats['rows_after_split']} "
                        f"(some rows had several addresses in the email field)"
                    )
                st.markdown(f"- **No email:** {ex_stats['no_email_count']} (empty/missing after split)")
                if use_validation:
                    st.markdown(f"- **Invalid format:** {ex_stats['invalid_count']} (failed email validation)")
                st.markdown(f"- **Duplicate:** {ex_stats['dup_count']} (same email already seen)")
                st.caption("Try **Full** to export everything, or **Unique (dedup only)** if validation drops too many.")

        # Column filter
        preset = st.selectbox(
            "Filter columns to show/export",
            list(COLUMN_PRESETS.keys()),
            key="saved_preset",
        )
        st.session_state.saved_leads_column_preset = preset
        cols = [c for c in COLUMN_PRESETS[preset] if c in (export_leads[0].keys() if export_leads else [])]
        if not cols:
            cols = list(COLUMN_PRESETS[preset])

        # Preview
        df_merged = pd.DataFrame(export_leads)
        show_cols = [c for c in cols if c in df_merged.columns]
        display_df = df_merged[show_cols] if show_cols else df_merged
        if not display_df.empty:
            st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Export merged
        st.markdown("**Download merged (filtered columns):**")
        e1, e2, e3, e4 = st.columns(4)
        with e1:
            csv_data = leads_to_dataframe(export_leads, columns=COLUMN_PRESETS[preset]).to_csv(index=False)
            st.download_button("⬇️ CSV", data=csv_data, file_name="merged_leads.csv", mime="text/csv", key="dl_merged_csv")
        with e2:
            if st.button("📄 Save CSV", key="save_merged_csv"):
                path = export_to_csv(export_leads, f"merged_{len(export_leads)}_leads.csv", columns=COLUMN_PRESETS[preset])
                st.success(f"✅ {path}")
        with e3:
            if st.button("📊 Save Excel", key="save_merged_xlsx"):
                path = export_to_excel(export_leads, f"merged_{len(export_leads)}_leads.xlsx", columns=COLUMN_PRESETS[preset])
                st.success(f"✅ {path}")
        with e4:
            if st.button("📧 Use for Email Campaign", key="use_merged_email"):
                st.session_state.merged_leads_for_email = export_leads
                st.session_state.selected_session_ids = list(st.session_state.saved_leads_selected_ids)
                st.session_state.current_page = "📧 Email Sender"
                st.session_state.top_nav_radio = "📧 Email Sender"
                st.rerun()
    
    st.divider()
    st.markdown("### 🔍 Individual Sessions")
    st.caption("View and export each session separately. Use the column filter below for exports.")
    
    single_preset = st.selectbox("Export columns (per session)", list(COLUMN_PRESETS.keys()), key="single_preset")
    single_cols = COLUMN_PRESETS[single_preset]
    
    for search in searches:
        search_id = search["id"]
        query = search["query"]
        num_leads = search["num_leads"]
        created_at = search["created_at"]
        
        with st.expander(f"Session #{search_id}: {query[:60]}{'...' if len(query) > 60 else ''} ({num_leads} leads) - {created_at}"):
            leads = get_leads_by_search(search_id)
            if leads:
                df = pd.DataFrame(leads)
                display_cols = ["contact_name", "phone", "email"]
                avail = [c for c in display_cols if c in df.columns]
                
                st.dataframe(
                    df[avail], use_container_width=True, hide_index=True,
                    column_config={
                        "contact_name": st.column_config.TextColumn("👤 Name", width="medium"),
                        "phone": st.column_config.TextColumn("📞 Phone", width="medium"),
                        "email": st.column_config.TextColumn("📧 Email", width="large"),
                    },
                )
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    csv_one = leads_to_dataframe(leads, columns=single_cols).to_csv(index=False)
                    st.download_button("⬇️ Download CSV", data=csv_one, file_name=f"session_{search_id}.csv", mime="text/csv", key=f"dl_{search_id}")
                with col2:
                    if st.button(f"📄 Save CSV", key=f"csv_{search_id}"):
                        path = export_to_csv(leads, f"session_{search_id}", columns=single_cols)
                        st.success(f"✅ {path}")
                with col3:
                    if st.button(f"📊 Save Excel", key=f"xlsx_{search_id}"):
                        path = export_to_excel(leads, f"session_{search_id}", columns=single_cols)
                        st.success(f"✅ {path}")
            else:
                st.caption("No leads found for this session.")


# ─── Settings Page ────────────────────────────────────────────────────────────
def render_settings_page():
    """Render settings page"""
    st.markdown('<p class="app-title">⚙️ Settings</p>', unsafe_allow_html=True)
    st.markdown('<p class="app-subtitle">Configure application settings</p>', unsafe_allow_html=True)

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
        st.success("Settings saved successfully.")
        st.rerun()

    st.divider()
    st.caption("Server status and stats are available in the sidebar.")


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    # Check license first - show activation dialog if needed
    is_valid, user = check_license()
    
    if not is_valid:
        # Show activation dialog
        if st.session_state.get("show_activation", True):
            activated = show_activation_dialog()
            if activated:
                st.session_state.show_activation = False
                st.rerun()
            else:
                st.stop()  # Stop app until license is activated
        else:
            show_activation_dialog()
            st.stop()
    
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
    elif current_page == "📧 Email Sender":
        render_email_sender_page()
    elif current_page == "⚙️ Settings":
        render_settings_page()


if __name__ == "__main__":
    main()
