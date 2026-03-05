#!/bin/bash
# Test script to verify app launches correctly

set -e

echo "🧪 Testing Lead Extractor Pro Launch"
echo "===================================="
echo ""

# Kill any existing instances
pkill -f "streamlit.*main.py" 2>/dev/null || true
pkill -f "LeadExtractorPro" 2>/dev/null || true
sleep 2

# Check if app exists
if [ ! -d "dist/LeadExtractorPro.app" ]; then
    echo "❌ App not found. Build it first: ./build_macos.sh"
    exit 1
fi

echo "📦 App found: dist/LeadExtractorPro.app"
echo ""

# Run app in background and capture output
echo "🚀 Launching app..."
LOG_FILE="/tmp/lead_extractor_test.log"
dist/LeadExtractorPro.app/Contents/MacOS/LeadExtractorPro > "$LOG_FILE" 2>&1 &
APP_PID=$!

echo "⏳ Waiting for app to start (10 seconds)..."
sleep 10

# Check if process is still running
if ps -p $APP_PID > /dev/null 2>&1; then
    echo "✅ App process is running (PID: $APP_PID)"
else
    echo "❌ App process crashed!"
    echo ""
    echo "Error log:"
    tail -50 "$LOG_FILE"
    exit 1
fi

# Check if Streamlit server is responding
echo ""
echo "🌐 Checking Streamlit server..."
if curl -s http://localhost:8501 > /dev/null 2>&1; then
    echo "✅ Streamlit server is responding!"
    echo "✅ App is WORKING!"
    echo ""
    echo "📋 Open in browser: http://localhost:8501"
    echo ""
    echo "Press Ctrl+C to stop the app"
    
    # Wait for user interrupt
    trap "kill $APP_PID 2>/dev/null; exit" INT TERM
    wait $APP_PID
else
    echo "⚠️  Server not responding yet"
    echo "   (May need more time to start)"
    echo ""
    echo "Last 20 lines of log:"
    tail -20 "$LOG_FILE"
    kill $APP_PID 2>/dev/null || true
fi

