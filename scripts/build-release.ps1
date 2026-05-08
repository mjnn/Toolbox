[CmdletBinding()]
param(
    # 可选：并行执行「前端 pnpm build」与「pip install + pyinstaller 安装」（仅缩短打包机耗时，与运行时 Uvicorn worker 无关）；与 CI / Dockerfile 一致使用 pnpm。
    [switch] $ParallelPrereqs,
    # 若本机存在 backend/.env 则默认已复制到便携包根；此开关仅表示「若不存在则告警」（便于 CI 显式要求）
    [switch] $IncludeBackendEnv,
    # 内网精简包：跳过性能脚本/perf 目录与 .env.example（仅后端 exe + 启停脚本 + README）
    [switch] $MinimalIntranetPackage,
    # 默认打包后执行一次 start/stop 冒烟；CI 如需跳过可显式传入此开关
    [switch] $SkipPortableSmokeTest
)

$ErrorActionPreference = "Stop"
# 前端构建与 CI / 根 Dockerfile 一致使用 pnpm（需已安装 Node，且通常需 `corepack enable` 以激活 pnpm）。

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$FrontendDistDir = Join-Path $FrontendDir "dist"
$ReleaseDirBase = Join-Path $ProjectRoot "release\toolbox-portable"
$ReleaseDir = $ReleaseDirBase
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
$SkipConfigTemplate = [bool]$MinimalIntranetPackage
$SkipPerfPayload = [bool]$MinimalIntranetPackage

function Invoke-PortableSmokeTest {
    param(
        [string] $ReleaseDir
    )

    $startScript = Join-Path $ReleaseDir "start.ps1"
    $stopScript = Join-Path $ReleaseDir "stop.ps1"
    $pidFile = Join-Path $ReleaseDir "run\toolbox-backend.pid"
    $rootUrl = "http://127.0.0.1:3000/"
    $healthUrl = "http://127.0.0.1:3000/health"

    if (-not (Test-Path $startScript)) {
        throw "portable smoke test failed: start.ps1 missing at $startScript"
    }
    if (-not (Test-Path $stopScript)) {
        throw "portable smoke test failed: stop.ps1 missing at $stopScript"
    }

    Write-Host "[5/5] Smoke test portable package (start -> health/html -> stop)..."

    $stopped = $false
    try {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $startScript
        if ($LASTEXITCODE -ne 0) {
            throw "portable start script returned exit code $LASTEXITCODE"
        }

        $healthOk = $false
        for ($i = 0; $i -lt 20; $i++) {
            Start-Sleep -Milliseconds 500
            try {
                $healthResp = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
                if ($healthResp.StatusCode -eq 200) {
                    $healthOk = $true
                    break
                }
            } catch {
            }
        }
        if (-not $healthOk) {
            throw "portable smoke test failed: /health did not return 200"
        }

        $rootResp = Invoke-WebRequest -Uri $rootUrl -UseBasicParsing -TimeoutSec 5
        if ($rootResp.StatusCode -ne 200) {
            throw "portable smoke test failed: '/' status code $($rootResp.StatusCode)"
        }
        if (-not $rootResp.Content -or $rootResp.Content -notmatch "<!DOCTYPE html>") {
            throw "portable smoke test failed: '/' is not frontend HTML"
        }

        Write-Host "Smoke test passed: /health and frontend index are reachable."
    } finally {
        if (Test-Path $stopScript) {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $stopScript
            $stopped = $true
        }

        if (Test-Path $pidFile) {
            Start-Sleep -Milliseconds 500
            if (Test-Path $pidFile) {
                throw "portable smoke test cleanup failed: pid file still exists after stop"
            }
        } elseif (-not $stopped) {
            Write-Warning "portable smoke test cleanup may be incomplete (stop script was not executed)."
        }
    }
}

function Remove-DirectoryWithRetry {
    param(
        [string] $Path,
        [int] $MaxAttempts = 8,
        [int] $DelayMs = 600
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            Remove-Item $Path -Recurse -Force -ErrorAction Stop
            return
        } catch {
            if ($attempt -ge $MaxAttempts) {
                throw
            }
            Start-Sleep -Milliseconds $DelayMs
        }
    }
}

if (-not (Test-Path $VenvPython)) {
    throw "Python virtualenv not found: $VenvPython"
}

