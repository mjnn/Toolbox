param(
  [Parameter(Mandatory = $true)]
  [string[]]$SummaryFiles,
  [Parameter(Mandatory = $false)]
  [double]$P95ThresholdMs = 1200,
  [Parameter(Mandatory = $false)]
  [double]$P99ThresholdMs = 2000,
  [Parameter(Mandatory = $false)]
  [double]$FailRateThreshold = 0.02,
  [Parameter(Mandatory = $false)]
  [string]$OutMarkdown = ""
)

$ErrorActionPreference = "Stop"

function Get-MetricValue {
  param(
    [Parameter(Mandatory = $true)]$MetricObj,
    [Parameter(Mandatory = $true)][string]$Field,
    [Parameter(Mandatory = $false)][double]$Default = 0
  )
  if (-not $MetricObj) { return $Default }
  $value = $MetricObj.PSObject.Properties[$Field]
  if (-not $value) { return $Default }
  return [double]$value.Value
}

$rows = @()
foreach ($file in $SummaryFiles) {
  if (-not (Test-Path $file)) {
    throw "Summary file not found: $file"
  }
  $json = Get-Content -Raw -Path $file | ConvertFrom-Json
  $dur = $json.metrics.http_req_duration
  $fail = $json.metrics.http_req_failed
  $reqs = $json.metrics.http_reqs

  $p95 = Get-MetricValue -MetricObj $dur -Field "p(95)"
  $p99 = Get-MetricValue -MetricObj $dur -Field "p(99)"
  $avg = Get-MetricValue -MetricObj $dur -Field "avg"
  $failRate = Get-MetricValue -MetricObj $fail -Field "rate"
  $rps = Get-MetricValue -MetricObj $reqs -Field "rate"

  $pass = ($p95 -le $P95ThresholdMs) -and ($p99 -le $P99ThresholdMs) -and ($failRate -le $FailRateThreshold)
  $rows += [PSCustomObject]@{
    File = $file
    P95Ms = [math]::Round($p95, 2)
    P99Ms = [math]::Round($p99, 2)
    AvgMs = [math]::Round($avg, 2)
    FailRate = [math]::Round($failRate * 100, 2)
    RPS = [math]::Round($rps, 2)
    Pass = $pass
  }
}

Write-Host ""
Write-Host "k6 Performance Report"
Write-Host "Thresholds: p95<=$P95ThresholdMs ms, p99<=$P99ThresholdMs ms, fail_rate<=$([math]::Round($FailRateThreshold * 100, 2))%"
Write-Host ""
$rows | Format-Table -AutoSize

if ($OutMarkdown -ne "") {
  $lines = @()
  $lines += "# k6 Performance Report"
  $lines += ""
  $lines += "- Threshold p95 <= $P95ThresholdMs ms"
  $lines += "- Threshold p99 <= $P99ThresholdMs ms"
  $lines += "- Threshold fail_rate <= $([math]::Round($FailRateThreshold * 100, 2))%"
  $lines += ""
  $lines += "| File | P95 (ms) | P99 (ms) | Avg (ms) | Fail Rate (%) | RPS | Pass |"
  $lines += "| --- | ---: | ---: | ---: | ---: | ---: | :---: |"
  foreach ($r in $rows) {
    $passText = if ($r.Pass) { "YES" } else { "NO" }
    $lines += "| $($r.File) | $($r.P95Ms) | $($r.P99Ms) | $($r.AvgMs) | $($r.FailRate) | $($r.RPS) | $passText |"
  }
  Set-Content -Path $OutMarkdown -Value ($lines -join [Environment]::NewLine) -Encoding UTF8
  Write-Host ""
  Write-Host "Markdown report saved: $OutMarkdown"
}

$failed = $rows | Where-Object { -not $_.Pass }
if ($failed.Count -gt 0) {
  exit 1
}
