"""
License Key Generator - Admin tool to create license keys.

Usage:
    python -m backend.license.generator --email user@example.com --tier pro --days 365
"""
import argparse
import json
import base64
import hashlib
import hmac
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def generate_master_key() -> str:
    """Generate a new master key for license validation."""
    import secrets
    key = secrets.token_urlsafe(32)
    print(f"\n🔑 Your Master Key (save this in .env as LICENSE_MASTER_KEY):\n")
    print(f"   {key}\n")
    return key


def generate_license_key(
    master_key: str,
    email: str,
    tier: str = "free",
    days: int = 30,
    max_daily_searches: int = 10,
) -> str:
    """
    Generate an encrypted license key.
    
    The key contains:
    - User email
    - Tier (free/pro/enterprise)
    - Expiry date
    - Max daily searches
    - HMAC signature for tamper detection
    """
    expiry = (datetime.utcnow() + timedelta(days=days)).isoformat()
    
    # Build the license payload
    payload = {
        "email": email,
        "tier": tier,
        "expiry": expiry,
        "max_daily_searches": max_daily_searches,
        "created": datetime.utcnow().isoformat(),
    }
    
    # Serialize payload
    payload_json = json.dumps(payload, sort_keys=True)
    payload_bytes = payload_json.encode("utf-8")
    
    # Create HMAC signature
    signature = hmac.new(
        master_key.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    
    # Combine payload + signature
    license_data = {
        "payload": payload,
        "signature": signature,
    }
    
    # Encode to base64 for a clean license key format
    license_json = json.dumps(license_data)
    license_b64 = base64.urlsafe_b64encode(license_json.encode("utf-8")).decode("utf-8")
    
    # Format as chunks for readability (XXXX-XXXX-XXXX format)
    chunk_size = 8
    chunks = [license_b64[i:i + chunk_size] for i in range(0, len(license_b64), chunk_size)]
    formatted_key = "-".join(chunks)
    
    return formatted_key


def main():
    parser = argparse.ArgumentParser(description="Lead Extractor License Key Generator")
    subparsers = parser.add_subparsers(dest="command")
    
    # Generate master key
    subparsers.add_parser("master-key", help="Generate a new master key")
    
    # Generate license
    gen_parser = subparsers.add_parser("generate", help="Generate a license key")
    gen_parser.add_argument("--master-key", required=True, help="Master key for signing")
    gen_parser.add_argument("--email", required=True, help="User email")
    gen_parser.add_argument(
        "--tier",
        choices=["free", "pro", "enterprise"],
        default="free",
        help="License tier",
    )
    gen_parser.add_argument("--days", type=int, default=30, help="License validity in days")
    
    args = parser.parse_args()
    
    if args.command == "master-key":
        generate_master_key()
    elif args.command == "generate":
        # Set max searches based on tier
        tier_searches = {"free": 10, "pro": 100, "enterprise": 9999}
        max_searches = tier_searches.get(args.tier, 10)
        
        key = generate_license_key(
            master_key=args.master_key,
            email=args.email,
            tier=args.tier,
            days=args.days,
            max_daily_searches=max_searches,
        )
        
        print(f"\n✅ License Key Generated!")
        print(f"   Email: {args.email}")
        print(f"   Tier:  {args.tier}")
        print(f"   Valid: {args.days} days")
        print(f"   Max Searches/Day: {max_searches}")
        print(f"\n🔑 License Key:\n")
        print(f"   {key}\n")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

