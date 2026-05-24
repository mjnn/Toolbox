@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem Launch PowerShell in a new window and return immediately.
rem Default database is sqlite. Example: start-dev.cmd -Database postgres
start "MOS Toolbox Dev" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-dev.ps1" %*
