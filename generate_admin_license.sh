#!/bin/bash
# Quick script to generate your admin license

echo "🔐 Generating Admin License..."
echo ""

# Get machine ID
MACHINE_ID=$(python3 -c "from app.license.machine_id import get_machine_id; print(get_machine_id())" 2>/dev/null)

if [ -z "$MACHINE_ID" ]; then
    echo "❌ Error: Could not get machine ID"
    exit 1
fi

echo "Your Machine ID: $MACHINE_ID"
echo ""

# Generate license (10 years)
python3 generate_license_admin.py \
    --name "Admin" \
    --machine-id "$MACHINE_ID" \
    --plan enterprise \
    --days 3650

echo ""
echo "✅ Copy the license key above and save it securely!"
echo "💡 You can use this license key in the app to activate."

