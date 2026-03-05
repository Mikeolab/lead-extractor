#!/usr/bin/env python3
"""
Simple launcher - minimal approach for macOS
Based on research: Streamlit works best when run directly
"""
import sys
import os
import time
import subprocess
from pathlib import Path

# Determine paths
if getattr(sys, 'frozen', False):
    base_path = Path(sys._MEIPASS)
    app_path = base_path / "app"
    main_script = app_path / "main.py"
else:
    base_path = Path(__file__).parent
    app_path = base_path / "app"
    main_script = app_path / "main.py"

sys.path.insert(0, str(base_path))

def find_free_port(start_port=8501):
    """Find a free port"""
    import socket
    for i in range(10):
        port = start_port + i
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('127.0.0.1', port))
            sock.close()
            return port
        except:
            sock.close()
    return start_port

def main():
    """Simple launcher - just run Streamlit"""
    try:
        # Kill any existing instances
        try:
            subprocess.run(
                ["pkill", "-9", "-f", "LeadExtractorPro"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2
            )
            time.sleep(1)
        except:
            pass
        
        # Find port
        port = find_free_port(8501)
        
        # Start FastAPI in background (optional)
        try:
            import uvicorn
            from app.server.automation_server import app as fastapi_app
            import threading
            
            def run_fastapi():
                try:
                    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="error")
                except:
                    pass
            
            fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
            fastapi_thread.start()
            time.sleep(0.5)
        except:
            pass
        
        # Run Streamlit directly - this is the key: run it normally
        # Don't try to wrap it in threads or subprocesses
        import streamlit.web.cli as stcli
        
        # Set up Streamlit args
        sys.argv = [
            "streamlit",
            "run",
            str(main_script),
            f"--server.port={port}",
            "--server.address=localhost",
            "--browser.gatherUsageStats=false",
            "--server.headless=true",
            "--global.developmentMode=false",
            "--server.runOnSave=false",
            "--server.fileWatcherType=none",
            "--server.enableCORS=false",
            "--server.enableXsrfProtection=false",
        ]
        
        # Set environment to prevent auto-browser
        os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
        os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
        
        # Run Streamlit - this blocks until app closes
        stcli.main()
        
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        # Log error
        try:
            error_log = Path.home() / "Library" / "Application Support" / "LeadExtractorPro" / "error.log"
            error_log.parent.mkdir(parents=True, exist_ok=True)
            with open(error_log, "a") as f:
                import traceback
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Error: {e}\n")
                f.write(traceback.format_exc())
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
