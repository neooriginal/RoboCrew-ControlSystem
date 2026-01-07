@echo off
title ARCS Remote Worker
cls
echo ==========================================
echo           ARCS Remote Worker
echo ==========================================
echo.

set LAST_URL_FILE=.last_robot_url
set DEFAULT_URL=http://192.168.1.50:5000

if exist %LAST_URL_FILE% (
    set /p SAVED_URL=<%LAST_URL_FILE%
) else (
    set SAVED_URL=
)

if "%SAVED_URL%"=="" (
    set PROMPT_MSG="Robot URL (e.g. %DEFAULT_URL%): "
) else (
    set PROMPT_MSG="Robot URL [Enter for %SAVED_URL%]: "
)

set /p ROBOT_URL=%PROMPT_MSG%

if "%ROBOT_URL%"=="" set ROBOT_URL=%SAVED_URL%
if "%ROBOT_URL%"=="" set ROBOT_URL=%DEFAULT_URL%

:: Remove all spaces from URL
set ROBOT_URL=%ROBOT_URL: =%

echo %ROBOT_URL%>%LAST_URL_FILE%
echo.

echo [1/3] Installing/Updating dependencies...
pip install --upgrade lerobot requests huggingface_hub -q

echo.
echo [2/3] Checking HuggingFace Login...
python -m huggingface_hub.commands.huggingface_cli whoami >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Login required. Please paste your token below:
    python -m huggingface_hub.commands.huggingface_cli login
) else (
    echo Already logged in.
)
echo.

echo [3/3] Starting worker...
echo.

:loop
python -c "import requests; exec(requests.get('%ROBOT_URL%/static/worker.py').text)" %ROBOT_URL%
timeout /t 5 /nobreak >nul
goto loop
