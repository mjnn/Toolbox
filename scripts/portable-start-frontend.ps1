$ErrorActionPreference = "Stop"

$Root = (Resolve-Path $PSScriptRoot).Path
$Caddy = Join-Path $Root "ops\caddy.exe"
$RunDir = Join-Path $Root "run"
$LogsDir = Join-Path $Root "logs"
$PidFile = Join-Path $RunDir "toolbox-frontend.pid"
$Caddyfile = Join-Path $RunDir "Caddyfile.ops-frontend"

if (-not (Test-Path $Caddy)) {
    throw "caddy.exe not found: $Caddy (rebuild portable package with network to fetch ops binaries)"
}

New-Item -ItemType Directory -Path $RunDir -Force | Out-Null
New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null

if (Test-Path $PidFile) {
    $oldPid = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($oldPid) {
        $proc = Get-Process -Id ([int]$oldPid) -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "Frontend (Caddy) already running (PID: $oldPid)."
            exit 0
        }
    }
}

$fePort = 3000
if ($env:TOOLBOX_FE_PORT) {
    $fePort = [int]$env:TOOLBOX_FE_PORT
}

$apiPort = 3001
if ($env:TOOLBOX_API_PORT) {
    $apiPort = [int]$env:TOOLBOX_API_PORT
}

$apiBind = if ($env:TOOLBOX_API_BIND) { $env:TOOLBOX_API_BIND } else { "127.0.0.1" }
$apiUpstream = "http://${apiBind}:$apiPort"

$frontendDistCandidates = @(
    (Join-Path $Root "frontend\dist"),
    (Join-Path $Root "_internal\frontend\dist")
)
$dist = $null
foreach ($candidate in $frontendDistCandidates) {
    if (Test-Path (Join-Path $candidate "index.html")) {
        $dist = $candidate
        break
    }
}
if (-not $dist) {
    throw "frontend dist not found (expected frontend\dist or _internal\frontend\dist with index.html)"
}

$distCaddy = ($dist -replace '\\', '/')
$distRoot = '"' + ($distCaddy -replace '"', '') + '"'

$caddyBody = @"
{
	admin off
}
:0.0.0.0:$fePort {
	encode gzip zstd
	handle /api/* {
		reverse_proxy $apiUpstream
	}
	handle /static/* {
		reverse_proxy $apiUpstream
	}
	handle {
		root * $distRoot
		route {
			try_files {path} /index.html
			file_server
		}
	}
}
"@

[System.IO.File]::WriteAllText($Caddyfile, $caddyBody.Trim() + "`n", [System.Text.UTF8Encoding]::new($false))

$stdoutLog = Join-Path $LogsDir "caddy-runtime.out.log"
$stderrLog = Join-Path $LogsDir "caddy-runtime.err.log"

$proc = Start-Process -FilePath $Caddy -WorkingDirectory $Root -ArgumentList @("run", "--config", $Caddyfile) -PassThru `
    -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog

$proc.Id | Out-File $PidFile -Encoding ascii -Force

$feUrl = "http://127.0.0.1:$fePort/"
$ok = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $resp = Invoke-WebRequest -Uri $feUrl -UseBasicParsing -TimeoutSec 2
        if ($resp.StatusCode -eq 200) {
            $ok = $true
            break
        }
    } catch {
    }
}

if (-not $ok) {
    Write-Host "Caddy startup timeout. Check: $stderrLog"
    exit 1
}

Write-Host ""
Write-Host "Frontend (Caddy) started on 0.0.0.0:$fePort -> SPA + /api -> $apiUpstream"
Write-Host "Local: $feUrl"
Write-Host ""
