@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" app.py --demo --cli
) else (
  py -3 app.py --demo --cli
)
if errorlevel 1 pause
