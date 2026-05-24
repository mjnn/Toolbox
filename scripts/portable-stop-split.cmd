@echo off
setlocal
if exist "%~dp0stop-split.ps1" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-split.ps1"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0portable-stop-split.ps1"
)
endlocal
