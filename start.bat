@echo off
title Nyx Terminal
echo.
echo  NYX TERMINAL — Arranque
echo  ========================
echo.

cd /d "%~dp0"

echo  [1] Instalando dependencias en venv...
if not exist .venv (
    uv venv .venv --python 3.14
)
uv pip install -r requirements.txt --quiet
echo      OK

echo.
echo  [2] Levantando Diaricat Live en http://127.0.0.1:8766 ...
start "Diaricat Live :8766" /min .venv\Scripts\python.exe diaricat_service.py

echo  [3] Levantando API en http://localhost:8000 ...
echo      Dashboard: http://localhost:8000/map
echo.
echo  Ctrl+C para detener la API (la ventana de Diaricat se cierra sola)
echo.

timeout /t 2 /nobreak >nul
start "" "http://localhost:8000/map"
.venv\Scripts\uvicorn api:app --reload --port 8000
