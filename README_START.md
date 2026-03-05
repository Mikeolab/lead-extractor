# 🚀 How to Start the Application

## ✅ One-Command Startup (Recommended)

```bash
./start_desktop.sh
```

**That's it!** Everything starts together:
- ✅ Automation server (port 8000)
- ✅ Desktop UI (port 8501)
- ✅ Browser opens automatically
- ✅ Connection status shown in UI

## 📋 What Happens

1. **Checks dependencies** - Installs if needed
2. **Cleans up** - Kills any old processes
3. **Starts server** - Waits until ready
4. **Starts UI** - Opens in browser
5. **Shows status** - "✅ Server Connected" when ready

## 🎯 After Startup

1. **Wait for "✅ Server Connected"** in sidebar
2. **Enter your search query**
3. **Click ▶️ Start**
4. **Watch it work!**

## 🛑 To Stop

Press `Ctrl+C` in terminal

## ⚠️ Troubleshooting

**If "Server Not Connected":**
- Check terminal for errors
- Click "🔄 Check Server" button
- Restart: `./start_desktop.sh`

**If port already in use:**
- Script auto-kills old processes
- Or manually: `lsof -ti:8000 | xargs kill -9`

---

**Ready to extract leads!** 🎯

