@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\workflow\finish-slice.ps1"
if errorlevel 1 (
  echo.
  echo Something went wrong. See the message above.
  pause
)
