@echo off
setlocal
if exist "%~dp0start-split.ps1" (
  start "" /b powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "%~dp0start-split.ps1"
) else (
  start "" /b powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "%~dp0start.ps1"
)
exit /b 0
