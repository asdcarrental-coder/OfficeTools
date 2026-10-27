@echo off
cd /d "%~dp0"
python -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Ready. Double-click start.bat to launch.
pause
exit /b 0
:failed
echo Setup failed. See error above.
pause
exit /b 1
