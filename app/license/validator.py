"""
License Key Validator
Validates HMAC-signed license keys and checks expiry.
"""
import hmac
import hashlib
import json
import base64
from datetime import datetime
from dataclasses import dataclass


@dataclass
class LicenseInfo:
    valid: bool
    licensee: str = ""
    plan: str = ""
    issued_at: str = ""
    expires_at: str = ""
    error: str = ""


def validate_license(license_key: str, secret: str) -> LicenseInfo:
    """
    Validate a license key against the signing secret.

    Args:
        license_key: The license key to validate
        secret: The signing secret used to generate the key

    Returns:
        LicenseInfo with validation result
    """
    if not license_key or not license_key.strip():
        return LicenseInfo(valid=False, error="No license key provided")

    try:
        parts = license_key.strip().split(".")
        if len(parts) != 2:
            return LicenseInfo(valid=False, error="Invalid license key format")

        payload_b64, provided_signature = parts

        # Verify HMAC signature
        expected_signature = hmac.new(
            secret.encode(),
            payload_b64.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(provided_signature, expected_signature):
            return LicenseInfo(valid=False, error="Invalid license key signature")

        # Decode payload
        payload_json = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload = json.loads(payload_json)

        # Check expiry
        expires_at = datetime.fromisoformat(payload["expires_at"])
        if datetime.utcnow() > expires_at:
            return LicenseInfo(
                valid=False,
                licensee=payload.get("licensee", ""),
                plan=payload.get("plan", ""),
                issued_at=payload.get("issued_at", ""),
                expires_at=payload.get("expires_at", ""),
                error="License key has expired",
            )
        
        # Check machine binding if present (machine_id or machine_ids)
        machine_ids = payload.get("machine_ids")
        machine_id = payload.get("machine_id")
        if machine_ids:
            from app.license.machine_id import get_machine_id
            current = get_machine_id().lower()
            allowed = [m.lower() for m in machine_ids]
            if current not in allowed:
                return LicenseInfo(
                    valid=False,
                    licensee=payload.get("licensee", ""),
                    plan=payload.get("plan", ""),
                    issued_at=payload.get("issued_at", ""),
                    expires_at=payload.get("expires_at", ""),
                    error="License not valid for this computer",
                )
        elif machine_id:
            from app.license.machine_id import get_machine_id, validate_machine_id
            current_machine_id = get_machine_id()
            if not validate_machine_id(machine_id, current_machine_id):
                return LicenseInfo(
                    valid=False,
                    licensee=payload.get("licensee", ""),
                    plan=payload.get("plan", ""),
                    issued_at=payload.get("issued_at", ""),
                    expires_at=payload.get("expires_at", ""),
                    error="License not valid for this computer",
                )

        return LicenseInfo(
            valid=True,
            licensee=payload.get("licensee", ""),
            plan=payload.get("plan", ""),
            issued_at=payload.get("issued_at", ""),
            expires_at=payload.get("expires_at", ""),
        )

    except Exception as e:
        return LicenseInfo(valid=False, error=f"License validation error: {str(e)}")

