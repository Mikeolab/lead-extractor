#!/usr/bin/env python3
"""
License Key Generator - Admin Tool
Run this script to generate license keys for users.

Usage:
    python generate_license.py --name "John Doe" --plan pro --days 365
    python generate_license.py --name "Mike" --plan enterprise --days 730
"""
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import LICENSE_SECRET
from app.license.generator import generate_license_key, decode_license_key


def main():
    parser = argparse.ArgumentParser(description="Generate License Keys for Lead Extractor Pro")
    parser.add_argument("--name", required=True, help="Licensee name")
    parser.add_argument("--plan", choices=["free", "pro", "enterprise"], default="pro", help="License plan")
    parser.add_argument("--days", type=int, default=365, help="Days valid (default: 365)")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🔑 Lead Extractor Pro - License Generator")
    print("=" * 60)

    license_key = generate_license_key(
        secret=LICENSE_SECRET,
        licensee_name=args.name,
        plan=args.plan,
        days_valid=args.days,
    )

    # Decode to show details
    payload = decode_license_key(license_key)

    print(f"\n📋 License Details:")
    print(f"   Name:    {payload['licensee']}")
    print(f"   Plan:    {payload['plan'].upper()}")
    print(f"   Issued:  {payload['issued_at'][:19]}")
    print(f"   Expires: {payload['expires_at'][:19]}")

    print(f"\n🔑 License Key:")
    print(f"\n{license_key}\n")

    print(f"Add this to your .env file as:")
    print(f"LICENSE_KEY={license_key}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

