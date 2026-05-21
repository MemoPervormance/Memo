@echo off
title CroixAI — Build Customer EXE
color 0E
echo.
echo  ========================================================
echo    CroixAI — Customer EXE Builder
echo    Produces: dist\CroixAI.exe  (kein Sourcecode sichtbar)
echo  ========================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python nicht gefunden. Bitte Python 3.11+ installieren.
    pause & exit /b 1
)

echo  [1/4] Installiere Build-Tools...
pip install pyinstaller pyarmor --quiet
if errorlevel 1 goto :error

echo  [2/4] Obfuskiere Sourcecode mit PyArmor...
:: Remove old obfuscated output
if exist obf_build rmdir /s /q obf_build

:: Obfuscate all Python source files
:: --enable-rft = rename functions/variables (extra protection)
:: --restrict 2 = prevent import outside the package
pyarmor gen --recursive --output obf_build ^
    --enable-rft ^
    main_customer.py ^
    license.py ^
    config.py ^
    assist_loop.py ^
    aligner.py ^
    auto_fire.py ^
    capture_backends ^
    input_backends ^
    detector_yolo.py ^
    discord_rpc.py ^
    game_presets.py ^
    hotkeys.py ^
    math_utils.py ^
    model_registry.py ^
    overlay.py ^
    recoil.py ^
    setup_wizard.py ^
    tunnel.py ^
    web_server.py ^
    wind_mouse.py

if errorlevel 1 goto :error

:: Copy non-Python assets into obf_build
xcopy /e /i /q static       obf_build\static\       >nul
xcopy /e /i /q profiles     obf_build\profiles\     >nul
copy /y config.toml.example obf_build\              >nul

echo  [3/4] Kompiliere mit PyInstaller...
cd obf_build
pyinstaller ..\croixai_customer.spec --distpath ..\dist --workpath ..\build_tmp --noconfirm
if errorlevel 1 (cd .. & goto :error)
cd ..

echo  [4/4] Räume auf...
rmdir /s /q obf_build   2>nul
rmdir /s /q build_tmp   2>nul

echo.
echo  ========================================================
echo   FERTIG!  Customer EXE:  dist\CroixAI.exe
echo.
echo   Diese Datei an Kunden weitergeben:
echo     dist\CroixAI.exe
echo     models\          (ONNX-Modell hinzufügen)
echo     LICENSE_INFO.txt
echo  ========================================================
echo.
pause
exit /b 0

:error
echo.
echo  [ERROR] Build fehlgeschlagen. Siehe Ausgabe oben.
pause
exit /b 1
