"""
License Activation UI
Streamlit components for license activation dialog
"""
from __future__ import annotations
from typing import Optional, Dict, Tuple
import streamlit as st
from app.license.machine_id import get_machine_id
from app.license.validator import validate_license, LicenseInfo
from app.config import LICENSE_SECRET
from app.users.manager import user_manager

# Try to import pyperclip, fallback if not available
try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False


def show_activation_dialog() -> bool:
    """
    Show license activation dialog.
    
    Returns:
        True if license activated successfully, False otherwise
    """
    st.title("🔐 License Activation Required")
    
    st.info(
        "This software requires a valid license key to operate. "
        "Please follow the steps below to activate your license."
    )
    
    # Step 1: Show Hardware ID
    st.subheader("Step 1: Get Your Hardware ID")
    st.write("Copy your Hardware ID and send it to the administrator to receive your license key.")
    
    machine_id = get_machine_id()
    
    # Use st.code() - has built-in copy button that works in browsers (pyperclip fails in Streamlit/browser)
    st.caption("Your Hardware ID (click the copy icon to copy):")
    st.code(machine_id, language=None)
    st.caption("Send this ID to the administrator to receive your license key.")
    
    st.divider()
    
    # Step 2: Enter License Key
    st.subheader("Step 2: Enter Your License Key")
    st.write("Enter the license key you received via email to activate the software.")
    
    license_key = st.text_input(
        "Enter License Key:",
        value="",
        placeholder="Paste your license key here",
        key="license_key_input",
        type="default"
    )
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("✅ Activate License", type="primary", use_container_width=True):
            if not license_key:
                st.error("Please enter a license key.")
            else:
                # Clean license key (remove dashes, spaces, newlines)
                clean_license_key = license_key.replace("-", "").replace(" ", "").replace("\n", "").strip()
                
                # Validate license
                license_info = validate_license(clean_license_key, LICENSE_SECRET)
                
                if not license_info.valid:
                    st.error(f"❌ Invalid license key: {license_info.error}")
                else:
                    # Check machine ID
                    current_machine_id = get_machine_id()
                    # Note: Machine ID check will be added when we update the generator
                    # For now, we'll check if machine_id is in the payload
                    from app.license.generator import decode_license_key
                    payload = decode_license_key(clean_license_key)
                    
                    if payload and payload.get("machine_id"):
                        if payload["machine_id"] != current_machine_id:
                            st.error(
                                "❌ License not valid for this computer. "
                                "This license is bound to a different machine."
                            )
                            return False
                    
                    # Create user from license
                    user = user_manager.create_user_from_license(clean_license_key)
                    
                    if user:
                        # Store license in session
                        st.session_state.license_key = clean_license_key
                        st.session_state.user = user
                        st.session_state.license_valid = True
                        
                        # Store in database
                        from app.database.db import get_connection
                        conn = get_connection()
                        conn.execute(
                            """CREATE TABLE IF NOT EXISTS app_license (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                license_key TEXT UNIQUE,
                                machine_id TEXT,
                                activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                is_active BOOLEAN DEFAULT 1
                            )"""
                        )
                        conn.execute(
                            """INSERT OR REPLACE INTO app_license (license_key, machine_id, is_active)
                               VALUES (?, ?, 1)""",
                            (clean_license_key, current_machine_id)
                        )
                        conn.commit()
                        conn.close()
                        
                        st.success("✅ License activated successfully!")
                        st.balloons()
                        st.rerun()
                        return True
                    else:
                        st.error("❌ Failed to create user account. Please try again.")
                        return False
    
    with col2:
        if st.button("❌ Exit", use_container_width=True):
            st.stop()
    
    st.divider()
    
    # Contact information
    st.caption("💡 Need a license key? Contact: admin@yourapp.com")
    
    return False


def check_license() -> Tuple[bool, Optional[Dict]]:
    """
    Check if a valid, machine-bound license exists.

    Enforcement order:
      1. Session-state cache (fast path) — re-validates HMAC + machine ID every call.
      2. Database record — always checks both the HMAC and the machine_id column
         that was written at activation time.

    A license without a machine_id in its JWT payload is still accepted ONLY if
    the machine_id stored in the DB at activation matches this machine.
    There is no "backward compatibility" bypass — machine binding is always required.
    """
    current_machine_id = get_machine_id()
    from app.database.db import get_connection

    # ── Ensure table exists ───────────────────────────────────────────────────
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_license (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT UNIQUE,
            machine_id TEXT NOT NULL DEFAULT '',
            activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()

    # ── Session-state fast path ───────────────────────────────────────────────
    if st.session_state.get("license_valid") and st.session_state.get("license_key"):
        license_key = st.session_state.license_key
        license_info = validate_license(license_key, LICENSE_SECRET)
        if license_info.valid:
            # Always verify the machine ID stored at activation time
            bound_mid = st.session_state.get("_bound_machine_id", "")
            if bound_mid and bound_mid.lower() != current_machine_id.lower():
                # Machine changed or license shared to a different PC — block it
                st.session_state.license_valid = False
                st.session_state.license_key = None
                return False, None
            if bound_mid:
                return True, st.session_state.get("user")
            # bound_mid not yet in session — fall through to DB to load it

    # ── Database check ────────────────────────────────────────────────────────
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT license_key, machine_id FROM app_license WHERE is_active = 1 ORDER BY activated_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        return False, None

    license_key, stored_machine_id = row[0], (row[1] or "")

    # 1. HMAC signature + expiry
    license_info = validate_license(license_key, LICENSE_SECRET)
    if not license_info.valid:
        return False, None

    # 2. Machine binding — stored_machine_id is set at activation and is REQUIRED.
    #    If it's empty (legacy record), block and force re-activation.
    if not stored_machine_id:
        return False, None
    if stored_machine_id.lower() != current_machine_id.lower():
        return False, None

    # 3. Load / create the user record
    user = user_manager.get_user_by_license(license_key)
    if not user:
        user = user_manager.create_user_from_license(license_key)
    if not user:
        return False, None

    # Cache in session state (including the bound machine ID)
    st.session_state.license_key = license_key
    st.session_state.user = user
    st.session_state.license_valid = True
    st.session_state._bound_machine_id = stored_machine_id
    return True, user


def show_license_status():
    """Show current license status in sidebar"""
    is_valid, user = check_license()
    
    if is_valid and user:
        st.sidebar.success(f"✅ License Active")
        st.sidebar.caption(f"Plan: {user.get('plan', 'Unknown').upper()}")
        st.sidebar.caption(f"User: {user.get('username', 'Unknown')}")
        
        # Show expiry if available
        if st.session_state.get("license_key"):
            from app.license.generator import decode_license_key
            payload = decode_license_key(st.session_state.license_key)
            if payload and payload.get("expires_at"):
                from datetime import datetime
                expires = datetime.fromisoformat(payload["expires_at"])
                days_left = (expires - datetime.utcnow()).days
                if days_left > 0:
                    st.sidebar.caption(f"Expires in: {days_left} days")
                else:
                    st.sidebar.warning("⚠️ License expired!")
    else:
        st.sidebar.error("❌ No valid license")
        if st.sidebar.button("🔐 Activate License"):
            st.session_state.show_activation = True
            st.rerun()

