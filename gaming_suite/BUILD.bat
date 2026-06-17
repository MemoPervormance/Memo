@echo off
title INFINITY HUB — Build System
color 0B

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║       INFINITY HUB BUILD SYSTEM             ║
echo  ║       Gaming Optimization Suite             ║
echo  ╚══════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: Install dependencies
echo [1/4] Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: pip install failed.
    pause
    exit /b 1
)

echo [2/4] Cleaning previous build...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "*.spec" del /q *.spec

echo [3/4] Building EXE (INFINITY HUB - All-In-One)...
pyinstaller ^
    --name "InfinityHub" ^
    --onefile ^
    --windowed ^
    --icon=assets/icons/icon.ico ^
    --add-data "assets;assets" ^
    --hidden-import "PyQt6.QtWidgets" ^
    --hidden-import "PyQt6.QtGui" ^
    --hidden-import "PyQt6.QtCore" ^
    --hidden-import "psutil" ^
    main.py

if errorlevel 1 (
    echo ERROR: Build failed.
    pause
    exit /b 1
)

echo [4/4] Done!
echo.
echo  ✓ Output: dist\InfinityHub.exe
echo.

pause
