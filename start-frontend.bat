@echo off
REM InsureMate AI - frontend
cd /d "%~dp0frontend"
call npm install
call npm run dev
pause
