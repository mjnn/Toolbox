$ErrorActionPreference = "Stop"

$Root = (Resolve-Path $PSScriptRoot).Path
$Exe = Join-Path $Root "toolbox-backend.exe"
$RunDir = Join-Path $Root "run"
$LogsDir = Join-Path $Root "logs"
$PidFile = Join-Path $RunDir "toolbox-backend.pid"

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
            Write-Host "Toolbox is already running (PID: $oldPid)."
            Write-Host "Local URL: http://127.0.0.1:3000"
            exit 0
        }
    }
}

$env:TOOLBOX_BOOTSTRAP_USERS = "1"
$env:TOOLBOX_LOG_DIR = $LogsDir
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
if (-not $resolvedFrontendDist) {
    Write-Host "Warning: frontend dist not found in expected locations."
    Write-Host "Tried:"
    $frontendDistCandidates | ForEach-Object { Write-Host "  - $_" }
} else {
    $env:TOOLBOX_FRONTEND_DIST = $resolvedFrontendDist
}
$env:TOOLBOX_STATIC_DIR = (Join-Path $Root "static")
$env:TOOLBOX_HOST = "0.0.0.0"
$env:TOOLBOX_PORT = "3000"

$stdoutLog = Join-Path $LogsDir "backend-runtime.out.log"
$stderrLog = Join-Path $LogsDir "backend-runtime.err.log"

$proc = Start-Process -FilePath $Exe -WorkingDirectory $Root -PassThru `
    -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog

$proc.Id | Out-File $PidFile -Encoding ascii -Force

$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Milliseconds 800
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:3000/health" -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) {
            $ok = $true
            break
        }
    } catch {
    }
}

if (-not $ok) {
    Write-Host "Startup timeout. Check logs under: $LogsDir"
    Write-Host "stderr: $stderrLog"
    exit 1
}

Write-Host ""
Write-Host "Toolbox started successfully."
Write-Host "Local URL: http://127.0.0.1:3000"
Write-Host "LAN URL(s):"
$lanIps = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
        $_.IPAddress -and
        $_.AddressState -eq "Preferred" -and
        $_.IPAddress -ne "127.0.0.1" -and
        $_.IPAddress -notlike "169.254.*"
    } |
    Select-Object -ExpandProperty IPAddress -Unique)
if ($lanIps.Count -gt 0) {
    foreach ($ip in $lanIps) {
        Write-Host "  http://${ip}:3000"
    }
} else {
    Write-Host "  (No LAN IPv4 detected. Check adapter/network state.)"
}
Write-Host ""
Write-Host "Default accounts:"
Write-Host "  admin / admin123         (administrator)"
Write-Host "  owner / owner123         (feature owner)"
Write-Host "  user / user12345         (normal user)"
Write-Host ""
Write-Host "Logs:"
Write-Host "  backend runtime  -> logs\backend-runtime.out.log / logs\backend-runtime.err.log"
Write-Host "  backend access   -> logs\backend-access.log"
Write-Host "  frontend access  -> logs\frontend-access.log"
Write-Host "  app mixed log    -> logs\app.log"
Write-Host ""
Write-Host "Note: Ensure Windows Firewall allows inbound TCP 3000 for LAN access."
Write-Host ""
Write-Host "Use stop.cmd to stop all services."

Start-Process "http://127.0.0.1:3000" | Out-Null
