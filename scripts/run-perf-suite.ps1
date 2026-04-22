param(
  [Parameter(Mandatory = $false)]
  [string]$BaseUrl = "http://127.0.0.1:3001",
  [Parameter(Mandatory = $true)]
  [string]$Token,
  [Parameter(Mandatory = $false)]
  [string]$ToolId = "",
  [Parameter(Mandatory = $false)]
  [string]$OutputDir = ".\perf\results",
  [Parameter(Mandatory = $false)]
  [string]$Label = "postgres",
  [Parameter(Mandatory = $false)]
  [switch]$Quick
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$runScript = Join-Path $repoRoot "scripts\run-perf-k6.ps1"
$reportScript = Join-Path $repoRoot "scripts\report-perf-k6.ps1"
if (-not (Test-Path $runScript)) { throw "Missing script: $runScript" }
if (-not (Test-Path $reportScript)) { throw "Missing script: $reportScript" }

if (-not (Test-Path $OutputDir)) {
  New-Item -Path $OutputDir -ItemType Directory | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$baselineJson = Join-Path $OutputDir "k6-$Label-baseline-$timestamp.json"
$stressJson = Join-Path $OutputDir "k6-$Label-stress-$timestamp.json"
$reportMd = Join-Path $OutputDir "k6-$Label-report-$timestamp.md"

if ($Quick) {
  $baselineProfile = "custom"
  $stressProfile = "custom"
  $baselineExtra = @(
    "-StartVus", "1",
    "-SteadyTargetVus", "3",
    "-RampDuration", "10s",
    "-SteadyDuration", "20s",
    "-RampDownDuration", "10s"
  )
  $stressExtra = @(
    "-StartVus", "1",
    "-SteadyTargetVus", "10",
    "-RampDuration", "10s",
    "-SteadyDuration", "30s",
    "-RampDownDuration", "10s"
  )
} else {
  $baselineProfile = "baseline"
  $stressProfile = "stress"
  $baselineExtra = @()
  $stressExtra = @()
}

Write-Host "[suite] Running baseline profile..."
$baselineCmd = @(
  "powershell", "-ExecutionPolicy", "Bypass", "-File", $runScript,
  "-BaseUrl", $BaseUrl,
  "-Token", $Token,
  "-Profile", $baselineProfile,
  "-OutJson", $baselineJson
) + $baselineExtra
if ($ToolId -ne "") {
  $baselineCmd += @("-ToolId", $ToolId)
}
& $baselineCmd[0] $baselineCmd[1..($baselineCmd.Length - 1)]
if ($LASTEXITCODE -ne 0) { throw "Baseline run failed with code $LASTEXITCODE" }

Write-Host "[suite] Running stress profile..."
$stressCmd = @(
  "powershell", "-ExecutionPolicy", "Bypass", "-File", $runScript,
  "-BaseUrl", $BaseUrl,
  "-Token", $Token,
  "-Profile", $stressProfile,
  "-OutJson", $stressJson
) + $stressExtra
if ($ToolId -ne "") {
  $stressCmd += @("-ToolId", $ToolId)
}
& $stressCmd[0] $stressCmd[1..($stressCmd.Length - 1)]
if ($LASTEXITCODE -ne 0) { throw "Stress run failed with code $LASTEXITCODE" }

Write-Host "[suite] Generating report..."
& $reportScript `
  -SummaryFiles @($baselineJson, $stressJson) `
  -OutMarkdown $reportMd
if ($LASTEXITCODE -ne 0) {
  Write-Host "[suite] Report completed with threshold failures."
  exit 1
}

Write-Host ""
Write-Host "[suite] Completed."
Write-Host "[suite] Baseline: $baselineJson"
Write-Host "[suite] Stress:   $stressJson"
Write-Host "[suite] Report:   $reportMd"
