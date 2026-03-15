#!/bin/bash
# Create a CLEAN Windows zip for distribution to customers.
# Excludes: .env (your keys), data/ (your DB with license), exports/ (your data)
# Result: Customer must activate with their own license key.

set -e
cd "$(dirname "$0")"

OUTPUT="lead-extractor-windows-customer.zip"
echo "📦 Creating customer distribution zip (license required)..."
echo "   Excluding: .env, data/, exports/, __pycache__, .git"
echo ""

# Remove old zip if exists
rm -f "$OUTPUT"

zip -r "$OUTPUT" . \
  -x "*.pyc" \
  -x "*__pycache__*" \
  -x ".git/*" \
  -x "dist/*" \
  -x "build/*" \
  -x "*.egg-info/*" \
  -x ".env" \
  -x "data/*" \
  -x "exports/*" \
  -x "*.db" \
  -x "*.db-wal" \
  -x "*.db-shm" \
  -x "*.log" \
  -x ".cursor/*" \
  -x "node_modules/*" \
  -x "*.spec" \
  -x "LeadExtractorPro*.zip" \
  -x "lead-extractor-windows*.zip" \
  -x "lead-extractor-windows-customer.zip" \
  -x "package_windows_for_customers.sh"

echo ""
echo "✅ Created: $OUTPUT"
echo ""
echo "📋 Customer flow:"
echo "   1. Install Python 3.9+ from python.org (check 'Add to PATH')"
echo "   2. Unzip this folder on Windows"
echo "   3. Double-click SETUP_AND_RUN.bat (first run installs everything, ~2-5 min)"
echo "   4. License activation dialog will appear"
echo "   5. Customer sends Hardware ID → you generate license → they activate"
echo ""
