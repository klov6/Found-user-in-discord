@echo off
title Discord Username Sniper v2
echo Checking environment...

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found! Please install Python from https://python.org
    pause
    exit /b 1
)

:: Check required packages
echo Installing / verifying required packages...
python -m pip install --quiet --upgrade PyQt6 requests

:: Launch the sniper
echo Starting Discord Username Sniper v2...
python sniper_v2.py
if %errorlevel% neq 0 (
    echo The script crashed or was closed unexpectedly.
    pause
) else (
    echo Sniper closed.
)
exit /b 0