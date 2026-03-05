"""
License Key Validator - Validates and decodes license keys.
"""
import json
import base64
import hashlib
import hmac
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class LicenseInfo:
    """Decoded license information."""
    email: str
    tier: str
    expiry: datetime
    max_daily_searches: int
    created: datetime
    is_valid: bool
    error: Optional[str] = None


def validate_license_key(license_key: str, master_key: str) -> LicenseInfo:
    """
    Validate a license key and return the decoded information.
    
    Args:
        license_key: The formatted license key (XXXX-XXXX-... format)
        master_key: The master key used for HMAC verification
        
    Returns:
        LicenseInfo with validation results
    """
    try:
        # Remove formatting (dashes)
        clean_key = license_key.replace("-", "").strip()
        
        # Decode base64
        try:
            decoded_bytes = base64.urlsafe_b64decode(clean_key + "==")  # Add padding
            decoded_str = decoded_bytes.decode("utf-8")
        except Exception:
            return LicenseInfo(
                email="", tier="", expiry=datetime.min,
                max_daily_searches=0, created=datetime.min,
                is_valid=False, error="Invalid license key format"
            )
        
        # Parse JSON
        try:
            license_data = json.loads(decoded_str)
        except json.JSONDecodeError:
            return LicenseInfo(
                email="", tier="", expiry=datetime.min,
                max_daily_searches=0, created=datetime.min,
                is_valid=False, error="Corrupted license key"
            )
        
        payload = license_data.get("payload", {})
        signature = license_data.get("signature", "")
        
        # Verify HMAC signature
        payload_json = json.dumps(payload, sort_keys=True)
        payload_bytes = payload_json.encode("utf-8")
        
        expected_signature = hmac.new(
            master_key.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return LicenseInfo(
                email="", tier="", expiry=datetime.min,
                max_daily_searches=0, created=datetime.min,
                is_valid=False, error="Invalid license key - signature mismatch"
            )
        
        # Parse dates
        expiry = datetime.fromisoformat(payload["expiry"])
        created = datetime.fromisoformat(payload["created"])
        
        # Check expiry
        if datetime.utcnow() > expiry:
            return LicenseInfo(
                email=payload["email"],
                tier=payload["tier"],
                expiry=expiry,
                max_daily_searches=payload["max_daily_searches"],
                created=created,
                is_valid=False,
                error=f"License expired on {expiry.strftime('%Y-%m-%d')}"
            )
        
        # Valid!
        return LicenseInfo(
            email=payload["email"],
            tier=payload["tier"],
            expiry=expiry,
            max_daily_searches=payload["max_daily_searches"],
            created=created,
            is_valid=True,
        )
        
    except Exception as e:
        return LicenseInfo(
            email="", tier="", expiry=datetime.min,
            max_daily_searches=0, created=datetime.min,
            is_valid=False, error=f"License validation error: {str(e)}"
        )

