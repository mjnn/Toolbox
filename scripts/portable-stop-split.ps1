$ErrorActionPreference = "Stop"

$Root = (Resolve-Path $PSScriptRoot).Path
$RunDir = Join-Path $Root "run"

$pidFiles = @(
    (Join-Path $RunDir "toolbox-host.pid"),
    (Join-Path $RunDir "toolbox-tool-service-id.pid"),
    (Join-Path $RunDir "toolbox-tool-mos.pid"),
    (Join-Path $RunDir "toolbox-tool-rsa.pid"),
    (Join-Path $RunDir "toolbox-tool-data-secure.pid")
)

$stopped = 0
foreach ($pidFile in $pidFiles) {
    if (-not (Test-Path $pidFile)) { continue }
    $pidText = Get-Content $pidFile -ErrorAction SilentlyContinue
    if (-not $pidText) {
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        continue
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
        Write-Host "Stopped PID $procId from $(Split-Path $pidFile -Leaf)"
        $stopped++
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
}

if ($stopped -eq 0) {
    Write-Host "No split-mode process found."
} else {
    Write-Host "Split mode stopped ($stopped process roots)."
}
