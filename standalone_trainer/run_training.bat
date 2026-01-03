@echo off
setlocal
title RoboCrew VLA Trainer

echo ===================================================
echo       RoboCrew VLA Standalone Trainer
echo ===================================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b
)

:: 2. Setup/Install Requirements
echo [1/3] Checking dependencies...
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt
echo.

:: 3. Select Dataset
echo [2/3] Dataset Selection
echo Please drag and drop your dataset ZIP file here and press Enter:
set /p DATASET_PATH="> "

:: Remove quotes if present
set DATASET_PATH=%DATASET_PATH:"=%

:: Remove trailing backslash if present (common drag-drop issue for folders)
if "%DATASET_PATH:~-1%"=="\" set DATASET_PATH=%DATASET_PATH:~0,-1%

:: Check if file exists (using quotes to handle spaces)
if not exist "%DATASET_PATH%" (
    echo [ERROR] File not found: "%DATASET_PATH%"
    pause
    exit /b
)

:: 4. Model Name
echo.
echo [3/3] Configuration
set /p MODEL_NAME="Enter a name for your model (e.g., pick_cup_v1): "
if "%MODEL_NAME%"=="" set MODEL_NAME=my_policy

set /p EPOCHS="Enter number of epochs [default: 50]: "
if "%EPOCHS%"=="" set EPOCHS=50

:: 5. Train
echo.
echo Starting training...
echo Dataset: %DATASET_PATH%
echo Model:   %MODEL_NAME%
echo Epochs:  %EPOCHS%
echo.

python train.py --dataset "%DATASET_PATH%" --model_name "%MODEL_NAME%" --epochs %EPOCHS%

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Training failed.
) else (
    echo.
    echo ===================================================
    echo Training Complete! 
    echo Your model is in the 'models' folder.
    echo Please upload '%MODEL_NAME%_ep%EPOCHS%.pth' to the Robot UI.
    echo ===================================================
)

pause
