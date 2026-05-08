$ErrorActionPreference = "Stop"

$Root = (Resolve-Path $PSScriptRoot).Path
$Exe = Join-Path $Root "toolbox-backend.exe"
$RunDir = Join-Path $Root "run"
$LogsDir = Join-Path $Root "logs"

if (-not (Test-Path $Exe)) {
    throw "backend executable not found: $Exe"
}

New-Item -ItemType Directory -Path $RunDir -Force | Out-Null
New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Root "static\avatars") -Force | Out-Null

$processSpecs = @(
    @{
        Name = "host"
        Port = 3000
        PidFile = (Join-Path $RunDir "toolbox-host.pid")
        StdOut = (Join-Path $LogsDir "host-runtime.out.log")
        StdErr = (Join-Path $LogsDir "host-runtime.err.log")
        LoadPlugins = "none"
        ToolUpstreams = "service-id-registry=http://127.0.0.1:3001,mos-integration-toolbox=http://127.0.0.1:3002,rsa-token-livestream=http://127.0.0.1:3003,data-secure-manage=http://127.0.0.1:3004"
        VisibleTools = $null
        Workers = "2"
        PoolSize = "12"
        MaxOverflow = "8"
    },
    @{
        Name = "service-id"
        Port = 3001
        PidFile = (Join-Path $RunDir "toolbox-tool-service-id.pid")
        StdOut = (Join-Path $LogsDir "tool-service-id-runtime.out.log")
        StdErr = (Join-Path $LogsDir "tool-service-id-runtime.err.log")
        LoadPlugins = "service-id-registry"
        ToolUpstreams = $null
        VisibleTools = "service-id-registry"
        Workers = "1"
        PoolSize = "6"
        MaxOverflow = "4"
    },
    @{
        Name = "mos"
        Port = 3002
        PidFile = (Join-Path $RunDir "toolbox-tool-mos.pid")
        StdOut = (Join-Path $LogsDir "tool-mos-runtime.out.log")
        StdErr = (Join-Path $LogsDir "tool-mos-runtime.err.log")
        LoadPlugins = "mos-integration-toolbox"
        ToolUpstreams = $null
        VisibleTools = "mos-integration-toolbox"
        Workers = "1"
        PoolSize = "6"
        MaxOverflow = "4"
    },
    @{
        Name = "rsa"
        Port = 3003
        PidFile = (Join-Path $RunDir "toolbox-tool-rsa.pid")
        StdOut = (Join-Path $LogsDir "tool-rsa-runtime.out.log")
        StdErr = (Join-Path $LogsDir "tool-rsa-runtime.err.log")
        LoadPlugins = "rsa-token-livestream"
        ToolUpstreams = $null
        VisibleTools = "rsa-token-livestream"
        Workers = "1"
        PoolSize = "6"
        MaxOverflow = "4"
    },
    @{
        Name = "data-secure"
        Port = 3004
        PidFile = (Join-Path $RunDir "toolbox-tool-data-secure.pid")
        StdOut = (Join-Path $LogsDir "tool-data-secure-runtime.out.log")
        StdErr = (Join-Path $LogsDir "tool-data-secure-runtime.err.log")
        LoadPlugins = "data-secure-manage"
        ToolUpstreams = $null
        VisibleTools = "data-secure-manage"
        Workers = "1"
        PoolSize = "6"
        MaxOverflow = "4"
    }
)

function Test-PortListening {
    param([int]$Port)
    $conn = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -eq $Port }
    return ($null -ne $conn)
}

