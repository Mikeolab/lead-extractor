"""
Lead Extractor Pro - Live Browser Automation
Streamlit UI that connects to FastAPI WebSocket server for real-time browser visualization.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
import json
import threading
import time
import websocket
from typing import List
from streamlit_autorefresh import st_autorefresh

from app.config import APP_NAME, APP_VERSION, LICENSE_KEY, LICENSE_SECRET, EXPORT_DIR, WEBSOCKET_URL, AUTOMATION_SERVER_URL
from app.license.validator import validate_license
from app.license.activation_ui import check_license, show_activation_dialog, show_license_status
from app.database.db import get_all_leads, get_lead_stats
from app.export.exporter import export_to_csv, export_to_excel, COLUMN_PRESETS, leads_to_dataframe
from app.export.pdf_exporter import export_to_pdf
from app.config_manager import load_settings
from app.email.email_ui import render_email_sender_page


# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
</style>
""", unsafe_allow_html=True)


# ─── Thread-safe shared data (background thread writes here, main thread reads) ─
import threading

if "ws_data" not in st.session_state:
    st.session_state.ws_data = {
        "activity_log": [],
        "extracted_leads": [],
        "current_screenshot": None,
        "is_running": False,
        "needs_refresh": False,
        "current_lead_count": 0,
        "target_lead_count": 0,
        "saved_files": [],
        "last_update": 0,
    }
    st.session_state.ws_lock = threading.Lock()

# Convenience ref
_ws = st.session_state.ws_data
_ws_lock = st.session_state.ws_lock

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


# ─── WebSocket Client (URL from app.config, supports local + cloud) ───────────


def websocket_client(queries: List[str], max_pages: int, delay_pages: float, delay_actions: float,
                     ws_data: dict, ws_lock: threading.Lock, target_leads: int = 0):
    """Connect to WebSocket server and handle messages (runs in background thread).
    Writes to ws_data dict (NOT st.session_state) to avoid ScriptRunContext errors.
    """
    _last_screenshot_time = [0.0]

    def on_message(ws, message):
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            with ws_lock:
                if msg_type == "status":
                    ws_data["activity_log"].append(data.get("message", ""))
                    if len(ws_data["activity_log"]) > 200:
                        ws_data["activity_log"] = ws_data["activity_log"][-200:]
                    ws_data["needs_refresh"] = True

                elif msg_type == "screenshot":
                    screenshot_data = data.get("data", "")
                    if screenshot_data:
                        now = time.time()
                        if (now - _last_screenshot_time[0]) >= 1.0:
                            ws_data["current_screenshot"] = screenshot_data
                            _last_screenshot_time[0] = now
                            ws_data["needs_refresh"] = True

                elif msg_type == "ping":
                    pass

                elif msg_type == "leads":
                    ws_data["extracted_leads"].extend(data.get("data", []))
                    ws_data["current_lead_count"] = len(ws_data["extracted_leads"])
                    ws_data["needs_refresh"] = True

                elif msg_type == "lead_count":
                    ws_data["current_lead_count"] = data.get("count", 0)
                    ws_data["target_lead_count"] = data.get("target", 0)
                    ws_data["needs_refresh"] = True

                elif msg_type == "file_saved":
                    ws_data["saved_files"].append({
                        "path": data.get("path", ""),
                        "query": data.get("query", ""),
                        "count": data.get("count", 0),
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                    })
                    ws_data["needs_refresh"] = True

                elif msg_type == "complete":
                    all_leads = data.get("data", [])
                    if all_leads:
                        ws_data["extracted_leads"] = all_leads
                    ws_data["activity_log"].append("🎉 Automation completed!")
                    ws_data["is_running"] = False
                    ws_data["needs_refresh"] = True
                    time.sleep(1)
                    try:
                        ws.close()
                    except Exception:
                        pass

                elif msg_type == "error":
                    error_msg = data.get("message", "")
                    ws_data["activity_log"].append(error_msg)
                    if "fatal" in error_msg.lower() or "crash" in error_msg.lower():
                        ws_data["is_running"] = False
                        ws.close()
                    else:
                        ws_data["needs_refresh"] = True

        except Exception as e:
            with ws_lock:
                ws_data["activity_log"].append(f"❌ Error: {str(e)}")

    def on_error(ws, error):
        with ws_lock:
            ws_data["activity_log"].append(f"❌ WebSocket error: {str(error)}")
            ws_data["is_running"] = False

    def on_close(ws, close_status_code, close_msg):
        with ws_lock:
            ws_data["is_running"] = False

    def on_open(ws):
        with ws_lock:
            ws_data["is_running"] = True
        ws.send(json.dumps({
            "command": "start",
            "queries": queries,
            "max_pages": max_pages,
            "delay_pages": delay_pages,
            "delay_actions": delay_actions,
            "target_leads": target_leads,
        }))

    try:
        ws_app = websocket.WebSocketApp(
            WEBSOCKET_URL,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open,
        )
        with ws_lock:
            ws_data["ws_client"] = ws_app
        ws_app.run_forever()
    except Exception as e:
        with ws_lock:
            ws_data["activity_log"].append(f"❌ Connection error: {str(e)}")
            ws_data["is_running"] = False


