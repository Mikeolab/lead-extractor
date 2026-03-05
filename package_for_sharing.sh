#!/bin/bash
# Package app for sharing with Mac users

set -e

APP_PATH="dist/LeadExtractorPro.app"
SHARE_DIR="dist/share"

echo "📦 Packaging app for sharing..."

# Check if app exists
if [ ! -d "$APP_PATH" ]; then
    echo "❌ App not found at $APP_PATH"
    echo "   Run ./build_macos.sh first"
    exit 1
fi

mkdir -p "$SHARE_DIR"

# Create ZIP
echo "📦 Creating ZIP file..."
cd dist
zip -r share/LeadExtractorPro_Mac.zip LeadExtractorPro.app
cd ..

# Create DMG
echo "📦 Creating DMG installer..."
hdiutil create -volname "Lead Extractor Pro" \
    -srcfolder "$APP_PATH" \
    -ov -format UDZO \
    "$SHARE_DIR/LeadExtractorPro_Mac.dmg" 2>/dev/null || {
    echo "⚠️  DMG creation failed (may need to be run manually)"
}

echo ""
echo "✅ Packaging complete!"
echo ""
echo "📦 Files created in: $SHARE_DIR"
ls -lh "$SHARE_DIR"
echo ""
echo "📤 Ready to share:"
echo "   - ZIP: $SHARE_DIR/LeadExtractorPro_Mac.zip"
echo "   - DMG: $SHARE_DIR/LeadExtractorPro_Mac.dmg (if created)"
echo ""
echo "💡 Send either file to Mac users!"

