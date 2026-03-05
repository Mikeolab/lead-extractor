# 🚀 Quick Start - Live Browser Automation

## Step 1: Start the Automation Server

**Terminal 1:**
```bash
cd /Users/mikeolab/lead-extractor
python3 -m uvicorn app.server.automation_server:app --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Step 2: Start Streamlit UI

**Terminal 2:**
```bash
cd /Users/mikeolab/lead-extractor
streamlit run app/main.py --server.port 8501
```

## Step 3: Open Browser

Go to: **http://localhost:8501**

## Step 4: Use It!

1. Enter a query like: `'digital twin engineers' 'service' filetype:pdf intext:@ intext:Livermore, California`
2. Or enable **Batch Mode** and paste multiple queries (one per line)
3. Click **▶️ Start**
4. **Watch the browser automate!** You'll see:
   - Browser window opens
   - Goes to Google
   - Types your query
   - Searches
   - Loops through pages
   - Extracts results
   - Moves to next query

## What You'll See

- **Left Panel**: Live browser window (updates in real-time)
- **Right Panel**: Activity log (every action logged)
- **Bottom**: Extracted leads table (updates as found)

## Troubleshooting

**"Server Not Connected" warning?**
- Make sure Terminal 1 is running the automation server
- Check: `curl http://localhost:8000/` should return JSON

**Browser not visible?**
- The browser window should pop up automatically
- If not, check that `headless=False` in `automation_server.py`

**Screenshots not updating?**
- Click the refresh button in your browser
- Or wait a moment - updates happen every 0.3 seconds

## Architecture

```
┌─────────────────┐         WebSocket          ┌──────────────────┐
│   Streamlit UI  │ ←────────────────────────→ │  FastAPI Server  │
│   (Port 8501)   │    (screenshots + logs)    │   (Port 8000)    │
│                 │                             │                  │
│  - Live View    │                             │  - Playwright    │
│  - Activity Log │                             │  - Browser Auto  │
│  - Results      │                             │  - Loop Logic    │
└─────────────────┘                             └──────────────────┘
```

## Technology

- ✅ **Playwright** - Best browser automation (faster, more reliable than Selenium)
- ✅ **FastAPI** - Modern async Python web framework
- ✅ **WebSockets** - Real-time bidirectional communication
- ✅ **Streamlit** - Fast UI development

**No third-party services needed** - Everything runs locally!

