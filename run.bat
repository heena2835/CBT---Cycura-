@echo off
REM Helper to run python scripts using the project's virtual environment
REM Usage: run.bat path/to/script.py [args]

if "%~1"=="" (
    echo Usage: run.bat path/to/script.py
    exit /b 1
)

.venv\Scripts\python.exe %*
