#!/bin/bash
# Create a FULL Windows zip for BUILDING the .exe (includes .spec, build_windows.bat, etc.)
# Use this when you need to run build_windows.bat on a Windows machine.
# Excludes: .env, data/, exports/, build/, dist/ (recreated by build)

set -e
cd "$(dirname "$0")"

OUTPUT="lead-extractor-windows-FULL-BUILD.zip"
echo "📦 Creating FULL build zip (for build_windows.bat)..."
echo "   Includes: .spec, build_windows.bat, hook, app, requirements — excludes .env, data/, dist/, build/"
echo ""

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
  -x "LeadExtractorPro*.zip" \
  -x "lead-extractor-windows*.zip" \
  -x "lead-extractor-windows-customer.zip" \
  -x "package_windows_for_customers.sh" \
  -x "package_windows_for_build.sh"

echo ""
echo "✅ Created: $OUTPUT"
echo ""
echo "📋 To build the .exe on Windows:"
echo "   1. Unzip this folder"
echo "   2. Double-click build_windows.bat"
echo "   3. Wait 5–15 min; exe will be in dist\\LeadExtractorPro.exe"
echo ""
