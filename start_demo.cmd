@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" app.py --demo
) else (
  py -3 app.py --demo
)
if errorlevel 1 pause
