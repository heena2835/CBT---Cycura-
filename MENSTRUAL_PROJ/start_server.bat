@echo off
echo Starting Cycura Backend Server...
start "" "http://localhost:5000"
.venv\Scripts\python.exe -m uvicorn backend.api:app --reload --port 5000
pause
