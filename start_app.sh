#!/bin/bash
# Start Lead Extractor Pro Desktop Application
# Starts both the automation server and Streamlit UI

cd "$(dirname "$0")"

echo "🎯 Starting Lead Extractor Pro Desktop Application..."
echo ""

# Check if ports are in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️  Port 8000 already in use. Killing existing process..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null
    sleep 1
fi

if lsof -Pi :8501 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️  Port 8501 already in use. Killing existing process..."
    lsof -ti:8501 | xargs kill -9 2>/dev/null
    sleep 1
fi

# Start automation server in background
echo "🚀 Starting Automation Server (port 8000)..."
python3 -m uvicorn app.server.automation_server:app --host 0.0.0.0 --port 8000 > /tmp/lead_extractor_server.log 2>&1 &
SERVER_PID=$!

# Wait for server to be ready (check every 0.5s for up to 10s)
echo "⏳ Waiting for server to start..."
for i in {1..20}; do
    sleep 0.5
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        echo "✅ Automation Server is ready (PID: $SERVER_PID)"
        break
    fi
    if [ $i -eq 20 ]; then
        echo "❌ Server failed to start after 10 seconds"
        echo "📋 Check logs: /tmp/lead_extractor_server.log"
        cat /tmp/lead_extractor_server.log
        exit 1
    fi
done

echo ""

# Start Streamlit UI
echo "🚀 Starting Desktop UI (port 8501)..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Application starting..."
echo "  📱 Open: http://localhost:8501"
echo "  🛑 Press Ctrl+C to stop"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start Streamlit (foreground)
python3 -m streamlit run app/main.py --server.port 8501 --server.headless true

# Cleanup on exit
echo ""
echo "🛑 Shutting down..."
kill $SERVER_PID 2>/dev/null
echo "✅ Done"

