param(
  [Parameter(Mandatory = $false)]
  [string]$BaseUrl = "http://127.0.0.1:3001",
  [Parameter(Mandatory = $true)]
  [string]$Token,
  [Parameter(Mandatory = $false)]
  [string]$ToolId = "",
  [Parameter(Mandatory = $false)]
  [string]$OutJson = "",
  [Parameter(Mandatory = $false)]
  [ValidateSet("baseline", "stress", "custom")]
  [string]$Profile = "stress",
  [Parameter(Mandatory = $false)]
  [int]$StartVus = 1,
  [Parameter(Mandatory = $false)]
  [int]$SteadyTargetVus = 10,
  [Parameter(Mandatory = $false)]
  [string]$RampDuration = "15s",
  [Parameter(Mandatory = $false)]
  [string]$SteadyDuration = "60s",
  [Parameter(Mandatory = $false)]
  [string]$RampDownDuration = "15s"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $repoRoot "perf\k6-api.js"
if (-not (Test-Path $scriptPath)) {
  throw "Missing script: $scriptPath"
}

function Resolve-K6Binary {
  $k6FromPath = Get-Command "k6" -ErrorAction SilentlyContinue
  if ($k6FromPath) { return $k6FromPath.Source }
  $fallback = Join-Path $env:ProgramFiles "k6\k6.exe"
  if (Test-Path $fallback) { return $fallback }
  throw "k6 not found in PATH or Program Files."
}

$k6Bin = Resolve-K6Binary

if ($Profile -eq "baseline") {
  $StartVus = 1
  $SteadyTargetVus = 3
  $RampDuration = "15s"
  $SteadyDuration = "60s"
  $RampDownDuration = "15s"
} elseif ($Profile -eq "stress") {
  $StartVus = 1
  $SteadyTargetVus = 10
  $RampDuration = "15s"
  $SteadyDuration = "60s"
  $RampDownDuration = "15s"
}

$cmd = @(
  $k6Bin
  "run"
  "-e"
  "BASE_URL=$BaseUrl"
  "-e"
  "TOKEN=$Token"
  "-e"
  "START_VUS=$StartVus"
  "-e"
  "STEADY_TARGET_VUS=$SteadyTargetVus"
  "-e"
  "RAMP_DURATION=$RampDuration"
  "-e"
  "STEADY_DURATION=$SteadyDuration"
  "-e"
  "RAMP_DOWN_DURATION=$RampDownDuration"
)

if ($ToolId -ne "") {
  $cmd += @("-e", "TOOL_ID=$ToolId")
}
if ($OutJson -ne "") {
  $cmd += @("--summary-export", $OutJson)
}
$cmd += $scriptPath

Write-Host "[k6] BASE_URL=$BaseUrl TOOL_ID=$ToolId PROFILE=$Profile"
Write-Host "[k6] START_VUS=$StartVus STEADY_TARGET_VUS=$SteadyTargetVus RAMP_DURATION=$RampDuration STEADY_DURATION=$SteadyDuration RAMP_DOWN_DURATION=$RampDownDuration"
Write-Host "[k6] Running: $($cmd -join ' ')"
& $cmd[0] $cmd[1..($cmd.Length - 1)]
