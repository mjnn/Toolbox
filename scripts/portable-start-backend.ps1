$ErrorActionPreference = "Stop"

$Root = (Resolve-Path $PSScriptRoot).Path
$Exe = Join-Path $Root "toolbox-backend.exe"
$RunDir = Join-Path $Root "run"
$LogsDir = Join-Path $Root "logs"
$PidFile = Join-Path $RunDir "toolbox-backend-api.pid"

$apiPort = 3001
if ($env:TOOLBOX_API_PORT) {
    $apiPort = [int]$env:TOOLBOX_API_PORT
}

if (-not (Test-Path $Exe)) {
    throw "backend executable not found: $Exe"
}

New-Item -ItemType Directory -Path $RunDir -Force | Out-Null
New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Root "static\avatars") -Force | Out-Null

if (Test-Path $PidFile) {
    $oldPid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($oldPid) {
        $proc = Get-Process -Id ([int]$oldPid) -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "API backend already running (PID: $oldPid). http://127.0.0.1:$apiPort/health"
            exit 0
        }
    }
}

$env:TOOLBOX_BOOTSTRAP_USERS = "0"
$env:TOOLBOX_LOG_DIR = $LogsDir
$env:TOOLBOX_DISABLE_SPA = "1"
$env:TOOLBOX_HOST = if ($env:TOOLBOX_API_BIND) { $env:TOOLBOX_API_BIND } else { "127.0.0.1" }
$env:TOOLBOX_PORT = "$apiPort"
if (-not $env:TOOLBOX_WORKERS) { $env:TOOLBOX_WORKERS = "2" }
if (-not $env:SQLALCHEMY_POOL_SIZE) { $env:SQLALCHEMY_POOL_SIZE = "12" }
if (-not $env:SQLALCHEMY_MAX_OVERFLOW) { $env:SQLALCHEMY_MAX_OVERFLOW = "8" }
if (-not $env:SQLALCHEMY_POOL_TIMEOUT) { $env:SQLALCHEMY_POOL_TIMEOUT = "45" }
if (-not $env:SQLALCHEMY_POOL_RECYCLE) { $env:SQLALCHEMY_POOL_RECYCLE = "1800" }
if (-not $env:SQLALCHEMY_STATEMENT_TIMEOUT_MS) { $env:SQLALCHEMY_STATEMENT_TIMEOUT_MS = "15000" }

$frontendDistCandidates = @(
    (Join-Path $Root "frontend\dist"),
    (Join-Path $Root "_internal\frontend\dist")
)
$resolvedFrontendDist = $null
foreach ($candidate in $frontendDistCandidates) {
    if (Test-Path (Join-Path $candidate "index.html")) {
        $resolvedFrontendDist = $candidate
        break
    }
}
if ($resolvedFrontendDist) {
    $env:TOOLBOX_FRONTEND_DIST = $resolvedFrontendDist
}
$env:TOOLBOX_STATIC_DIR = (Join-Path $Root "static")

$stdoutLog = Join-Path $LogsDir "backend-api-runtime.out.log"
$stderrLog = Join-Path $LogsDir "backend-api-runtime.err.log"

$proc = Start-Process -FilePath $Exe -WorkingDirectory $Root -PassThru `
    -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog

$proc.Id | Out-File $PidFile -Encoding ascii -Force

$healthUrl = "http://127.0.0.1:$apiPort/health"
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 800
    try {
        $resp = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) {
            $ok = $true
            break
        }
    } catch {
    }
}

if (-not $ok) {
    Write-Host "API startup timeout. Check logs under: $LogsDir"
    Write-Host "stderr: $stderrLog"
    exit 1
}

Write-Host ""
Write-Host "API backend started (SPA disabled, Caddy should serve port 3000)."
Write-Host "Health: $healthUrl"
Write-Host ""
