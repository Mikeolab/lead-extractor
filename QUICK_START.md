# ⚡ Quick Start Guide

## 🚀 Start the Application (One Command!)

**Everything starts together automatically:**

```bash
./start_desktop.sh
```

This will:
1. ✅ Start the automation server (port 8000)
2. ✅ Start the desktop UI (port 8501)
3. ✅ Open your browser automatically
4. ✅ Show connection status

**The UI will show "✅ Server Connected" when ready!**

## 📝 How to Use

1. **Wait for "✅ Server Connected"** in the sidebar
2. **Enter a query** like: `'digital twin engineers' filetype:pdf intext:@`
3. **Or enable Batch Mode** and paste multiple queries
4. **Click ▶️ Start**
5. **Watch the browser automate!** You'll see:
   - Browser window opens
   - Goes to Google
   - Types your query
   - Finds PDFs
   - **Opens each PDF**
   - **Extracts emails, phones, names**
   - **Saves to file**
   - Shows save location
   - Moves to next query

## 🛑 To Stop

Press `Ctrl+C` in the terminal, or use the **⏹️ Stop** button in the UI.

## 🔄 To Restart

```bash
./start_desktop.sh
```

## ⚠️ If Server Shows "Not Connected"

1. **Check terminal** - Make sure server started successfully
2. **Click "🔄 Check Server"** button in UI
3. **Or restart:** `./start_desktop.sh`

---

**Everything is ready to test!** 🎯

