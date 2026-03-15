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
    Check if valid license exists.
    
    Returns:
        Tuple of (is_valid, user_dict)
    """
    # Check session state first
    if st.session_state.get("license_valid") and st.session_state.get("license_key"):
        license_key = st.session_state.license_key
        
        # Quick validation
        license_info = validate_license(license_key, LICENSE_SECRET)
        if license_info.valid:
            # Check machine ID
            current_machine_id = get_machine_id()
            from app.license.generator import decode_license_key
            payload = decode_license_key(license_key)
            
            if payload and payload.get("machine_id"):
                if payload["machine_id"] == current_machine_id:
                    return True, st.session_state.get("user")
            
            # If no machine_id in payload, allow (backward compatibility)
            if not payload or not payload.get("machine_id"):
                return True, st.session_state.get("user")
    
    # Check database
    from app.database.db import get_connection
    conn = get_connection()
    
    # Ensure table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_license (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            license_key TEXT UNIQUE,
            machine_id TEXT,
            activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    """)
    
    cursor = conn.cursor()
    cursor.execute(
        "SELECT license_key FROM app_license WHERE is_active = 1 ORDER BY activated_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()
    
    if row:
        license_key = row[0]
        
        # Validate
        license_info = validate_license(license_key, LICENSE_SECRET)
        if license_info.valid:
            # Check machine ID
            current_machine_id = get_machine_id()
            from app.license.generator import decode_license_key
            payload = decode_license_key(license_key)
            
            if payload and payload.get("machine_id"):
                if payload["machine_id"] != current_machine_id:
                    return False, None
            
            # Get or create user
            user = user_manager.get_user_by_license(license_key)
            if not user:
                user = user_manager.create_user_from_license(license_key)
            
            if user:
                st.session_state.license_key = license_key
                st.session_state.user = user
                st.session_state.license_valid = True
                return True, user
    
    return False, None


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

