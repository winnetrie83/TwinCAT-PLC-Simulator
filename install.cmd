@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
)
if not exist ".venv\Scripts\python.exe" (
    echo Kon de virtuele Python-omgeving niet maken. Controleer je Python-installatie.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Installatie mislukt; controleer je netwerkverbinding.
    pause
    exit /b 1
)
echo.
echo Alles geinstalleerd. Gebruik start_demo.cmd (zonder TwinCAT).
pause
