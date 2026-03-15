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
    """Simple launcher - just run Streamlit. On Windows, use launch_app_windows.py instead."""
    # On Windows, delegate to the Windows launcher (handles taskkill, different paths, etc.)
    if sys.platform == "win32":
        try:
            launch_windows = base_path / "launch_app_windows.py"
            if launch_windows.exists():
                os.execv(sys.executable, [sys.executable, str(launch_windows)] + sys.argv[1:])
        except Exception:
            pass
        # Fall through if execv fails
    try:
        # Kill any existing instances (macOS/Unix only - pkill, lsof)
        if sys.platform != "win32":
            try:
                subprocess.run(
                    ["pkill", "-9", "-f", "launch_app_simple|streamlit run app/main.py|LeadExtractorPro"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2
                )
                for p in [8000, 8501]:
                    try:
                        subprocess.run(f"lsof -ti:{p} | xargs kill -9 2>/dev/null", shell=True, timeout=2)
                    except Exception:
                        pass
                time.sleep(2)
            except Exception:
                pass
        
        # Find port
        port = find_free_port(8501)
        
        # Start FastAPI in SUBPROCESS (not thread) - required on macOS for Chrome window to pop up.
        # Threads can lose display access; a subprocess inherits it properly from Terminal.
        fastapi_proc = None
        fastapi_ok = False
        try:
            fastapi_proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.server.automation_server:app",
                 "--host", "127.0.0.1", "--port", "8000"],
                cwd=str(base_path),
                env={**os.environ, "PYTHONPATH": str(base_path)},
                stdout=None,
                stderr=None,
            )
            # Wait for uvicorn to bind to port 8000
            for _ in range(15):
                time.sleep(0.5)
                try:
                    import socket
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.5)
                    result = s.connect_ex(("127.0.0.1", 8000))
                    s.close()
                    if result == 0:
                        fastapi_ok = True
                        print("[FastAPI] Backend ready on http://localhost:8000")
                        break
                except Exception:
                    pass
            if not fastapi_ok:
                print("[FastAPI] Backend may still be starting - check Server status in UI")
        except Exception as e:
            print(f"[FastAPI] Failed to start backend: {e}", file=sys.stderr, flush=True)
            print("  → Server Not Connected in UI. Fix the error above and restart.", file=sys.stderr)
        
        try:
            # Run Streamlit directly - this is the key: run it normally
            import streamlit.web.cli as stcli
            
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
            os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
            os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
            stcli.main()
        finally:
            if fastapi_proc and fastapi_proc.poll() is None:
                fastapi_proc.terminate()
                fastapi_proc.wait(timeout=5)
        
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        # Log error (platform-specific path)
        try:
            if sys.platform == "win32":
                error_log = Path(os.environ.get("APPDATA", Path.home())) / "LeadExtractorPro" / "error.log"
            elif sys.platform == "darwin":
                error_log = Path.home() / "Library" / "Application Support" / "LeadExtractorPro" / "error.log"
            else:
                error_log = Path.home() / ".local" / "share" / "LeadExtractorPro" / "error.log"
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