# ─── License Check ───────────────────────────────────────────────────────────
# License checking is now handled by activation_ui module


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

        st.markdown("### ⚙️ Engine")
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
        except Exception:
            st.caption("No data yet")


# ─── Bottom Navigation ────────────────────────────────────────────────────────
def render_bottom_navigation():
    """Render bottom navigation tabs"""
    st.markdown("---")
    st.markdown("### 📑 Navigation")
    
    # Create navigation buttons
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔍 Live", use_container_width=True, 
                    type="primary" if st.session_state.current_page == "🔍 Live Extractor" else "secondary",
                    key="nav_live"):
            st.session_state.current_page = "🔍 Live Extractor"
            st.rerun()
    
    with col2:
        if st.button("📋 Saved", use_container_width=True,
                    type="primary" if st.session_state.current_page == "📋 Saved Leads" else "secondary",
                    key="nav_saved"):
            st.session_state.current_page = "📋 Saved Leads"
            st.rerun()
    
    with col3:
        if st.button("📧 Sender", use_container_width=True,
                    type="primary" if st.session_state.current_page == "📧 Email Sender" else "secondary",
                    key="nav_sender"):
            st.session_state.current_page = "📧 Email Sender"
            st.rerun()
    
    with col4:
        if st.button("⚙️ Settings", use_container_width=True,
                    type="primary" if st.session_state.current_page == "⚙️ Settings" else "secondary",
                    key="nav_settings"):
            st.session_state.current_page = "⚙️ Settings"
            st.rerun()


# ─── Main Extractor Page ─────────────────────────────────────────────────────
def _sync_ws_data():
    """Copy data from thread-safe ws_data dict into session_state for rendering."""
    _ws = st.session_state.ws_data
    _lock = st.session_state.ws_lock
    with _lock:
        if _ws["activity_log"]:
            st.session_state.activity_log = list(_ws["activity_log"])
        if _ws["extracted_leads"]:
            st.session_state.extracted_leads = list(_ws["extracted_leads"])
        if _ws["current_screenshot"]:
            st.session_state.current_screenshot = _ws["current_screenshot"]
        st.session_state.current_lead_count = _ws["current_lead_count"]
        st.session_state.target_lead_count = _ws["target_lead_count"]
        if _ws["saved_files"]:
            st.session_state.saved_files = list(_ws["saved_files"])
        if not _ws["is_running"] and st.session_state.is_running:
            st.session_state.is_running = False
        st.session_state.needs_refresh = _ws["needs_refresh"]
        _ws["needs_refresh"] = False


