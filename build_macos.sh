#!/bin/bash
# Build macOS .app bundle for Lead Extractor Pro

set -e  # Exit on error

echo "🔨 Building macOS app..."

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "❌ PyInstaller not found. Installing..."
    pip3 install pyinstaller
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build dist *.spec

# Build the app
echo "📦 Building LeadExtractorPro.app..."
python3 -m PyInstaller --name=LeadExtractorPro \
    --onedir \
    --windowed \
    --osx-bundle-identifier=com.leadextractor.pro \
    --add-data="app:app" \
    --hidden-import=streamlit \
    --hidden-import=streamlit.web.cli \
    --hidden-import=streamlit.runtime.scriptrunner \
    --hidden-import=playwright \
    --hidden-import=fastapi \
    --hidden-import=uvicorn \
    --hidden-import=websocket \
    --hidden-import=sqlite3 \
    --hidden-import=pdfplumber \
    --hidden-import=httpx \
    --hidden-import=pandas \
    --hidden-import=openpyxl \
    --hidden-import=reportlab \
    --hidden-import=fpdf \
    --hidden-import=fpdf2 \
    --collect-all streamlit \
    --collect-all playwright \
    --noconfirm \
    launch_app_simple.py

# Check if build succeeded
if [ -d "dist/LeadExtractorPro.app" ]; then
    # Copy custom Info.plist for proper GUI app behavior
    if [ -f "Info.plist.template" ]; then
        echo "📝 Updating Info.plist for GUI app..."
        cp Info.plist.template dist/LeadExtractorPro.app/Contents/Info.plist
    fi
    
    echo ""
    echo "✅ Build successful!"
    echo "📦 App location: dist/LeadExtractorPro.app"
    echo ""
    echo "🧪 Testing app..."
    open dist/LeadExtractorPro.app
    
    echo ""
    echo "📋 Next steps:"
    echo "1. Test the app thoroughly"
    echo "2. Create DMG installer (optional):"
    echo "   hdiutil create -volname 'Lead Extractor Pro' -srcfolder dist/LeadExtractorPro.app -ov -format UDZO dist/LeadExtractorPro.dmg"
    echo "3. Distribute to users"
else
    echo "❌ Build failed! Check errors above."
    exit 1
fi

