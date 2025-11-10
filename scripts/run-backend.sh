#!/bin/bash

cd "$(dirname "$0")/../backend" || exit 1

# Use venv Python if it exists, otherwise use system Python
if [ -f ".venv/bin/python" ]; then
    .venv/bin/python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
elif [ -f ".venv/Scripts/python.exe" ]; then
    .venv/Scripts/python.exe -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
else
    python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
fi

