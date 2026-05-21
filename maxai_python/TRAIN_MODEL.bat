@echo off
title CroixAI — Model Training
color 0E
cd /d "%~dp0"
echo.
echo  ========================================================
echo    CroixAI — YOLOv8 Model Training
echo  ========================================================
echo.
echo  Voraussetzungen:
echo  - NVIDIA GPU (RTX 2060 oder besser empfohlen)
echo  - CUDA + cuDNN installiert (INSTALL_CUDA.bat)
echo  - Annotierte Trainingsdaten in datasets\
echo.
echo  Schritt 1: Ultralytics installieren
python -m pip install ultralytics --quiet
if errorlevel 1 (echo  [FEHLER] Installation fehlgeschlagen & pause & exit /b 1)
echo  OK.
echo.

echo  Welches Spiel?
echo  [1] Valorant
echo  [2] CS2 / FaceIt
echo  [3] Apex Legends
echo  [4] Fortnite
echo  [5] COD Warzone
echo  [6] Rainbow Six Siege
echo  [7] Rust
echo  [8] Universal (alle Spiele)
echo.
set /p GAME="  Auswahl [1-8]: "

if "%GAME%"=="1" set GAME_ID=valorant & set MODEL_OUT=phantom_v
if "%GAME%"=="2" set GAME_ID=cs2      & set MODEL_OUT=krieg_cs
if "%GAME%"=="3" set GAME_ID=apex     & set MODEL_OUT=havoc_ax
if "%GAME%"=="4" set GAME_ID=fortnite & set MODEL_OUT=storm_fn
if "%GAME%"=="5" set GAME_ID=warzone  & set MODEL_OUT=warlock_wz
if "%GAME%"=="6" set GAME_ID=r6       & set MODEL_OUT=breach_r6
if "%GAME%"=="7" set GAME_ID=rust     & set MODEL_OUT=furnace_rs
if "%GAME%"=="8" set GAME_ID=universal & set MODEL_OUT=nexus_uni

if "%GAME_ID%"=="" (echo  Ungueltige Auswahl. & pause & exit /b 1)

echo.
echo  Training: %GAME_ID% -> models\%MODEL_OUT%.onnx
echo.
echo  WICHTIG: Du brauchst annotierte Bilder in:
echo    datasets\%GAME_ID%\images\train\
echo    datasets\%GAME_ID%\labels\train\
echo.
echo  Bilder annotieren mit: https://roboflow.com (kostenlos)
echo  Format: YOLOv8 (txt labels)
echo  Klassen: 0=head, 1=body
echo.
pause

python training/train_yolo.py --game %GAME_ID% --output models/%MODEL_OUT%.onnx

if errorlevel 1 (
    echo.
    echo  [FEHLER] Training fehlgeschlagen.
    echo  Pruefe logs\croixai.log fuer Details.
    pause & exit /b 1
)

echo.
echo  ========================================================
echo   Training abgeschlossen!
echo   Modell: models\%MODEL_OUT%.onnx
echo.
echo   Lade es im AI Models Tab -> Scannen -> Laden
echo  ========================================================
pause
