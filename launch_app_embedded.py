#!/usr/bin/env python3
"""
Embedded launcher - starts FastAPI server + Streamlit
Works standalone without external server
"""
import sys
import os
import threading
import time
import fcntl
from pathlib import Path

# Determine paths
if getattr(sys, 'frozen', False):
    # Bundled app - PyInstaller
    base_path = Path(sys._MEIPASS)
    app_path = base_path / "app"
    main_script = app_path / "main.py"
else:
    # Development mode
    base_path = Path(__file__).parent
    app_path = base_path / "app"
    main_script = app_path / "main.py"

# Add to path
sys.path.insert(0, str(base_path))

# Lock file to prevent multiple instances
LOCK_FILE = Path.home() / "Library" / "Application Support" / "LeadExtractorPro" / ".app_lock"

def acquire_lock():
    """Acquire lock file to prevent multiple instances"""
    try:
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Check if lock file exists and process is still running
        if LOCK_FILE.exists():
            try:
                with open(LOCK_FILE, 'r') as f:
                    pid = int(f.read().strip())
                # Check if process is still running
                try:
                    os.kill(pid, 0)  # Signal 0 just checks if process exists
                    # Process exists, another instance is running
                    return None
                except (OSError, ProcessLookupError):
                    # Process doesn't exist, remove stale lock
                    LOCK_FILE.unlink()
            except (ValueError, FileNotFoundError):
                # Invalid lock file, remove it
                if LOCK_FILE.exists():
                    LOCK_FILE.unlink()
        
        # Create new lock file
        lock_fd = open(LOCK_FILE, 'w')
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock_fd.write(str(os.getpid()))
            lock_fd.flush()
            return lock_fd
        except (IOError, OSError):
            # Another instance is running
            lock_fd.close()
            return None
    except Exception as e:
        # If lock fails, log but don't block (for debugging)
        try:
            error_log = Path.home() / "Library" / "Application Support" / "LeadExtractorPro" / "error.log"
            error_log.parent.mkdir(parents=True, exist_ok=True)
            with open(error_log, "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Lock error: {e}\n")
        except:
            pass
        return None

def release_lock(lock_fd):
    """Release lock file"""
    try:
        if lock_fd:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
            if LOCK_FILE.exists():
                LOCK_FILE.unlink()
    except Exception:
        pass

def find_free_port(start_port=8000, max_attempts=10):
    """Find a free port starting from start_port"""
    import socket
    for i in range(max_attempts):
        port = start_port + i
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            result = sock.bind(('127.0.0.1', port))
            sock.close()
            return port
        except (OSError, socket.error) as e:
            sock.close()
            continue
    # If all ports are taken, just return the starting port and let the app handle it
    return start_port

def start_fastapi_server():
    """Start FastAPI server in background thread"""
    try:
        import socket
        import uvicorn
        from app.server.automation_server import app as fastapi_app
        
        # Check if port 8000 is already in use
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port_8000_in_use = sock.connect_ex(('127.0.0.1', 8000)) == 0
        sock.close()
        
        if port_8000_in_use:
            # Server already running, that's fine
            return True
        
        # Find free port if 8000 is taken
        port = find_free_port(8000)
        
        # Run server in background
        config = uvicorn.Config(
            fastapi_app,
            host="127.0.0.1",
            port=port,
            log_level="error",  # Minimal logging
        )
        server = uvicorn.Server(config)
        
        # Run in thread
        def run_server():
            try:
                server.run()
            except Exception:
                pass  # Ignore all errors in background thread
        
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        
        # Wait for server to start
        time.sleep(1)
        
        return True
    except Exception:
        return False  # Fail silently, app can work without FastAPI

def run_streamlit_in_thread(port, browser_opened_flag):
    """Run Streamlit in a background thread"""
    import subprocess
    import webbrowser
    import socket
    
    error_log_path = None
    try:
        # Setup error log path
        error_log_path = Path.home() / "Library" / "Application Support" / "LeadExtractorPro" / "error.log"
        error_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        streamlit_cmd = [
            sys.executable, "-m", "streamlit", "run", str(main_script),
            f"--server.port={port}",
            "--server.address=localhost",
            "--browser.gatherUsageStats=false",
            "--server.headless=true",
            "--global.developmentMode=false",
            "--server.runOnSave=false",
            "--server.fileWatcherType=none",
            "--server.enableCORS=false",
            "--server.enableXsrfProtection=false",
            "--server.headless=true",
            "--browser.serverAddress=localhost",
            "--browser.serverPort={}".format(port),
        ]
        
        # Disable Streamlit's auto-browser opening via environment variable
        env = os.environ.copy()
        env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
        env["STREAMLIT_SERVER_HEADLESS"] = "true"
        
        # Run Streamlit - redirect stderr to log file for debugging
        stderr_file = None
        try:
            stderr_file = open(error_log_path.parent / "streamlit_stderr.log", "a")
        except:
            pass
        
        process = subprocess.Popen(
            streamlit_cmd,
            stdout=subprocess.PIPE,
            stderr=stderr_file if stderr_file else subprocess.PIPE,
            cwd=str(base_path),
            env=env,
        )
        
        # Wait for server to be ready (check if port is listening)
        max_wait = 30  # 30 seconds max
        waited = 0
        server_ready = False
        
        while waited < max_wait and not server_ready:
            time.sleep(1)
            waited += 1
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                if result == 0:
                    server_ready = True
                    break
            except:
                pass
        
        # Only open browser once if server is ready and we haven't opened it yet
        if server_ready and not browser_opened_flag[0]:
            browser_opened_flag[0] = True
            try:
                webbrowser.open(f"http://localhost:{port}")
            except Exception as e:
                with open(error_log_path, "a") as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Browser open error: {e}\n")
        
        # Wait for process
        process.wait()
    except Exception as e:
        # Log error to file for debugging
        try:
            if error_log_path:
                with open(error_log_path, "a") as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Streamlit thread error: {e}\n")
                    import traceback
                    f.write(traceback.format_exc())
        except:
            pass

