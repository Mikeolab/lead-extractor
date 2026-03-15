#!/bin/bash
# Lead Extractor Pro - Double-click to start (runs in Terminal for proper browser display)
cd "$(dirname "$0")"

echo "🎯 Starting Lead Extractor Pro..."
echo "   (Running from Terminal so the automation browser can pop up)"
echo ""

# Kill existing instances
pkill -9 -f "launch_app_simple|streamlit run app/main.py" 2>/dev/null
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:8501 | xargs kill -9 2>/dev/null
sleep 2

# Run full app (FastAPI + Streamlit) - MUST run from Terminal for browser to show
python3 launch_app_simple.py

echo ""
echo "App closed. You can close this window."
