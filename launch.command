#!/bin/bash
# Lead Extractor Pro - One-Click Launcher
# Double-click this file to start the app

cd "$(dirname "$0")"

echo "🎯 Starting Lead Extractor Pro..."
echo ""

# Kill any existing instance
lsof -ti:8501 | xargs kill -9 2>/dev/null
sleep 1

# Start Streamlit
python3 -m streamlit run app/main.py \
    --server.headless true \
    --server.port 8501 \
    --browser.gatherUsageStats false &

# Wait for server to start
sleep 3

# Open in browser
open http://localhost:8501

echo "✅ App is running at http://localhost:8501"
echo "Press Ctrl+C to stop."

# Keep window open
wait

