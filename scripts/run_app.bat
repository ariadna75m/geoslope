@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo Falta el entorno virtual. Sigue docs\manual_instalacion.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\run_app.py
if errorlevel 1 (
  echo La aplicacion no pudo iniciar. Verifica dependencias e integridad.
  pause
  exit /b 1
)
endlocal
