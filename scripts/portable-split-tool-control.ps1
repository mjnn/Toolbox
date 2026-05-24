$ErrorActionPreference = "Stop"

param(
    [ValidateSet("status", "start", "stop", "restart")]
    [string]$Action = "status",

    [ValidateSet("all", "host", "service-id", "mos", "rsa", "data-secure")]
    [string]$Tool = "all"
)

$Root = (Resolve-Path $PSScriptRoot).Path
$Exe = Join-Path $Root "toolbox-backend.exe"
$RunDir = Join-Path $Root "run"
$LogsDir = Join-Path $Root "logs"

if (-not (Test-Path $Exe)) {
    throw "backend executable not found: $Exe"
}

New-Item -ItemType Directory -Path $RunDir -Force | Out-Null
New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null

$allSpecs = @{
    "host" = @{
        Name = "host"; Port = 3000;
        PidFile = (Join-Path $RunDir "toolbox-host.pid");
        StdOut = (Join-Path $LogsDir "host-runtime.out.log");
        StdErr = (Join-Path $LogsDir "host-runtime.err.log");
        LoadPlugins = "none";
        ToolUpstreams = "service-id-registry=http://127.0.0.1:3001,mos-integration-toolbox=http://127.0.0.1:3002,rsa-token-livestream=http://127.0.0.1:3003,data-secure-manage=http://127.0.0.1:3004";
        VisibleTools = $null; Workers = "2"; PoolSize = "12"; MaxOverflow = "8"
    }
    "service-id" = @{
        Name = "service-id"; Port = 3001;
        PidFile = (Join-Path $RunDir "toolbox-tool-service-id.pid");
        StdOut = (Join-Path $LogsDir "tool-service-id-runtime.out.log");
        StdErr = (Join-Path $LogsDir "tool-service-id-runtime.err.log");
        LoadPlugins = "service-id-registry";
        ToolUpstreams = $null; VisibleTools = "service-id-registry"; Workers = "1"; PoolSize = "6"; MaxOverflow = "4"
    }
    "mos" = @{
        Name = "mos"; Port = 3002;
        PidFile = (Join-Path $RunDir "toolbox-tool-mos.pid");
        StdOut = (Join-Path $LogsDir "tool-mos-runtime.out.log");
        StdErr = (Join-Path $LogsDir "tool-mos-runtime.err.log");
        LoadPlugins = "mos-integration-toolbox";
        ToolUpstreams = $null; VisibleTools = "mos-integration-toolbox"; Workers = "1"; PoolSize = "6"; MaxOverflow = "4"
    }
    "rsa" = @{
        Name = "rsa"; Port = 3003;
        PidFile = (Join-Path $RunDir "toolbox-tool-rsa.pid");
        StdOut = (Join-Path $LogsDir "tool-rsa-runtime.out.log");
        StdErr = (Join-Path $LogsDir "tool-rsa-runtime.err.log");
        LoadPlugins = "rsa-token-livestream";
        ToolUpstreams = $null; VisibleTools = "rsa-token-livestream"; Workers = "1"; PoolSize = "6"; MaxOverflow = "4"
    }
    "data-secure" = @{
        Name = "data-secure"; Port = 3004;
        PidFile = (Join-Path $RunDir "toolbox-tool-data-secure.pid");
        StdOut = (Join-Path $LogsDir "tool-data-secure-runtime.out.log");
        StdErr = (Join-Path $LogsDir "tool-data-secure-runtime.err.log");
        LoadPlugins = "data-secure-manage";
        ToolUpstreams = $null; VisibleTools = "data-secure-manage"; Workers = "1"; PoolSize = "6"; MaxOverflow = "4"
    }
}

function Test-PortListening {
    param([int]$Port)
    $conn = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -eq $Port }
    return ($null -ne $conn)
}

function Get-Targets {
    param([string]$Name)
    if ($Name -eq "all") {
        return @($allSpecs["host"], $allSpecs["service-id"], $allSpecs["mos"], $allSpecs["rsa"], $allSpecs["data-secure"])
    }
    return @($allSpecs[$Name])
}

