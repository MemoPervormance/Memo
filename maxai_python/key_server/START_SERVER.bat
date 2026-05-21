@echo off
title CroixAI Key Server
echo.
echo  CroixAI Key Server starten...
echo  Admin-Secret aus Umgebungsvariable CROIXAI_ADMIN_SECRET
echo.
pip install -r requirements.txt --quiet
uvicorn server:app --host 0.0.0.0 --port 8080
pause
