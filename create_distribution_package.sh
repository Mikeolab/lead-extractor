#!/bin/bash
# Create distribution package for Windows users

set -e

echo "📦 Creating Windows Distribution Package..."

# Check if .exe exists (if built on Windows)
if [ ! -f "dist/LeadExtractorPro.exe" ]; then
    echo "⚠️  LeadExtractorPro.exe not found in dist/"
    echo "   Note: Windows .exe must be built on a Windows machine"
    echo "   Run: build_windows.bat (on Windows)"
    echo ""
    echo "   For now, creating package structure..."
    mkdir -p dist/package
else
    echo "✅ Found LeadExtractorPro.exe"
    mkdir -p dist/package
    cp dist/LeadExtractorPro.exe dist/package/
fi

# Create README
cat > dist/package/README.txt << 'EOF'
Lead Extractor Pro - Installation Instructions
==============================================

INSTALLATION:
1. Extract this zip file to a folder (e.g., Desktop or Program Files)
2. Double-click LeadExtractorPro.exe to run
3. No installation required - just run the .exe file

ACTIVATION:
1. When you first run the app, you'll see an activation dialog
2. Copy your Hardware ID and send it to the administrator
3. You'll receive a license key via email
4. Enter the license key in the app to activate

SYSTEM REQUIREMENTS:
- Windows 10 or later
- Internet connection (for automation features)
- No additional software required

SUPPORT:
For support, please contact: support@yourapp.com

Version: 1.0.0
EOF

# Create zip file
cd dist/package
if command -v zip &> /dev/null; then
    zip -r ../LeadExtractorPro_Windows.zip *
    echo ""
    echo "✅ Package created: dist/LeadExtractorPro_Windows.zip"
    echo ""
    echo "📋 Package contents:"
    ls -lh
    echo ""
    echo "📤 Ready to distribute!"
    echo "   Upload to Google Drive, Dropbox, or your website"
else
    echo "⚠️  zip command not found. Package folder ready at: dist/package/"
    echo "   Manually create zip file from dist/package/"
fi

cd ../..