function Stop-One {
    param([hashtable]$Spec)
    if (-not (Test-Path $Spec.PidFile)) {
        Write-Host "$($Spec.Name): not running (no pid file)."
        return
    }
    $pidText = Get-Content $Spec.PidFile -ErrorAction SilentlyContinue
    if (-not $pidText) {
        Remove-Item $Spec.PidFile -Force -ErrorAction SilentlyContinue
        Write-Host "$($Spec.Name): invalid pid file removed."
        return
    }
    $procId = [int]$pidText
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc) {
        $taskkill = (Get-Command taskkill.exe -ErrorAction SilentlyContinue).Source
        if ($taskkill) {
            & $taskkill /PID $procId /T /F | Out-Null
        } else {
            Stop-Process -Id $procId -Force
        }
        Write-Host "$($Spec.Name): stopped PID $procId."
    } else {
        Write-Host "$($Spec.Name): PID $procId not found, cleanup pid file."
    }
    Remove-Item $Spec.PidFile -Force -ErrorAction SilentlyContinue
}

function Start-One {
    param([hashtable]$Spec)

    if (Test-Path $Spec.PidFile) {
        $oldPid = Get-Content $Spec.PidFile -ErrorAction SilentlyContinue
        if ($oldPid) {
            $oldProc = Get-Process -Id ([int]$oldPid) -ErrorAction SilentlyContinue
            if ($oldProc) {
                Write-Host "$($Spec.Name): already running (PID $oldPid)."
                return
            }
        }
        Remove-Item $Spec.PidFile -Force -ErrorAction SilentlyContinue
    }

    if (Test-PortListening -Port $Spec.Port) {
        throw "$($Spec.Name): port $($Spec.Port) already in use."
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
    Write-Host "$($Spec.Name): started PID $($proc.Id) on port $($Spec.Port)."
}

function Wait-Health {
    param([hashtable]$Spec)
    $ok = $false
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $resp = Invoke-WebRequest -Uri "http://127.0.0.1:$($Spec.Port)/health" -UseBasicParsing -TimeoutSec 2
            if ($resp.StatusCode -eq 200) { $ok = $true; break }
        } catch {}
    }
    if ($ok) {
        Write-Host "$($Spec.Name): health ok."
    } else {
        throw "$($Spec.Name): health timeout on port $($Spec.Port)"
    }
}

function Status-One {
    param([hashtable]$Spec)
    $procId = $null
    $running = $false
    if (Test-Path $Spec.PidFile) {
        $txt = Get-Content $Spec.PidFile -ErrorAction SilentlyContinue
        if ($txt) {
            $procId = [int]$txt
            $running = $null -ne (Get-Process -Id $procId -ErrorAction SilentlyContinue)
        }
    }
    $listening = Test-PortListening -Port $Spec.Port
    Write-Host ("{0,-12} pid={1,-8} running={2,-5} listen={3,-5} port={4}" -f $Spec.Name, ($procId ?? "-"), $running, $listening, $Spec.Port)
}

$targets = Get-Targets -Name $Tool

switch ($Action) {
    "status" {
        foreach ($t in $targets) { Status-One -Spec $t }
        exit 0
    }
    "stop" {
        foreach ($t in ($targets | Sort-Object Port -Descending)) { Stop-One -Spec $t }
        exit 0
    }
    "start" {
        if ($Tool -eq "all") {
            foreach ($t in ($targets | Where-Object { $_.Name -ne "host" })) { Start-One -Spec $t; Wait-Health -Spec $t }
            $host = $targets | Where-Object { $_.Name -eq "host" } | Select-Object -First 1
            Start-One -Spec $host
            Wait-Health -Spec $host
        } else {
            foreach ($t in $targets) { Start-One -Spec $t; Wait-Health -Spec $t }
        }
        exit 0
    }
    "restart" {
        if ($Tool -eq "all") {
            foreach ($t in ($targets | Sort-Object Port -Descending)) { Stop-One -Spec $t }
            foreach ($t in ($targets | Where-Object { $_.Name -ne "host" })) { Start-One -Spec $t; Wait-Health -Spec $t }
            $host = $targets | Where-Object { $_.Name -eq "host" } | Select-Object -First 1
            Start-One -Spec $host
            Wait-Health -Spec $host
        } else {
            foreach ($t in $targets) { Stop-One -Spec $t; Start-One -Spec $t; Wait-Health -Spec $t }
        }
        exit 0
    }
}
