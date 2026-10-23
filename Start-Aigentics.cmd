@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Install first using the Windows instructions in README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m aigentics
if errorlevel 1 pause
