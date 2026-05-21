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

:: Wechsle ins Verzeichnis der .bat Datei
cd /d "%~dp0"

echo.
echo  ========================================================
echo    CroixAI  —  Target Tracker
echo    Web-UI: http://127.0.0.1:17384
echo  ========================================================
echo.

:: Python check
python --version >nul 2>&1
if errorlevel 1 (
    echo  [FEHLER] Python nicht gefunden!
    echo  Bitte INSTALL.bat zuerst ausführen.
    echo.
    pause & exit /b 1
)

:: Start
python main.py %*

if errorlevel 1 (
    echo.
    echo  [FEHLER] CroixAI ist abgestürzt.
    echo  Prüfe logs\croixai.log für Details.
    pause
)
