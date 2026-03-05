#!/usr/bin/env python3
"""
Admin License Generator Tool
Generate license keys for users after they send you their Hardware ID.

Usage:
    python3 generate_license_admin.py --name "Mike" --machine-id "70998ed59f0f1577" --plan "enterprise" --days 365
"""
import argparse
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.license.generator import generate_license_key
from app.config import LICENSE_SECRET


def main():
    parser = argparse.ArgumentParser(
        description="Generate license keys for Lead Extractor Pro",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Lifetime license (permanent)
  python3 generate_license_admin.py --name "Mike" --machine-id "70998ed59f0f1577" --plan enterprise --type lifetime
  
  # Monthly subscription
  python3 generate_license_admin.py --name "John" --machine-id "abc123def456" --plan pro --type monthly
  
  # Yearly subscription
  python3 generate_license_admin.py --name "Jane" --machine-id "def456ghi789" --plan enterprise --type yearly
  
  # Custom period (6 months)
  python3 generate_license_admin.py --name "Bob" --machine-id "ghi789jkl012" --plan pro --days 180
        """
    )
    
    parser.add_argument(
        "--name",
        required=True,
        help="Licensee name (e.g., 'Mike', 'John Doe')"
    )
    
    parser.add_argument(
        "--machine-id",
        required=True,
        help="Hardware ID from user's computer (16-char hex, e.g., '70998ed59f0f1577')"
    )
    
    parser.add_argument(
        "--plan",
        choices=["free", "pro", "enterprise"],
        default="pro",
        help="License plan (default: pro)"
    )
    
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Number of days license is valid (custom period)"
    )
    
    parser.add_argument(
        "--type",
        choices=["lifetime", "monthly", "yearly", "quarterly", "semiannual"],
        default=None,
        help="Preset license type (lifetime, monthly, yearly, quarterly, semiannual)"
    )
    
    args = parser.parse_args()
    
    # Determine validity period
    if args.type:
        # Preset types
        validity_map = {
            "lifetime": 36500,      # 100 years (effectively permanent)
            "monthly": 30,          # 1 month
            "quarterly": 90,        # 3 months
            "semiannual": 180,      # 6 months
            "yearly": 365,          # 1 year
        }
        days_valid = validity_map[args.type]
        validity_description = args.type.upper()
    elif args.days:
        # Custom days
        days_valid = args.days
        validity_description = f"{args.days} days"
    else:
        # Default to yearly if nothing specified
        days_valid = 365
        validity_description = "1 year (default)"
    
    # Validate machine ID format
    machine_id = args.machine_id.replace("-", "").replace(" ", "").lower()
    if len(machine_id) != 16 or not all(c in '0123456789abcdef' for c in machine_id):
        print(f"❌ Error: Invalid machine ID format. Expected 16-character hex string.")
        print(f"   Received: {args.machine_id}")
        print(f"   Example: 70998ed59f0f1577")
        sys.exit(1)
    
    # Generate license key
    try:
        license_key = generate_license_key(
            secret=LICENSE_SECRET,
            licensee_name=args.name,
            machine_id=machine_id,
            plan=args.plan,
            days_valid=days_valid
        )
        
        print("\n" + "="*60)
        print("✅ LICENSE KEY GENERATED")
        print("="*60)
        print(f"\nLicensee: {args.name}")
        print(f"Plan: {args.plan.upper()}")
        print(f"Machine ID: {machine_id}")
        print(f"Validity: {validity_description}")
        if args.type == "lifetime":
            print(f"   (Effectively permanent - 100 years)")
        elif args.type:
            print(f"   ({days_valid} days)")
        else:
            print(f"   ({days_valid} days)")
        print(f"\nLicense Key:")
        print("-"*60)
        print(license_key)
        print("-"*60)
        print("\n📧 Send this license key to the user via email.")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"❌ Error generating license: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