function Invoke-ParallelPackagingPrereqs {
    param(
        [string] $FrontendDir,
        [string] $VenvPython,
        [string] $BackendDir
    )
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $mergedPath = @($machinePath, $userPath) -join ";"

    Write-Host "[1/4] ParallelPrereqs: frontend 'pnpm install --frozen-lockfile' + 'pnpm run build' + backend 'pip install' (two jobs)..."

    $sbFrontend = {
        param($Dir, $MergedPath)
        $ErrorActionPreference = "Stop"
        $env:Path = $MergedPath
        Set-Location $Dir
        corepack enable
        pnpm install --frozen-lockfile
        pnpm run build
    }
    $sbPip = {
        param($Python, $ReqDir, $MergedPath)
        $ErrorActionPreference = "Stop"
        $env:Path = $MergedPath
        & $Python -m pip install -r (Join-Path $ReqDir "requirements.txt")
        & $Python -m pip install pyinstaller
    }

    $jobFrontend = Start-Job -Name "toolbox_pack_frontend" -ScriptBlock $sbFrontend -ArgumentList $FrontendDir, $mergedPath
    $jobPip = Start-Job -Name "toolbox_pack_pip" -ScriptBlock $sbPip -ArgumentList $VenvPython, $BackendDir, $mergedPath

    $jobs = @($jobFrontend, $jobPip)
    Wait-Job -Job $jobs | Out-Null

    $prevEa = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    foreach ($j in $jobs) {
        Write-Host "--- $($j.Name) ---"
        Receive-Job -Job $j 2>&1 | ForEach-Object { Write-Host $_ }
        if ($j.State -ne "Completed") {
            Remove-Job -Job $j -Force -ErrorAction SilentlyContinue
            throw "Packaging job '$($j.Name)' ended with state: $($j.State)."
        }
        Remove-Job -Job $j -Force
    }
    $ErrorActionPreference = $prevEa
}

if ($ParallelPrereqs) {
    Invoke-ParallelPackagingPrereqs -FrontendDir $FrontendDir -VenvPython $VenvPython -BackendDir $BackendDir
    Write-Host "[2/4] Backend venv ready; frontend dist should exist for PyInstaller."
} else {
    Write-Host "[1/4] Build frontend dist (default sequential pipeline)..."
    Push-Location $FrontendDir
    corepack enable
    pnpm install --frozen-lockfile
    pnpm run build
    Pop-Location

    Write-Host "[2/4] Install backend requirements and PyInstaller..."
    & $VenvPython -m pip install -r (Join-Path $BackendDir "requirements.txt")
    & $VenvPython -m pip install pyinstaller
}

Write-Host "[3/4] Build backend executable..."
Push-Location $BackendDir
if (Test-Path ".\dist_packaging") { Remove-Item ".\dist_packaging" -Recurse -Force }
if (Test-Path ".\build") { Remove-Item ".\build" -Recurse -Force }
if (Test-Path ".\run_server.spec") { Remove-Item ".\run_server.spec" -Force }