def kill_existing_instances():
    """Kill any existing LeadExtractorPro processes"""
    try:
        import subprocess
        # Kill any existing processes
        subprocess.run(
            ["pkill", "-9", "-f", "LeadExtractorPro"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(1)  # Wait for processes to die
    except Exception:
        pass

def main():
    """Main launcher - keeps main thread alive for GUI app"""
    # Kill any existing instances first
    if getattr(sys, 'frozen', False):
        kill_existing_instances()
    
    # Acquire lock to prevent multiple instances
    lock_fd = acquire_lock()
    if lock_fd is None:
        # Another instance is already running - exit silently
        # Don't log this as it's expected behavior
        sys.exit(0)
    
    error_log_path = None
    try:
        # Setup error log
        error_log_path = Path.home() / "Library" / "Application Support" / "LeadExtractorPro" / "error.log"
        error_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Test imports first
        try:
            import streamlit
            from streamlit.web import cli as stcli
        except ImportError as e:
            # Log error
            try:
                with open(error_log_path, "a") as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Import error: {e}\n")
                    import traceback
                    f.write(traceback.format_exc())
            except:
                pass
            release_lock(lock_fd)
            sys.exit(1)
        
        # Start FastAPI server first (non-blocking)
        try:
            start_fastapi_server()
        except Exception as e:
            try:
                with open(error_log_path, "a") as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - FastAPI start error: {e}\n")
            except:
                pass
        
        # Find free port for Streamlit
        streamlit_port = find_free_port(8501)
        if streamlit_port is None:
            streamlit_port = 8501
        
        # For GUI apps, run Streamlit in a background thread
        # and keep main thread alive
        if getattr(sys, 'frozen', False):
            # Flag to ensure browser only opens once
            browser_opened_flag = [False]
            
            # Running as bundled app - use thread to avoid blocking
            streamlit_thread = threading.Thread(
                target=run_streamlit_in_thread,
                args=(streamlit_port, browser_opened_flag),
                daemon=False  # Keep thread alive
            )
            streamlit_thread.start()
            
            # Log startup
            try:
                with open(error_log_path, "a") as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - App started, Streamlit thread launched on port {streamlit_port}\n")
            except:
                pass
            
            # Keep main thread alive (required for GUI apps)
            # Use a more responsive loop
            try:
                import signal
                # Set up signal handlers for graceful shutdown
                def signal_handler(sig, frame):
                    release_lock(lock_fd)
                    sys.exit(0)
                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGTERM, signal_handler)
            except:
                pass
            
            # Keep alive loop - check thread status
            try:
                while streamlit_thread.is_alive():
                    time.sleep(0.5)  # More responsive
                    # Check if thread is still running
                    if not streamlit_thread.is_alive():
                        break
            except KeyboardInterrupt:
                release_lock(lock_fd)
                sys.exit(0)
            except Exception as e:
                # Log any errors in the keep-alive loop
                try:
                    with open(error_log_path, "a") as f:
                        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Keep-alive error: {e}\n")
                except:
                    pass
        else:
            # Development mode - run directly
            sys.argv = [
                "streamlit", "run", str(main_script),
                f"--server.port={streamlit_port}",
                "--server.address=localhost",
                "--browser.gatherUsageStats=false",
                "--server.headless=true",
                "--global.developmentMode=false",
                "--server.runOnSave=false",
                "--server.fileWatcherType=none",
                "--server.enableCORS=false",
                "--server.enableXsrfProtection=false",
            ]
            stcli.main()
        
    except KeyboardInterrupt:
        release_lock(lock_fd)
        sys.exit(0)
    except Exception as e:
        # Log error
        try:
            if error_log_path:
                with open(error_log_path, "a") as f:
                    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Main error: {e}\n")
                    import traceback
                    f.write(traceback.format_exc())
        except:
            pass
        release_lock(lock_fd)
        sys.exit(1)
    finally:
        release_lock(lock_fd)

if __name__ == "__main__":
    main()

