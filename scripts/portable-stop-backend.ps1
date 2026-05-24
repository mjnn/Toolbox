$ErrorActionPreference = "Stop"

$Root = (Resolve-Path $PSScriptRoot).Path
$PidFile = Join-Path $Root "run\toolbox-backend-api.pid"

if (-not (Test-Path $PidFile)) {
    Write-Host "No API pid file. API may already be stopped."
    exit 0
}

$pidText = Get-Content $PidFile -ErrorAction SilentlyContinue
if (-not $pidText) {
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    Write-Host "Invalid pid file removed."
    exit 0
}

$targetPid = [int]$pidText
$proc = Get-Process -Id $targetPid -ErrorAction SilentlyContinue
if ($proc) {
    $exe = (Get-Command taskkill.exe -ErrorAction SilentlyContinue).Source
    if ($exe) {
        & $exe /PID $targetPid /T /F | Out-Null
    } else {
        Stop-Process -Id $targetPid -Force
    }
    Write-Host "Stopped API backend (PID: $targetPid)."
} else {
    Write-Host "Process not found (PID: $targetPid)."
}

Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
