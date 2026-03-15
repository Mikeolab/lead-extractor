"""
License Key Generator
Generates HMAC-signed license keys with optional expiry dates.
Run this script as admin to create license keys for users.
"""
from __future__ import annotations

import hmac
import hashlib
import json
import base64
from datetime import datetime, timedelta
from typing import Optional


def generate_license_key(
    secret: str,
    licensee_name: str,
    machine_id: str = "",
    machine_ids: Optional[list] = None,
    plan: str = "pro",
    days_valid: int = 365,
) -> str:
    """
    Generate an HMAC-signed license key.

    Args:
        secret: The signing secret
        licensee_name: Name of the license holder
        machine_id: Single machine ID to bind to (optional)
        machine_ids: List of machine IDs - license valid on any of these (optional)
        plan: License plan (free, pro, enterprise)
        days_valid: Number of days the license is valid

    Returns:
        Base64-encoded license key string
    """
    issued_at = datetime.utcnow().isoformat()
    expires_at = (datetime.utcnow() + timedelta(days=days_valid)).isoformat()

    payload = {
        "licensee": licensee_name,
        "plan": plan,
        "issued_at": issued_at,
        "expires_at": expires_at,
    }

    # Add machine binding (if any)
    if machine_ids:
        payload["machine_ids"] = [m.replace("-", "").replace(" ", "").lower() for m in machine_ids]
    elif machine_id:
        payload["machine_id"] = machine_id.replace("-", "").replace(" ", "").lower()

    payload_json = json.dumps(payload, sort_keys=True)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()

    # Create HMAC signature
    signature = hmac.new(
        secret.encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).hexdigest()

    # License key format: PAYLOAD.SIGNATURE
    license_key = f"{payload_b64}.{signature}"
    return license_key


def decode_license_key(license_key: str) -> Optional[dict]:
    """Decode a license key and return the payload (without verifying)."""
    try:
        parts = license_key.strip().split(".")
        if len(parts) != 2:
            return None
        payload_b64 = parts[0]
        payload_json = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        return json.loads(payload_json)
    except Exception:
        return None

