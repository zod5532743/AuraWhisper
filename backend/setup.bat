@echo off
cd /d "%~dp0"
if exist "resources\app\backend\requirements.txt" cd /d "resources\app\backend"
if exist "backend\requirements.txt" cd /d "backend"
echo.
echo Current directory: %CD%
if not exist requirements.txt (
    echo [ERROR] requirements.txt not found! 
    echo Please make sure this script is near the backend folder.
    pause
    exit /b
)
echo Installing AuraWhisper Backend Dependencies...
python -m pip install --upgrade pip

echo Checking for NVIDIA GPU...
nvidia-smi >nul 2>&1
if %errorlevel% == 0 (
    echo NVIDIA GPU detected. Installing CUDA acceleration libraries...
    python -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
) else (
    echo NVIDIA GPU not detected or driver not installed. Skipping CUDA libraries.
)

python -m pip install -r requirements.txt
echo.
echo Setup Complete! You can now close this window and start AuraWhisper.
pause
