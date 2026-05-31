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
echo  [5/6] Erstelle Verzeichnisse...
if not exist "models"       mkdir models
if not exist "profiles"     mkdir profiles
if not exist "logs"         mkdir logs
if not exist "screenshots"  mkdir screenshots
echo  OK.
echo.

:: Download base model + write default config
echo  [6/6] Lade Basis-Model herunter und konfiguriere...
python -c "
import urllib.request, sys, os
from pathlib import Path

root = Path('.')
models_dir = root / 'models'
models_dir.mkdir(exist_ok=True)
out = models_dir / 'yolov8n_coco.onnx'

if out.exists() and out.stat().st_size > 100_000:
    print('  Basis-Model bereits vorhanden: yolov8n_coco.onnx')
else:
    urls = [
        'https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.onnx',
        'https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.onnx',
    ]
    print('  Lade YOLOv8n COCO herunter...')
    ok = False
    for url in urls:
        try:
            import ssl, urllib.request
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
                data = r.read()
            if len(data) > 100_000:
                out.write_bytes(data)
                print(f'  OK — {len(data)//1024} KB gespeichert: {out}')
                ok = True
                break
        except Exception as e:
            print(f'  Versuch fehlgeschlagen ({url}): {e}')
    if not ok:
        print('  [WARNUNG] Download fehlgeschlagen.')
        print('  Lege yolov8n_coco.onnx manuell in den models\\ Ordner.')

cfg_path = root / 'config.toml'
if not cfg_path.exists():
    cfg_path.write_text(
        '[detection]\n'
        'model_path           = \"models/yolov8n_coco.onnx\"\n'
        'blob_size            = 640\n'
        'confidence_threshold = 0.35\n'
        'target_classes       = [0]\n'
        '\n'
        '[aim]\n'
        'auto_aim = false\n'
        '\n'
        '[triggerbot]\n'
        'enabled = false\n',
        encoding='utf-8'
    )
    print('  config.toml angelegt.')
else:
    print('  config.toml bereits vorhanden — unveraendert.')
"

if errorlevel 1 (
    echo  [WARNUNG] Model-Download hatte Probleme - DOWNLOAD_MODEL.bat pruefen.
)
echo.

echo  =========================================================
echo   Installation abgeschlossen!
echo.
echo   Naechste Schritte:
echo    1. START.bat als Administrator starten
echo    2. Input-Backend waehlen (1 = SendInput, reicht fuer Start)
echo    3. Browser oeffnet automatisch auf http://127.0.0.1:17384
echo.
echo   Basis-Model: yolov8n_coco.onnx (erkennt Personen in allen Spielen)
echo   Fuer bessere Erkennung: TRAIN_MODEL.bat oder eigenes Modell laden
echo  =========================================================
echo.
pause
