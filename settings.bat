@echo off
setlocal
cd /d "%~dp0"

:: Start backend in a hidden-ish way if not already running (optional, but settings need it)
:: We'll use a simple check or just try starting it.
start /b "" cmd /c "backend\venv\Scripts\python.exe backend\server.py"

:: Give it a second to start
timeout /t 2 /nobreak >nul

:: Launch Electron with --settings flag
npx electron . --settings

exit
