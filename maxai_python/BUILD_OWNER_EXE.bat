@echo off
title CroixAI — Build Owner EXE
color 0B
echo.
echo  ========================================================
echo    CroixAI — Owner EXE Builder (kein Lizenz-Check)
echo    Erzeugt: dist\CroixAI_Owner.exe
echo  ========================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (echo [ERROR] Python nicht gefunden. & pause & exit /b 1)

echo  [1/2] Installiere PyInstaller...
pip install pyinstaller --quiet
if errorlevel 1 goto :error

echo  [2/2] Kompiliere...
pyinstaller --onefile --console ^
    --name CroixAI_Owner ^
    --add-data "static;static" ^
    --add-data "profiles;profiles" ^
    --add-data "config.toml.example;." ^
    --hidden-import uvicorn.logging ^
    --hidden-import uvicorn.loops ^
    --hidden-import uvicorn.loops.auto ^
    --hidden-import uvicorn.protocols ^
    --hidden-import uvicorn.protocols.http ^
    --hidden-import uvicorn.protocols.http.auto ^
    --hidden-import uvicorn.protocols.websockets ^
    --hidden-import uvicorn.protocols.websockets.auto ^
    --hidden-import uvicorn.lifespan ^
    --hidden-import uvicorn.lifespan.on ^
    --hidden-import pydantic.deprecated.class_validators ^
    --exclude-module ultralytics ^
    --exclude-module torch ^
    --exclude-module matplotlib ^
    main.py

if errorlevel 1 goto :error

echo.
echo  ========================================================
echo   FERTIG:  dist\CroixAI_Owner.exe
echo   Keine Lizenzkontrolle — nur für Eigenbedarf!
echo  ========================================================
echo.
pause & exit /b 0

:error
echo. & echo  [ERROR] Build fehlgeschlagen.
pause & exit /b 1
