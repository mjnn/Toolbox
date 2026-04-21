# 并发启动：后端与前端几乎同时各起一个独立窗口（Start-Process 不阻塞彼此）。
# 可选环境变量（多实例并发时改端口，避免冲突）：
#   TOOLBOX_BACKEND_PORT  默认 3001
#   TOOLBOX_FRONTEND_PORT 默认 3000
$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Backend = Join-Path $ProjectRoot "backend"
$Frontend = Join-Path $ProjectRoot "frontend"

if (-not (Test-Path $Backend)) { throw "Backend directory not found: $Backend" }
if (-not (Test-Path $Frontend)) { throw "Frontend directory not found: $Frontend" }

function Test-ListeningPort {
    param(
        [Parameter(Mandatory = $true)]
        [int]$Port
    )
    $pattern = "127.0.0.1:$Port\s+0.0.0.0:0\s+LISTENING"
    $hit = netstat -ano | Select-String -Pattern $pattern
    return $null -ne $hit
}

$BackendPort = 3001
$FrontendPort = 3000
if ($env:TOOLBOX_BACKEND_PORT) {
    try { $BackendPort = [int]$env:TOOLBOX_BACKEND_PORT } catch { }
}
if ($env:TOOLBOX_FRONTEND_PORT) {
    try { $FrontendPort = [int]$env:TOOLBOX_FRONTEND_PORT } catch { }
}

$venvPython = Join-Path $Backend ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $backendCmd = "& '$venvPython' -m uvicorn main:app --reload --host 127.0.0.1 --port $BackendPort"
} else {
    $backendCmd = "python -m uvicorn main:app --reload --host 127.0.0.1 --port $BackendPort"
}

$frontendCmd = "`$env:TOOLBOX_BACKEND_PORT='$BackendPort'; `$env:TOOLBOX_FRONTEND_PORT='$FrontendPort'; npm run dev"

Write-Host "Project root: $ProjectRoot"
Write-Host "Backend port: $BackendPort | Frontend port: $FrontendPort"

if (-not (Test-ListeningPort -Port $BackendPort)) {
    Write-Host "Opening backend window (http://127.0.0.1:$BackendPort) ..."
    Start-Process powershell -WorkingDirectory $Backend -ArgumentList @(
        "-NoExit",
        "-NoProfile",
        "-Command",
        $backendCmd
    )
} else {
    Write-Host "Backend already listening on 127.0.0.1:$BackendPort, skipping new backend process."
}

if (-not (Test-ListeningPort -Port $FrontendPort)) {
    Write-Host "Opening frontend window (http://127.0.0.1:$FrontendPort, API proxy -> $BackendPort) ..."
    Start-Process powershell -WorkingDirectory $Frontend -ArgumentList @(
        "-NoExit",
        "-NoProfile",
        "-Command",
        $frontendCmd
    )
} else {
    Write-Host "Frontend already listening on 127.0.0.1:$FrontendPort, skipping new frontend process."
}

Write-Host ""
Write-Host "Started. Close each PowerShell window to stop."
