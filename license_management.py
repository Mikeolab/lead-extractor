#!/usr/bin/env python3
"""
License Management Tool
View, list, and manage licenses (for future use with cloud system)
"""
import sys
from pathlib import Path
import sqlite3
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from app.config import DATABASE_PATH
from app.license.generator import decode_license_key


def list_licenses():
    """List all activated licenses in the database"""
    if not DATABASE_PATH.exists():
        print("❌ No database found. No licenses activated yet.")
        return
    
    conn = sqlite3.connect(str(DATABASE_PATH))
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='app_license'
    """)
    
    if not cursor.fetchone():
        print("❌ No license table found. No licenses activated yet.")
        conn.close()
        return
    
    # Get all licenses
    cursor.execute("""
        SELECT license_key, machine_id, activated_at, is_active
        FROM app_license
        ORDER BY activated_at DESC
    """)
    
    licenses = cursor.fetchall()
    conn.close()
    
    if not licenses:
        print("📋 No licenses found in database.")
        return
    
    print("\n" + "="*80)
    print("📋 ACTIVATED LICENSES")
    print("="*80)
    
    for idx, (license_key, machine_id, activated_at, is_active) in enumerate(licenses, 1):
        # Decode license to get details
        payload = decode_license_key(license_key)
        
        if payload:
            licensee = payload.get("licensee", "Unknown")
            plan = payload.get("plan", "Unknown")
            expires_at = payload.get("expires_at", "Unknown")
            
            # Calculate days remaining
            try:
                expiry = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                days_left = (expiry - datetime.utcnow()).days
                if days_left > 36500:
                    expiry_str = "LIFETIME"
                elif days_left > 0:
                    expiry_str = f"{days_left} days"
                else:
                    expiry_str = "EXPIRED"
            except Exception:
                expiry_str = expires_at
            
            status = "✅ Active" if is_active else "❌ Inactive"
            
            print(f"\n{idx}. {licensee} ({plan.upper()})")
            print(f"   Machine ID: {machine_id}")
            print(f"   Status: {status}")
            print(f"   Expires: {expiry_str}")
            print(f"   Activated: {activated_at}")
        else:
            print(f"\n{idx}. Invalid license (cannot decode)")
            print(f"   Machine ID: {machine_id}")
            print(f"   Status: {'✅ Active' if is_active else '❌ Inactive'}")
    
    print("\n" + "="*80 + "\n")


def show_license_info(license_key: str):
    """Show detailed information about a license key"""
    payload = decode_license_key(license_key)
    
    if not payload:
        print("❌ Invalid license key (cannot decode)")
        return
    
    print("\n" + "="*80)
    print("📋 LICENSE INFORMATION")
    print("="*80)
    print(f"\nLicensee: {payload.get('licensee', 'Unknown')}")
    print(f"Plan: {payload.get('plan', 'Unknown').upper()}")
    print(f"Machine ID: {payload.get('machine_id', 'Not set')}")
    print(f"Issued: {payload.get('issued_at', 'Unknown')}")
    print(f"Expires: {payload.get('expires_at', 'Unknown')}")
    
    # Calculate days remaining
    try:
        expires_at = payload.get('expires_at')
        if expires_at:
            expiry = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            days_left = (expiry - datetime.utcnow()).days
            if days_left > 36500:
                print(f"Status: ✅ LIFETIME (permanent)")
            elif days_left > 0:
                print(f"Status: ✅ Valid ({days_left} days remaining)")
            else:
                print(f"Status: ❌ EXPIRED ({abs(days_left)} days ago)")
    except Exception:
        pass
    
    print("="*80 + "\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="License Management Tool")
    parser.add_argument("--list", action="store_true", help="List all activated licenses")
    parser.add_argument("--info", type=str, help="Show info for a specific license key")
    
    args = parser.parse_args()
    
    if args.list:
        list_licenses()
    elif args.info:
        show_license_info(args.info)
    else:
        parser.print_help()