& $VenvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --name toolbox-backend `
    --onedir `
    --distpath ".\dist_packaging" `
    --paths "." `
    --add-data "../frontend/dist;frontend/dist" `
    --add-data "../ref/toolboxweb;toolboxweb" `
    --hidden-import "main" `
    --hidden-import "uvicorn.logging" `
    --hidden-import "uvicorn.loops.auto" `
    --hidden-import "uvicorn.protocols.http.auto" `
    --hidden-import "uvicorn.protocols.websockets.auto" `
    --hidden-import "uvicorn.lifespan.on" `
    --hidden-import "passlib.handlers.bcrypt" `
    --hidden-import "numpy" `
    --hidden-import "pandas" `
    --hidden-import "werkzeug" `
    --hidden-import "werkzeug.datastructures" `
    --hidden-import "openpyxl" `
    --hidden-import "selenium" `
    --hidden-import "selenium.common" `
    --hidden-import "selenium.common.exceptions" `
    --hidden-import "selenium.webdriver" `
    --hidden-import "selenium.webdriver.chrome" `
    --hidden-import "selenium.webdriver.chrome.service" `
    --hidden-import "selenium.webdriver.chrome.options" `
    --hidden-import "selenium_chrome" `
    --hidden-import "websocket" `
    --hidden-import "websocket._app" `
    --hidden-import "websocket._core" `
    --collect-all "numpy" `
    --collect-all "pandas" `
    --collect-all "selenium" `
    --collect-all "websocket" `
    "run_server.py"
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}
Pop-Location

Write-Host "[4/4] Assemble portable package..."
if (Test-Path $ReleaseDir) {
    $existingStopScript = Join-Path $ReleaseDir "stop.ps1"
    if (Test-Path $existingStopScript) {
        try {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $existingStopScript
        } catch {
            Write-Warning "Failed to run existing portable stop script before cleanup: $($_.Exception.Message)"
        }
    }

    try {
        Remove-DirectoryWithRetry -Path $ReleaseDir
    } catch {
        Write-Warning "Could not remove $ReleaseDir (stop toolbox-backend / close logs if locked). Retrying after clearing logs..."
        $logs = Join-Path $ReleaseDir "logs"
        if (Test-Path $logs) {
            Get-ChildItem $logs -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Milliseconds 400
        try {
            Remove-DirectoryWithRetry -Path $ReleaseDir -MaxAttempts 12 -DelayMs 800
        } catch {
            $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
            $ReleaseDir = Join-Path $ProjectRoot ("release\toolbox-portable-" + $timestamp)
            Write-Warning "Release folder is still locked. Fallback output path: $ReleaseDir"
        }
    }
}
New-Item -ItemType Directory -Path $ReleaseDir | Out-Null
Copy-Item (Join-Path $BackendDir "dist_packaging\toolbox-backend\*") $ReleaseDir -Recurse -Force

# PyInstaller data layout may vary by platform/version; force-copy frontend dist to a stable runtime path.
if (-not (Test-Path (Join-Path $FrontendDistDir "index.html"))) {
    throw "frontend dist missing: $FrontendDistDir (run frontend build before packaging)"
}
$ReleaseFrontendDistDir = Join-Path $ReleaseDir "frontend\dist"
New-Item -ItemType Directory -Path $ReleaseFrontendDistDir -Force | Out-Null
Copy-Item (Join-Path $FrontendDistDir "*") $ReleaseFrontendDistDir -Recurse -Force

Copy-Item (Join-Path $ProjectRoot "scripts\portable-start-split.ps1") (Join-Path $ReleaseDir "start.ps1") -Force
Copy-Item (Join-Path $ProjectRoot "scripts\portable-start.cmd") (Join-Path $ReleaseDir "start.cmd") -Force
Copy-Item (Join-Path $ProjectRoot "scripts\portable-stop-split.ps1") (Join-Path $ReleaseDir "stop.ps1") -Force
Copy-Item (Join-Path $ProjectRoot "scripts\portable-stop.cmd") (Join-Path $ReleaseDir "stop.cmd") -Force
Copy-Item (Join-Path $ProjectRoot "scripts\portable-start-split.ps1") (Join-Path $ReleaseDir "start-split.ps1") -Force
Copy-Item (Join-Path $ProjectRoot "scripts\portable-start-split.cmd") (Join-Path $ReleaseDir "start-split.cmd") -Force
Copy-Item (Join-Path $ProjectRoot "scripts\portable-stop-split.ps1") (Join-Path $ReleaseDir "stop-split.ps1") -Force
Copy-Item (Join-Path $ProjectRoot "scripts\portable-stop-split.cmd") (Join-Path $ReleaseDir "stop-split.cmd") -Force
Copy-Item (Join-Path $ProjectRoot "scripts\portable-split-tool-control.ps1") (Join-Path $ReleaseDir "tool-control.ps1") -Force
Copy-Item (Join-Path $ProjectRoot "scripts\portable-restart-tool.cmd") (Join-Path $ReleaseDir "restart-tool.cmd") -Force
Copy-Item (Join-Path $ProjectRoot "scripts\PORTABLE_README.md") (Join-Path $ReleaseDir "README.md") -Force
if (-not $SkipConfigTemplate) {
    Copy-Item (Join-Path $BackendDir ".env.example") (Join-Path $ReleaseDir ".env.example") -Force
} else {
    Write-Host "MinimalIntranetPackage: skipped .env.example."
}

# Perf scripts + k6; use k6 on PATH or place k6.exe under ops\
if (-not $SkipPerfPayload) {
    New-Item -ItemType Directory -Path (Join-Path $ReleaseDir "scripts") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $ReleaseDir "perf") -Force | Out-Null
    Copy-Item (Join-Path $ProjectRoot "scripts\run-perf-k6.ps1") (Join-Path $ReleaseDir "scripts\run-perf-k6.ps1") -Force
    Copy-Item (Join-Path $ProjectRoot "scripts\run-perf-suite.ps1") (Join-Path $ReleaseDir "scripts\run-perf-suite.ps1") -Force
    Copy-Item (Join-Path $ProjectRoot "scripts\report-perf-k6.ps1") (Join-Path $ReleaseDir "scripts\report-perf-k6.ps1") -Force
    Copy-Item (Join-Path $ProjectRoot "perf\k6-api.js") (Join-Path $ReleaseDir "perf\k6-api.js") -Force
    Copy-Item (Join-Path $ProjectRoot "perf\README.md") (Join-Path $ReleaseDir "perf\README.md") -Force
}

New-Item -ItemType Directory -Path (Join-Path $ReleaseDir "logs") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $ReleaseDir "run") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $ReleaseDir "static\avatars") -Force | Out-Null
if (-not $SkipPerfPayload) {
    New-Item -ItemType Directory -Path (Join-Path $ReleaseDir "perf\results") -Force | Out-Null
}

$BackendEnv = Join-Path $BackendDir ".env"
$ReleaseEnv = Join-Path $ReleaseDir ".env"
if (Test-Path $BackendEnv) {
    Copy-Item $BackendEnv $ReleaseEnv -Force
    Write-Host "Copied backend/.env -> release/toolbox-portable/.env"
} elseif ($IncludeBackendEnv) {
    Write-Warning "IncludeBackendEnv was set, but backend/.env not found; portable package has no .env."
} else {
    if ($SkipConfigTemplate) {
        Write-Host "No backend/.env to copy. MinimalIntranetPackage also skipped .env.example."
    } else {
        Write-Host "No backend/.env on build machine; copy release/toolbox-portable/.env from .env.example on deploy machine."
    }
}

if (-not (Test-Path (Join-Path $ReleaseFrontendDistDir "index.html"))) {
    throw "portable package missing frontend index: $ReleaseFrontendDistDir\index.html"
}

if ($SkipPortableSmokeTest) {
    Write-Host "SkipPortableSmokeTest: skipped post-package start/stop verification."
} else {
    Invoke-PortableSmokeTest -ReleaseDir $ReleaseDir
}

Write-Host "Done."
Write-Host "Portable package folder: $ReleaseDir"
