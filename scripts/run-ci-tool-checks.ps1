# Run tool manifest validation and plugin import boundary checks (from repo root).
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
python scripts/validate_tool_manifests.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/check_tool_plugin_boundaries.py
exit $LASTEXITCODE
