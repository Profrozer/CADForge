@echo off
cd /d "%~dp0backend"
.venv\Scripts\python -m uvicorn app.main:app --port 8000
