@echo off
REM Lead Extractor Pro — Windows launcher

cd /d "%~dp0"

echo Starting Lead Extractor Pro...
echo.

REM Start automation server in background
echo Starting Automation Server (port 8000)...
start /B python -m uvicorn app.server.automation_server:app --host 0.0.0.0 --port 8000

REM Wait for server to start
timeout /t 3 /nobreak >nul

REM Start Streamlit UI
echo Starting UI on port 8501...
echo.
echo Open http://localhost:8501 in your browser
echo.
python -m streamlit run app/main.py --server.port 8501
