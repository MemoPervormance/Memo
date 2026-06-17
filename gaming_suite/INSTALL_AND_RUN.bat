@echo off
title INFINITY HUB — Quick Start
color 0B

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║        INFINITY HUB — QUICK START           ║
echo  ╚══════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

echo Installing dependencies...
pip install PyQt6 psutil --quiet

echo.
echo Starting INFINITY HUB...
python main.py
