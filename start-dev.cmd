@echo off
chcp 65001 >nul
cd /d "%~dp0"
rem 新窗口运行 PowerShell，本 CMD 立即返回，便于多次启动或与其他任务并发
rem 默认 sqlite；可传参覆盖，例如：start-dev.cmd -Database postgres
start "MOS Toolbox Dev" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-dev.ps1" %*
