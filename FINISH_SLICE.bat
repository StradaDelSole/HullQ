@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\workflow\finish-slice.ps1"
set "exitcode=%errorlevel%"
echo.
if not "%exitcode%"=="0" (
  echo Something went wrong. See the message above.
) else (
  echo FINISH_SLICE finished successfully.
)
echo Press any key to close this window.
pause >nul
exit /b %exitcode%
