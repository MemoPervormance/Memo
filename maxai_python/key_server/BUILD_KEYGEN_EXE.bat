@echo off
title CroixAI — Build keygen.exe
echo.
echo  Baue keygen.exe...
pip install pyinstaller --quiet
pyinstaller --onefile --noconsole --name keygen keygen_gui.py
echo.
echo  Fertig: dist\keygen.exe
pause
