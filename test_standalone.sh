#!/bin/bash
# Test standalone app on your Mac

set -e

echo "🧪 Testing Lead Extractor Pro Standalone App"
echo "=============================================="
echo ""

# Check if app exists
if [ ! -d "dist/LeadExtractorPro.app" ]; then
    echo "❌ App not found. Building first..."
    ./build_macos.sh
fi

echo "✅ App found: dist/LeadExtractorPro.app"
echo ""

# Create test directory
TEST_DIR="$HOME/Desktop/LeadExtractorTest"
echo "📁 Creating test directory: $TEST_DIR"
mkdir -p "$TEST_DIR"

# Copy app to test directory
echo "📦 Copying app to test directory..."
cp -r dist/LeadExtractorPro.app "$TEST_DIR/"

echo ""
echo "🧹 Cleaning previous test data (if any)..."
# Remove any existing app data
rm -rf "$HOME/Library/Application Support/LeadExtractorPro" 2>/dev/null || true
rm -rf "$HOME/.lead-extractor" 2>/dev/null || true

echo ""
echo "🚀 Launching app for testing..."
echo ""
echo "📋 Test Checklist:"
echo "   1. ✅ App launches without errors"
echo "   2. ✅ Activation dialog appears"
echo "   3. ✅ Hardware ID displays correctly"
echo "   4. ✅ Can copy Hardware ID"
echo "   5. ✅ License activation works"
echo "   6. ✅ All features work"
echo ""
echo "💡 App location: $TEST_DIR/LeadExtractorPro.app"
echo ""

# Launch app
open "$TEST_DIR/LeadExtractorPro.app"

echo "✅ App launched! Test it now."
echo ""
echo "🔍 To check for errors, open Console.app and filter for 'LeadExtractorPro'"
echo ""

