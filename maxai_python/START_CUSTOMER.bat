@echo off
title CroixAI
color 0B

:: Prüfe ob als Admin
net session >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Starte neu als Administrator...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

echo.
echo  ========================================================
echo    CroixAI  —  Target Tracker
echo    Web-UI: http://127.0.0.1:17384
echo  ========================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  [FEHLER] Python nicht gefunden!
    echo  Bitte INSTALL.bat zuerst ausführen.
    pause & exit /b 1
)

python main_customer.py %*

if errorlevel 1 (
    echo.
    echo  [FEHLER] CroixAI abgestürzt — logs\croixai.log prüfen.
    pause
)
