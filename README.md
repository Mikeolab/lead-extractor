# 🎯 Lead Extractor Pro - Desktop Application

**Live Browser Automation Tool** - Watch your browser automate Google searches in real-time.

## 🖥️ Desktop Application (Not Web Deployment)

This is a **desktop application** that runs locally on your machine. It consists of:
- **FastAPI Server** - Runs browser automation (Playwright)
- **Streamlit UI** - Desktop interface for controlling and viewing automation

Both run on your local machine - no web hosting needed.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd /Users/mikeolab/lead-extractor
pip3 install -r requirements.txt
python3 -m playwright install chromium
```

### 2. Start the Application

**Option A: Use the startup script (recommended)**
```bash
./start_app.sh
```

**Option B: Manual start (two terminals)**

**Terminal 1 - Automation Server:**
```bash
python3 -m uvicorn app.server.automation_server:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Desktop UI:**
```bash
streamlit run app/main.py --server.port 8501
```

### 3. Open the Application

Your browser will automatically open to: **http://localhost:8501**

If not, manually navigate to: `http://localhost:8501`

## 📖 How to Use

1. **Enter Search Query**
   - Type your Google search query
   - Supports operators: `filetype:pdf`, `intext:@`, `site:`, etc.
   - Example: `'digital twin engineers' 'service' filetype:pdf intext:@ intext:Livermore, California`

2. **Batch Mode (Optional)**
   - Enable "Batch Mode"
   - Paste multiple queries (one per line)
   - Will process all queries sequentially

3. **Configure Settings**
   - **Max Pages**: How many Google result pages per query (1-20)
   - **Delay Between Pages**: Seconds to wait (prevents rate limiting)
   - **Action Delay**: Human-like delay between actions

4. **Start Automation**
   - Click **▶️ Start**
   - **Watch the browser window open and automate!**
   - You'll see it:
     - Open Google
     - Type your query
     - Search
     - Click through pages
     - Extract results
     - Move to next query

5. **View Results**
   - Live browser view (left panel) - See automation happening
   - Activity log (right panel) - Every action logged
   - Results table (bottom) - Extracted leads appear as found

## 🎬 What You'll See

### Live Browser Window
- Real browser window opens (Chrome)
- You see it navigate, type, click
- Updates in real-time as automation runs

### Activity Log
- `[HH:MM:SS] [*] Opening Google...`
- `[HH:MM:SS] [✓] Search results loaded`
- `[HH:MM:SS] [📄] Found PDF: ...`
- `[HH:MM:SS] [📄] Opening PDF: ...`
- `[HH:MM:SS] [✓] Extracted 1234 chars from PDF`
- `[HH:MM:SS] [✓] Found 5 emails, 3 phones, 2 names`
- `[HH:MM:SS] [💾] Saved to: /path/to/file.pdf`
- Every action is logged with timestamp

### Results Table
- Updates as leads are extracted from PDFs
- Shows: Email, Phone, Contact Name, Business, Website, Source URL
- Prioritizes email column (most important)
- Metrics: Total leads, emails found, phones found, names found

### Saved Files Section
- Shows all PDF files saved after each query
- Displays file path, lead count, and timestamp
- Click to expand and see full path

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Your Desktop Machine                       │
│                                                         │
│  ┌──────────────┐         WebSocket         ┌─────────┐│
│  │ Streamlit UI │ ←────────────────────────→ │ FastAPI ││
│  │  Port 8501   │   (screenshots + logs)    │ Port    ││
│  │              │                            │ 8000    ││
│  │ - Live View  │                            │         ││
│  │ - Controls   │                            │ - Play- ││
│  │ - Results    │                            │   wright││
│  └──────────────┘                            │ - Chrome││
│                                               │ - Auto  ││
│                                               └─────────┘│
└─────────────────────────────────────────────────────────┘
```

## 🔧 Technology Stack

- **Playwright** - Browser automation (faster, more reliable than Selenium)
- **FastAPI** - Modern Python web framework (WebSocket support)
- **Streamlit** - Rapid UI development (desktop app interface)
- **WebSockets** - Real-time bidirectional communication

**All open-source, no third-party services required.**

## ⚙️ Configuration

Settings are auto-saved in: `~/.lead_extractor_pro_settings.json`

- Max pages per query
- Delays (prevents rate limiting)
- Output format
- Auto-save to database

## 🐛 Troubleshooting

### "Server Not Connected"
- Make sure Terminal 1 is running: `python3 -m uvicorn app.server.automation_server:app --host 0.0.0.0 --port 8000`
- Check server: `curl http://localhost:8000/` should return JSON

### Browser Not Visible
- Browser window should pop up automatically
- If headless, change `headless=False` in `automation_server.py`

### Screenshots Not Updating
- Check WebSocket connection status in sidebar
- Refresh browser page
- Restart both servers if needed

### Port Already in Use
- Kill existing processes: `lsof -ti:8000 | xargs kill -9`
- Or change ports in startup commands

## 📝 Notes

- **Desktop Application**: Runs locally, not deployed to web
- **Visible Browser**: You'll see the actual Chrome window automating
- **Real-time**: Screenshots update as automation runs
- **Loop Support**: Processes 10-20 queries/pages automatically
- **No API Keys**: Uses free DuckDuckGo/Google search (no billing)

## 🎯 Features

✅ Live browser visualization  
✅ Real-time screenshot streaming  
✅ Multi-query batch processing  
✅ Multi-page search (up to 20 pages)  
✅ PDF detection and extraction  
✅ Activity logging  
✅ Results export (CSV/Excel/PDF)  
✅ Settings persistence  
✅ License key system  

---

**Built with ❤️ for efficient lead extraction**

