@echo off
title CroixAI — Model Setup
color 0B
cd /d "%~dp0"
echo.
echo  ========================================================
echo    CroixAI — Model Downloader
echo  ========================================================
echo.
echo  Was du brauchst:
echo  - Echte trainierte .onnx Modelle fuer jedes Spiel
echo  - Diese muessen auf Spiel-Footage trainiert worden sein
echo.
echo  Option 1: Fertiges Modell kaufen / downloaden
echo  -------------------------------------------------
echo  Es gibt fertige Aibot-Modelle fuer YOLOv8 online.
echo  Suche nach: "yolov8 onnx valorant model" etc.
echo  Lege die .onnx Datei in den models\ Ordner.
echo.
echo  Option 2: Selbst trainieren (GPU erforderlich)
echo  -------------------------------------------------
echo  1. Spiel-Screenshots sammeln mit F8 (Screenshot-Key)
echo  2. Bilder mit roboflow.com oder labelimg annotieren
echo  3. train_yolo.py ausfuehren (braucht ultralytics + GPU)
echo.
echo  Jetzt: Lade YOLOv8n als Basis-Modell (erkennt Personen generisch)...
echo  Kann als Test genutzt werden, aber NICHT spielspezifisch optimiert.
echo.

python --version >nul 2>&1
if errorlevel 1 (echo  [FEHLER] Python nicht gefunden. & pause & exit /b 1)

python -c "
import urllib.request, os, sys
from pathlib import Path

models_dir = Path('models')
models_dir.mkdir(exist_ok=True)

# YOLOv8n in ONNX exportiert — allgemeines Personen-Modell
# COCO-trained: erkennt 'person' als Klasse 0
url = 'https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.onnx'
out = models_dir / 'yolov8n_coco.onnx'

if out.exists() and out.stat().st_size > 100_000:
    print(f'  Bereits vorhanden: {out}')
else:
    print(f'  Lade YOLOv8n COCO ({url})...')
    try:
        urllib.request.urlretrieve(url, str(out))
        size = out.stat().st_size // 1024
        print(f'  OK — {size} KB gespeichert: {out}')
    except Exception as e:
        print(f'  FEHLER: {e}')
        sys.exit(1)

print()
print('  WICHTIG: yolov8n_coco.onnx erkennt Personen generisch (COCO-Datensatz).')
print('  Fuer optimale Ergebnisse brauchst du ein spielspezifisches Modell.')
print()
print('  Einstellungen fuer yolov8n_coco.onnx:')
print('  - Blob Size: 640')
print('  - Confidence: 0.35')
print('  - Zielklasse: 0 (person)')
"

if errorlevel 1 (
    echo.
    echo  Download fehlgeschlagen. Pruefe Internetverbindung.
    pause & exit /b 1
)

echo.
echo  ========================================================
echo   Modell heruntergeladen!
echo.
echo   Naechste Schritte:
echo   1. START.bat starten
echo   2. AI Models Tab - Scannen klicken
echo   3. yolov8n_coco.onnx laden
echo   4. Blob Size auf 640 stellen, Confidence auf 0.35
echo   5. Zielklasse 0 (person) funktioniert in allen Spielen
echo.
echo   Fuer spielspezifische Modelle:
echo   Eigene trainieren mit TRAIN_MODEL.bat
echo  ========================================================
echo.
pause