def render_extractor_page():
    # Sync thread data into session state on every render
    _sync_ws_data()

    st.markdown('<p class="app-title">🎯 Live Browser Automation</p>', unsafe_allow_html=True)
    st.markdown('<p class="app-subtitle">Watch the browser automate Google searches in real-time</p>', unsafe_allow_html=True)

    # ── Query Input ─────────────────────────────────────────────────────────
    st.markdown("### 🔍 Search Queries")
    query_input = st.text_area(
        "Enter search query:",
        height=70,
        placeholder="Example: 'digital twin engineers' 'service' filetype:pdf intext:@ intext:Livermore, California",
        key="query_input",
    )

    # ── Batch Mode ─────────────────────────────────────────────────────────
    with st.expander("➕ Batch Mode (Multiple Queries)", expanded=False):
        batch_queries_text = st.text_area(
            "Enter multiple queries (one per line):",
            height=150,
            key="batch_queries",
        )
        batch_mode = st.checkbox("Enable Batch Mode", value=False)

    # ── Settings ───────────────────────────────────────────────────────────
    with st.expander("⚙️ Settings", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Automation Settings**")
            max_pages = st.number_input("Max Pages per Query", min_value=1, max_value=20, value=10, step=1)
            delay_pages = st.number_input("Delay Between Pages (s)", min_value=0.0, max_value=10.0, value=3.0, step=0.5)
            delay_actions = st.number_input("Action Delay (s)", min_value=0.0, max_value=5.0, value=1.0, step=0.1)

        with col2:
            st.markdown("**Server Settings**")
            server_url = st.text_input("Server URL", value=WEBSOCKET_URL, help="WebSocket server URL")
            auto_save = st.checkbox("Auto-Save to Database", value=True)
            target_leads = st.number_input("Target Lead Count (0 = no limit)", min_value=0, max_value=10000, value=0, step=10, help="Stop automatically when this many leads are extracted")
            st.session_state.target_lead_count = target_leads

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

    # ── Controls ──────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        start_btn = st.button("▶️ Start", type="primary", use_container_width=True, disabled=st.session_state.is_running)
    with col2:
        stop_btn = st.button("⏹️ Stop", use_container_width=True, disabled=not st.session_state.is_running)
    with col3:
        clear_btn = st.button("🗑️ Clear", use_container_width=True)
    with col4:
        if st.button("🔄 Check Server", use_container_width=True):
            # Test server connection
            try:
                import httpx
                resp = httpx.get(f"{AUTOMATION_SERVER_URL.rstrip('/')}/", timeout=2)
                if resp.status_code == 200:
                    st.session_state.websocket_connected = True
                    st.session_state.server_checked = True
                    st.success("✅ Server is running")
                else:
                    st.error("❌ Server returned error")
            except Exception as e:
                st.session_state.websocket_connected = False
                st.error(f"❌ Server not running: {str(e)[:50]}")
                st.caption("Make sure automation server is running")

    if clear_btn:
        st.session_state.activity_log = []
        st.session_state.extracted_leads = []
        st.session_state.current_screenshot = None
        with st.session_state.ws_lock:
            st.session_state.ws_data["activity_log"] = []
            st.session_state.ws_data["extracted_leads"] = []
            st.session_state.ws_data["current_screenshot"] = None
            st.session_state.ws_data["saved_files"] = []
            st.session_state.ws_data["current_lead_count"] = 0
        st.rerun()

    # ── Stop Button Handler ───────────────────────────────────────────────────
    if stop_btn:
        st.session_state.is_running = False
        with st.session_state.ws_lock:
            st.session_state.ws_data["is_running"] = False
        ws_client = st.session_state.ws_data.get("ws_client")
        if ws_client:
            try:
                if hasattr(ws_client, 'send'):
                    ws_client.send(json.dumps({"command": "stop"}))
                    st.session_state.activity_log.append("🛑 Stop command sent to server...")
                else:
                    st.session_state.activity_log.append("🛑 Stop requested (connection closing...)")
            except Exception as e:
                st.session_state.activity_log.append(f"🛑 Stop requested (error: {str(e)[:50]})")
        else:
            st.session_state.activity_log.append("🛑 Stopped (no active connection)")
        st.rerun()

    # ── Live Browser View & Activity Log ───────────────────────────────────
    col_browser, col_log = st.columns([1.2, 0.8])

    with col_browser:
        st.markdown("### 🖥️ Live Browser View")
        browser_view = st.empty()
        if st.session_state.current_screenshot:
            browser_view.image(
                f"data:image/png;base64,{st.session_state.current_screenshot}",
                use_container_width=True,
                caption="Live browser automation",
            )
        else:
            browser_view.info("👆 Click 'Start' to see live browser automation...")

    with col_log:
        st.markdown("### 📋 Activity Log")
        log_text = "\n".join(st.session_state.activity_log[-50:])
        st.markdown(f'<div class="activity-log">{log_text}</div>', unsafe_allow_html=True)

    # ── Start Automation ───────────────────────────────────────────────────
    if start_btn:
        queries = []
        if batch_mode and batch_queries_text:
            queries = [q.strip() for q in batch_queries_text.split("\n") if q.strip()]
        elif query_input:
            queries = [query_input.strip()]

        if not queries:
            st.warning("Please enter at least one search query.")
        else:
            st.session_state.is_running = True
            st.session_state.extracted_leads = []
            st.session_state.activity_log = []
            st.session_state.current_screenshot = None
            st.session_state.saved_files = []
            # Reset shared data
            with st.session_state.ws_lock:
                ws = st.session_state.ws_data
                ws["activity_log"] = []
                ws["extracted_leads"] = []
                ws["current_screenshot"] = None
                ws["saved_files"] = []
                ws["current_lead_count"] = 0
                ws["is_running"] = True
                ws["needs_refresh"] = False

            target_leads = st.session_state.get("target_lead_count", 0)
            thread = threading.Thread(
                target=websocket_client,
                args=(queries, max_pages, delay_pages, delay_actions,
                      st.session_state.ws_data, st.session_state.ws_lock, target_leads),
                daemon=True,
            )
            thread.start()

    # ── Auto-refresh when running (smooth, no flicker) ─────────────────────
    if st.session_state.is_running:
        st_autorefresh(interval=2000, limit=None, key="live_autorefresh")

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
    st.caption("Select sessions to merge, filter columns, and download or send to Email Sender.")
    
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
        
        # Dedupe by email (keep first)
        seen = set()
        unique = []
        for l in all_merged:
            e = (l.get("email") or "").lower().strip()
            if e and "@" in e and e not in seen:
                seen.add(e)
                unique.append(l)
        
        st.success(f"✅ {len(unique)} unique leads (from {len(all_merged)} total across {len(st.session_state.saved_leads_selected_ids)} session(s))")
        
        # Column filter
        preset = st.selectbox(
            "Filter columns to show/export",
            list(COLUMN_PRESETS.keys()),
            key="saved_preset",
        )
        st.session_state.saved_leads_column_preset = preset
        cols = [c for c in COLUMN_PRESETS[preset] if c in (unique[0].keys() if unique else [])]
        if not cols:
            cols = list(COLUMN_PRESETS[preset])
        
        # Preview
        df_merged = pd.DataFrame(unique)
        show_cols = [c for c in cols if c in df_merged.columns]
        display_df = df_merged[show_cols] if show_cols else df_merged
        if not display_df.empty:
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Export merged
        st.markdown("**Download merged (filtered columns):**")
        e1, e2, e3, e4 = st.columns(4)
        with e1:
            csv_data = leads_to_dataframe(unique, columns=COLUMN_PRESETS[preset]).to_csv(index=False)
            st.download_button("⬇️ CSV", data=csv_data, file_name="merged_leads.csv", mime="text/csv", key="dl_merged_csv")
        with e2:
            if st.button("📄 Save CSV", key="save_merged_csv"):
                path = export_to_csv(unique, f"merged_{len(unique)}_leads.csv", columns=COLUMN_PRESETS[preset])
                st.success(f"✅ {path}")
        with e3:
            if st.button("📊 Save Excel", key="save_merged_xlsx"):
                path = export_to_excel(unique, f"merged_{len(unique)}_leads.xlsx", columns=COLUMN_PRESETS[preset])
                st.success(f"✅ {path}")
        with e4:
            if st.button("📧 Use for Email Campaign", key="use_merged_email"):
                st.session_state.merged_leads_for_email = unique
                st.session_state.selected_session_ids = list(st.session_state.saved_leads_selected_ids)
                st.session_state.current_page = "📧 Email Sender"
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
    
    st.info("Settings page coming soon! For now, use the sidebar to check server status and view stats.")


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
    
    # Render bottom navigation at the bottom
    render_bottom_navigation()


if __name__ == "__main__":
    main()
