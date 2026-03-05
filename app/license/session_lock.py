"""
Single-session license lock: one license = one active place at a time.
Prevents the same license from being used in two browsers or two devices.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta
from app.license.machine_id import get_machine_id


# After this long without activity, another session can take over
SESSION_STALE_MINUTES = 30


def get_license_session_id() -> str:
    """
    Unique ID for this "place": one browser session (web) or one machine (desktop).
    In Streamlit we use a per-browser UUID; otherwise machine_id.
    """
    try:
        import streamlit as st
        if "_license_session_id" not in st.session_state:
            st.session_state["_license_session_id"] = str(uuid.uuid4())
        return st.session_state["_license_session_id"]
    except Exception:
        pass
    return get_machine_id()


def claim_license_session(license_key: str, session_id: str) -> tuple[bool, str]:
    """
    Try to claim this license for this session.
    Returns (True, "") if this session can use it; (False, error_message) if already in use elsewhere.
    """
    from app.database.db import get_connection
    conn = get_connection()
    now = datetime.utcnow()
    stale_cutoff = (now - timedelta(minutes=SESSION_STALE_MINUTES)).isoformat()

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT session_id, last_seen_ts FROM license_active_sessions WHERE license_key = ?",
            (license_key,),
        )
        row = cursor.fetchone()
        if row is None:
            # No one has claimed; we take it (upsert for SQLite and PostgreSQL)
            cursor.execute(
                """INSERT INTO license_active_sessions (license_key, session_id, last_seen_ts)
                   VALUES (?, ?, ?)
                   ON CONFLICT(license_key) DO UPDATE SET session_id = excluded.session_id, last_seen_ts = excluded.last_seen_ts""",
                (license_key, session_id, now.isoformat()),
            )
            conn.commit()
            conn.close()
            return True, ""
        # Handle both dict-like (adapter) and indexable rows
        existing_session = row["session_id"] if hasattr(row, "get") else row[0]
        last_seen = row["last_seen_ts"] if hasattr(row, "get") else row[1]
        if existing_session == session_id:
            # Same session; refresh and allow
            cursor.execute(
                "UPDATE license_active_sessions SET last_seen_ts = ? WHERE license_key = ?",
                (now.isoformat(), license_key),
            )
            conn.commit()
            conn.close()
            return True, ""
        if last_seen and str(last_seen) < stale_cutoff:
            # Stale; we take over
            cursor.execute(
                "UPDATE license_active_sessions SET session_id = ?, last_seen_ts = ? WHERE license_key = ?",
                (session_id, now.isoformat(), license_key),
            )
            conn.commit()
            conn.close()
            return True, ""
        conn.close()
        return False, "This license is already in use on another device or browser. Only one active session is allowed. Try again later or close the other session."
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        # If table doesn't exist yet (old DB), allow and let table creation happen elsewhere
        return True, ""


def touch_license_session(license_key: str, session_id: str) -> None:
    """Update last_seen so this session keeps the claim."""
    from app.database.db import get_connection
    conn = get_connection()
    now = datetime.utcnow().isoformat()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE license_active_sessions SET last_seen_ts = ? WHERE license_key = ? AND session_id = ?",
            (now, license_key, session_id),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()
