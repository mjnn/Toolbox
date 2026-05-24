$ErrorActionPreference = "Stop"
$Root = (Resolve-Path $PSScriptRoot).Path
& (Join-Path $Root "stop-frontend.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Start-Sleep -Milliseconds 400
& (Join-Path $Root "start-frontend.ps1")
exit $LASTEXITCODE
