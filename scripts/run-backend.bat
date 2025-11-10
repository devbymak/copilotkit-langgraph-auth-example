@echo off
cd /d "%~dp0\..\backend" || exit /b 1

REM Use venv Python if it exists, otherwise use system Python
if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
) else (
    python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
)

