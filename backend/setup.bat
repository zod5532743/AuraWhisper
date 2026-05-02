@echo off
cd /d "%~dp0"
if exist "resources\app\backend\requirements.txt" cd /d "resources\app\backend"
if exist "backend\requirements.txt" cd /d "backend"
echo.
echo Current directory: %CD%
if not exist requirements-base.txt (
    echo [ERROR] requirements-base.txt not found! 
    echo Please make sure this script is near the backend folder.
    pause
    exit /b
)
echo Installing AuraWhisper Backend Base Dependencies...
rem python -m pip install --upgrade pip
python -m pip install -r requirements-base.txt

echo Checking for NVIDIA GPU...
nvidia-smi >nul 2>&1
if %errorlevel% == 0 (
    echo NVIDIA GPU detected. Installing GPU-specific libraries...
    python -m pip install -r requirements-gpu.txt
) else (
    echo NVIDIA GPU not detected or driver not installed. Skipping GPU libraries.
)
echo.
echo Setup Complete! You can now close this window and start AuraWhisper.
pause
