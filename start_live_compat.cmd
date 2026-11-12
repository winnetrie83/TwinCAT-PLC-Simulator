@echo off
setlocal
cd /d "%~dp0"
echo ======================================================
echo  TwinCAT PLC Simulator - ADS connection test + LIVE
echo  Compatible ADS setup: TwinCAT 2024 / 2026 and newer
 echo ======================================================
echo.
echo Start your TwinCAT UMRT separately, then activate the PLC
 echo configuration and put the PLC into RUN mode before continuing.
echo.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "tools\twincat_compat.py"
) else (
  py -3 "tools\twincat_compat.py"
)
echo.
pause
endlocal
