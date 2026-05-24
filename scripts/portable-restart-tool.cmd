@echo off
setlocal
if "%~1"=="" (
  echo Usage: portable-restart-tool.cmd ^<host^|service-id^|mos^|rsa^|data-secure^|all^>
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0portable-split-tool-control.ps1" -Action restart -Tool %1
endlocal
