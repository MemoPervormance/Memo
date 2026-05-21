@echo off
title CroixAI — CUDA Installation
color 0B
echo.
echo  =========================================================
echo    CroixAI — CUDA / NVIDIA GPU Setup
echo    Voraussetzung: NVIDIA GPU + CUDA 12.x + cuDNN
echo  =========================================================
echo.
echo  Entferne DirectML...
python -m pip uninstall onnxruntime-directml -y --quiet 2>nul
echo  Installiere onnxruntime-gpu (CUDA 12.x)...
python -m pip install onnxruntime-gpu --quiet
if errorlevel 1 (
    echo  [FEHLER] Stelle sicher dass CUDA 12.x installiert ist.
    echo  https://developer.nvidia.com/cuda-downloads
    pause & exit /b 1
)
echo.
echo  CUDA-Version installiert!
echo  Provider beim Start: CUDAExecutionProvider
echo.
pause
