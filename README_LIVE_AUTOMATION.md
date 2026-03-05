# 🎯 Lead Extractor Pro - Live Browser Automation

## Architecture

**Two-Server Setup:**
1. **FastAPI WebSocket Server** (port 8000) - Runs Playwright browser automation
2. **Streamlit UI** (port 8501) - Displays live browser screenshots and controls

## How It Works

1. **Browser Opens** → Playwright launches Chrome (visible window)
2. **Goes to Google** → Navigates to google.com
3. **Searches Query** → Types your query and presses Enter
4. **Extracts Results** → Loops through pages (up to 10-20)
5. **Closes & Repeats** → Moves to next query, repeats process
6. **Live Visualization** → Screenshots streamed to Streamlit in real-time

## Setup

### 1. Install Dependencies
```bash
pip3 install -r requirements.txt
python3 -m playwright install chromium
```

### 2. Start Automation Server
```bash
# Terminal 1
./start_server.sh
# OR
python3 -m uvicorn app.server.automation_server:app --host 0.0.0.0 --port 8000
```

### 3. Start Streamlit UI
```bash
# Terminal 2
streamlit run app/main.py --server.port 8501
```

### 4. Open Browser
Go to: **http://localhost:8501**

## Usage

1. **Enter Query** - Type your Google search query (supports operators like `filetype:pdf`)
2. **Or Batch Mode** - Enter multiple queries (one per line)
3. **Configure Settings** - Max pages, delays, etc.
4. **Click ▶️ Start** - Watch the browser automate in real-time!
5. **Live View** - See the browser window, clicks, navigation happening live

## Features

✅ **Live Browser Visualization** - See the actual browser window automating  
✅ **Real-time Screenshots** - Updates as browser navigates  
✅ **Loop Through Queries** - Processes 10-20 queries automatically  
✅ **Multi-page Search** - Goes through multiple Google result pages  
✅ **PDF Detection** - Identifies PDF results automatically  
✅ **Activity Log** - See every action in real-time  

## Technology Stack

- **Playwright** - Browser automation (better than Selenium)
- **FastAPI** - WebSocket server for real-time communication
- **Streamlit** - UI for displaying live screenshots
- **WebSockets** - Real-time data streaming

## Why This Architecture?

✅ **Professional** - Same approach as BrowserStack, Selenium Grid  
✅ **Real-time** - True live updates (not polling)  
✅ **Scalable** - Can handle multiple concurrent sessions  
✅ **Cross-platform** - Works on macOS, Linux, Windows  

## Troubleshooting

**Server not connecting?**
- Make sure automation server is running on port 8000
- Check: `curl http://localhost:8000/`

**Browser not visible?**
- Set `headless=False` in automation_server.py
- Make sure you have a display (not SSH without X11)

**Screenshots not updating?**
- Check WebSocket connection status in sidebar
- Restart both servers if needed