function Stop-ByPidFile {
    param([string]$PidFile)
    if (-not (Test-Path $PidFile)) { return }
    $pidText = Get-Content $PidFile -ErrorAction SilentlyContinue
    if (-not $pidText) {
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
        return
    }
    $proc = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
    if ($proc) {
        $taskkill = (Get-Command taskkill.exe -ErrorAction SilentlyContinue).Source
        if ($taskkill) {
            & $taskkill /PID ([int]$pidText) /T /F | Out-Null
        } else {
            Stop-Process -Id ([int]$pidText) -Force
        }
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

function Start-ToolboxProcess {
    param([hashtable]$Spec)

    if (Test-Path $Spec.PidFile) {
        $oldPid = Get-Content $Spec.PidFile -ErrorAction SilentlyContinue
        if ($oldPid) {
            $oldProc = Get-Process -Id ([int]$oldPid) -ErrorAction SilentlyContinue
            if ($oldProc) {
                Write-Host "$($Spec.Name) already running (PID: $oldPid, port: $($Spec.Port))"
                return
            }
        }
        Remove-Item $Spec.PidFile -Force -ErrorAction SilentlyContinue
    }

    if (Test-PortListening -Port $Spec.Port) {
        throw "Port $($Spec.Port) already in use; cannot start $($Spec.Name)"
    }

    $envMap = @{
        TOOLBOX_BOOTSTRAP_USERS = "0"
        TOOLBOX_LOG_DIR = $LogsDir
        TOOLBOX_STATIC_DIR = (Join-Path $Root "static")
        TOOLBOX_HOST = "0.0.0.0"
        TOOLBOX_PORT = "$($Spec.Port)"
        TOOLBOX_WORKERS = "$($Spec.Workers)"
        SQLALCHEMY_POOL_SIZE = "$($Spec.PoolSize)"
        SQLALCHEMY_MAX_OVERFLOW = "$($Spec.MaxOverflow)"
        SQLALCHEMY_POOL_TIMEOUT = "45"
        SQLALCHEMY_POOL_RECYCLE = "1800"
        SQLALCHEMY_STATEMENT_TIMEOUT_MS = "15000"
        TOOLBOX_LOAD_TOOL_PLUGINS = "$($Spec.LoadPlugins)"
    }
    if ($Spec.ToolUpstreams) { $envMap["TOOLBOX_TOOL_UPSTREAMS"] = "$($Spec.ToolUpstreams)" }
    if ($Spec.VisibleTools) { $envMap["TOOLBOX_VISIBLE_TOOL_KEYS"] = "$($Spec.VisibleTools)" }

    $backup = @{}
    foreach ($k in $envMap.Keys) {
        $backup[$k] = [System.Environment]::GetEnvironmentVariable($k, "Process")
        [System.Environment]::SetEnvironmentVariable($k, $envMap[$k], "Process")
    }
    try {
        $proc = Start-Process -FilePath $Exe -WorkingDirectory $Root -PassThru `
            -RedirectStandardOutput $Spec.StdOut -RedirectStandardError $Spec.StdErr
    } finally {
        foreach ($k in $envMap.Keys) {
            [System.Environment]::SetEnvironmentVariable($k, $backup[$k], "Process")
        }
    }

    $proc.Id | Out-File $Spec.PidFile -Encoding ascii -Force
    Write-Host "Started $($Spec.Name) (PID: $($proc.Id), port: $($Spec.Port))"
}

function Wait-Health {
    param([int]$Port, [string]$Name)
    $ok = $false
    for ($i = 0; $i -lt 80; $i++) {
        Start-Sleep -Milliseconds 600
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 2
            if ($resp.StatusCode -eq 200) { $ok = $true; break }
        } catch {}
    }
    if (-not $ok) {
        throw "$Name health check timeout at port $Port"
    }
}

try {
    # start tool runtimes first, then host
    foreach ($spec in $processSpecs | Where-Object { $_.Name -ne "host" }) {
        Start-ToolboxProcess -Spec $spec
    }
    foreach ($spec in $processSpecs | Where-Object { $_.Name -ne "host" }) {
        Wait-Health -Port $spec.Port -Name $spec.Name
    }

    $hostSpec = $processSpecs | Where-Object { $_.Name -eq "host" } | Select-Object -First 1
    Start-ToolboxProcess -Spec $hostSpec
    Wait-Health -Port 3000 -Name "host"
} catch {
    Write-Host "Split startup failed: $($_.Exception.Message)"
    foreach ($spec in $processSpecs) {
        Stop-ByPidFile -PidFile $spec.PidFile
    }
    exit 1
}

Write-Host ""
Write-Host "Toolbox split mode started successfully."
Write-Host "Host entry: http://127.0.0.1:3000"
Write-Host "Internal tools: service-id=3001, mos=3002, rsa=3003"
Write-Host "Use stop-split.cmd to stop all processes."
Write-Host ""

Start-Process "http://127.0.0.1:3000" | Out-Null
