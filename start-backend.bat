@echo off
REM InsureMate AI - backend (no Docker needed: uses a local SQLite file)
cd /d "%~dp0backend"
if not exist .venv ( python -m venv .venv )
call .venv\Scripts\activate.bat
pip install -r requirements.txt
set DATABASE_URL=sqlite:///./insuremate_hospital.db
set SECRET_KEY=change-this-to-any-long-random-text-1234567890
set LLM_MODEL=qwen2.5:7b-instruct
alembic upgrade head
uvicorn app.main:app --port 8000
pause
