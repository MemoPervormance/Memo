@echo off
title CroixAI — Installation
color 0A
echo.
echo  =========================================================
echo    CroixAI — Abhängigkeiten installieren
echo  =========================================================
echo.

:: Check Python
echo  [1/5] Prüfe Python...
python --version 2>nul
if errorlevel 1 (
    echo.
    echo  [FEHLER] Python nicht gefunden!
    echo  Bitte Python 3.11+ von https://python.org installieren.
    echo  Wichtig: "Add Python to PATH" anhaken beim Installieren!
    echo.
    pause & exit /b 1
)

:: Check Python version >= 3.11
python -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)" 2>nul
if errorlevel 1 (
    echo  [WARNUNG] Python 3.11+ empfohlen. Aktuelle Version könnte Probleme machen.
)

echo  OK - Python gefunden.
echo.

:: Upgrade pip
echo  [2/5] Aktualisiere pip...
python -m pip install --upgrade pip --quiet
echo  OK.
echo.

:: Core dependencies
echo  [3/5] Installiere Kernpakete...
python -m pip install ^
    fastapi ^
    "uvicorn[standard]" ^
    numpy ^
    Pillow ^
    "opencv-python" ^
    "toml>=0.10" ^
    "pydantic>=2.0" ^
    pyserial ^
    pywin32 ^
    pypresence ^
    dxcam ^
    --quiet
if errorlevel 1 (
    echo  [FEHLER] Paketinstallation fehlgeschlagen!
    pause & exit /b 1
)
echo  OK.
echo.

:: ONNX Runtime DirectML (works on all GPUs without CUDA)
echo  [4/5] Installiere ONNX Runtime (DirectML - funktioniert mit allen GPUs)...
python -m pip install onnxruntime-directml --quiet
if errorlevel 1 (
    echo  [WARNUNG] DirectML fehlgeschlagen - installiere CPU-Version...
    python -m pip install onnxruntime --quiet
)
echo  OK.
echo.

:: Create required directories
echo  [5/5] Erstelle Verzeichnisse...
if not exist "models"       mkdir models
if not exist "profiles"     mkdir profiles
if not exist "logs"         mkdir logs
if not exist "screenshots"  mkdir screenshots
echo  OK.
echo.

echo  =========================================================
echo   Installation abgeschlossen!
echo.
echo   Nächste Schritte:
echo    1. Lege deine .onnx Modelldatei in den models\ Ordner
echo    2. Starte START.bat als Administrator
echo  =========================================================
echo.
pause
