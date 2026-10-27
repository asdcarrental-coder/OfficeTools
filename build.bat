@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m pip install pyinstaller
if errorlevel 1 goto failed
".venv\Scripts\python.exe" scripts\build.py
if errorlevel 1 goto failed
echo Built: dist\OfficeTools\OfficeTools.exe
pause
exit /b 0
:failed
echo Build failed. See error above.
pause
exit /b 1
