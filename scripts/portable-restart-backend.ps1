$ErrorActionPreference = "Stop"
$Root = (Resolve-Path $PSScriptRoot).Path
& (Join-Path $Root "stop-backend.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Start-Sleep -Milliseconds 500
& (Join-Path $Root "start-backend.ps1")
exit $LASTEXITCODE
