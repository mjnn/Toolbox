[CmdletBinding()]
param(
    # 可选：并行执行「前端 npm run build」与「pip install + pyinstaller 安装」（仅缩短打包机耗时，与运行时 Uvicorn worker 无关）
    [switch] $ParallelPrereqs,
    # 可选：将 backend/.env 打进发布包（默认不打，避免携带开发或敏感配置）
    [switch] $IncludeBackendEnv
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$ReleaseDir = Join-Path $ProjectRoot "release\toolbox-portable"
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"

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

    Write-Host "[1/5] ParallelPrereqs: frontend 'npm run build' + backend 'pip install' (two jobs)..."

    $sbFrontend = {
        param($Dir, $MergedPath)
        $ErrorActionPreference = "Stop"
        $env:Path = $MergedPath
        Set-Location $Dir
        npm run build
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
    Write-Host "[2/5] Backend venv ready; frontend dist should exist for PyInstaller."
} else {
    Write-Host "[1/5] Build frontend dist (default sequential pipeline)..."
    Push-Location $FrontendDir
    npm run build
    Pop-Location

    Write-Host "[2/5] Install backend requirements and PyInstaller..."
    & $VenvPython -m pip install -r (Join-Path $BackendDir "requirements.txt")
    & $VenvPython -m pip install pyinstaller
}

Write-Host "[3/5] Build backend executable..."
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

Write-Host "[4/5] Assemble portable package..."
if (Test-Path $ReleaseDir) {
    try {
        Remove-Item $ReleaseDir -Recurse -Force -ErrorAction Stop
    } catch {
        Write-Warning "Could not remove $ReleaseDir (stop toolbox-backend / close logs if locked). Retrying after clearing logs..."
        $logs = Join-Path $ReleaseDir "logs"
        if (Test-Path $logs) {
            Get-ChildItem $logs -File -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Milliseconds 400
        Remove-Item $ReleaseDir -Recurse -Force
    }
}
New-Item -ItemType Directory -Path $ReleaseDir | Out-Null
Copy-Item (Join-Path $BackendDir "dist_packaging\toolbox-backend\*") $ReleaseDir -Recurse -Force

Copy-Item (Join-Path $ProjectRoot "scripts\portable-start.ps1") (Join-Path $ReleaseDir "start.ps1") -Force
Copy-Item (Join-Path $ProjectRoot "scripts\portable-start.cmd") (Join-Path $ReleaseDir "start.cmd") -Force
Copy-Item (Join-Path $ProjectRoot "scripts\portable-stop.ps1") (Join-Path $ReleaseDir "stop.ps1") -Force
Copy-Item (Join-Path $ProjectRoot "scripts\portable-stop.cmd") (Join-Path $ReleaseDir "stop.cmd") -Force
Copy-Item (Join-Path $ProjectRoot "scripts\PORTABLE_README.md") (Join-Path $ReleaseDir "README.md") -Force
Copy-Item (Join-Path $BackendDir ".env.example") (Join-Path $ReleaseDir ".env.example") -Force

# Perf scripts + k6 scenarios (for on-machine acceptance after deployment)
New-Item -ItemType Directory -Path (Join-Path $ReleaseDir "scripts") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $ReleaseDir "perf") -Force | Out-Null
Copy-Item (Join-Path $ProjectRoot "scripts\run-perf-k6.ps1") (Join-Path $ReleaseDir "scripts\run-perf-k6.ps1") -Force
Copy-Item (Join-Path $ProjectRoot "scripts\run-perf-suite.ps1") (Join-Path $ReleaseDir "scripts\run-perf-suite.ps1") -Force
Copy-Item (Join-Path $ProjectRoot "scripts\report-perf-k6.ps1") (Join-Path $ReleaseDir "scripts\report-perf-k6.ps1") -Force
Copy-Item (Join-Path $ProjectRoot "perf\k6-api.js") (Join-Path $ReleaseDir "perf\k6-api.js") -Force
Copy-Item (Join-Path $ProjectRoot "perf\README.md") (Join-Path $ReleaseDir "perf\README.md") -Force

New-Item -ItemType Directory -Path (Join-Path $ReleaseDir "logs") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $ReleaseDir "run") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $ReleaseDir "static\avatars") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $ReleaseDir "perf\results") -Force | Out-Null

$BackendEnv = Join-Path $BackendDir ".env"
if ($IncludeBackendEnv -and (Test-Path $BackendEnv)) {
    Copy-Item $BackendEnv (Join-Path $ReleaseDir ".env") -Force
    Write-Host "Included backend/.env -> release/toolbox-portable/.env (IncludeBackendEnv)"
} elseif ($IncludeBackendEnv) {
    Write-Warning "IncludeBackendEnv was set, but backend/.env not found."
} else {
    Write-Host "Skipped backend/.env by default. Fill release/toolbox-portable/.env from .env.example with production RDS config."
}

Write-Host "[5/5] Done."
Write-Host "Portable package folder: $ReleaseDir"
