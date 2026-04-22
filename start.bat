@echo off
cd /d %~dp0

echo Starting AuraWhisper Backend...
start /B "" "backend\venv\Scripts\python.exe" backend\server.py
timeout /t 5
echo Starting AuraWhisper Frontend...
npm start
