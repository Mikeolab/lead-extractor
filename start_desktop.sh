#!/bin/bash
# Desktop Application Launcher - Starts everything together
# This is the main entry point for the desktop application

cd "$(dirname "$0")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🎯 Lead Extractor Pro - Desktop Application"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.9+"
    exit 1
fi

# Check dependencies
echo "📦 Checking dependencies..."
if ! python3 -c "import streamlit, fastapi, playwright" 2>/dev/null; then
    echo "⚠️  Missing dependencies. Installing..."
    pip3 install -r requirements.txt
fi

# Kill existing processes
echo "🧹 Cleaning up existing processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:8501 | xargs kill -9 2>/dev/null
sleep 1

# Start automation server
echo "🚀 Starting Automation Server..."
python3 -m uvicorn app.server.automation_server:app --host 0.0.0.0 --port 8000 > /tmp/lead_extractor_server.log 2>&1 &
SERVER_PID=$!

# Wait for server to be ready
echo "⏳ Waiting for server..."
for i in {1..20}; do
    sleep 0.5
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo "✅ Server ready!"
        break
    fi
    if [ $i -eq 20 ]; then
        echo "❌ Server failed to start"
        cat /tmp/lead_extractor_server.log
        exit 1
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Application Ready!"
echo "  📱 Opening browser: http://localhost:8501"
echo "  🛑 Press Ctrl+C to stop"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Open browser automatically (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    sleep 2
    open http://localhost:8501 2>/dev/null &
fi

# Start Streamlit (foreground - this blocks)
python3 -m streamlit run app/main.py --server.port 8501 --server.headless true

# Cleanup on exit
echo ""
echo "🛑 Shutting down..."
kill $SERVER_PID 2>/dev/null
echo "✅ Done"

