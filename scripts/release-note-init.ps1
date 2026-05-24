[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("host", "tool", "mixed")]
    [string] $Type,
    [Parameter(Mandatory = $true)]
    [ValidateSet("ecs", "portable", "ecs+portable")]
    [string] $Channel,
    [string] $ReleaseId = "",
    [string] $Owner = "",
    [string[]] $Tools = @(),
    [string] $HostVersion = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$OutputDir = Join-Path $ProjectRoot "docs\releases"

if ($Type -eq "tool" -and $Tools.Count -eq 0) {
    throw "Type 'tool' requires at least one tool in -Tools."
}
if ($Type -eq "host" -and $Tools.Count -gt 0) {
    throw "Type 'host' should not include -Tools."
}
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

$dateStamp = Get-Date -Format "yyyyMMdd"
$timeStamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
if ([string]::IsNullOrWhiteSpace($ReleaseId)) {
    $ReleaseId = "$dateStamp-$Type-$Channel"
}
$safeReleaseId = ($ReleaseId -replace '[\\/:*?"<>| ]', "-")
$outputPath = Join-Path $OutputDir ("$safeReleaseId.md")
if (Test-Path $outputPath) {
    throw "Release note already exists: $outputPath"
}

$hostPublish = if ($Type -eq "tool") { "no" } else { "yes" }
$ownerText = if ([string]::IsNullOrWhiteSpace($Owner)) { "<fill-me>" } else { $Owner }
$hostVersionText = if ([string]::IsNullOrWhiteSpace($HostVersion)) { "<fill-me>" } else { $HostVersion }

$toolListLines = if ($Tools.Count -gt 0) {
    ($Tools | ForEach-Object { "- [x] $_" }) -join "`n"
} else {
    @"
- [ ] service-id-registry
- [ ] mos-integration-toolbox
- [ ] rsa-token-livestream
- [ ] other: <tool_key>
"@
}

$toolVersionLines = if ($Tools.Count -gt 0) {
    ($Tools | ForEach-Object { "- ${_}: <version>" }) -join "`n"
} else {
    "- <tool_key_1>: <version>"
}

$toolChangelogLines = if ($Tools.Count -gt 0) {
    ($Tools | ForEach-Object {
@"
- ${_}:
  - Added:
  - Fixed:
  - Compatibility impact:
"@
    }) -join "`n"
} else {
@"
- <tool_key_1>:
  - Added:
  - Fixed:
  - Compatibility impact:
"@
}

$toolRollbackLines = if ($Tools.Count -gt 0) {
    ($Tools | ForEach-Object { "- ${_}: <version/tag>" }) -join "`n"
} else {
    "- <tool_key_1>: <version/tag>"
}

$hostChangelogBlock = if ($Type -eq "tool") {
    "- N/A"
} else {
@"
- Added:
- Fixed:
- Compatibility impact:
"@
}

$content = @"
# Release Scope And Changelog

## 1) Basic Info

- Release ID: $ReleaseId
- Release Time: $timeStamp
- Owner: $ownerText
- Channel: $Channel
- Type: $Type

## 2) Scope (minimum coupled range)

- host:
  - publish: $hostPublish
- tools (affected tool_key only):
$toolListLines

## 3) Version Info (host/tool separated)

- host_version: $hostVersionText
- tool_versions:
$toolVersionLines

## 4) Changelog (host/tool separated)

- host_changelog (N/A when empty):
$hostChangelogBlock
- tool_changelog (by tool, N/A when empty):
$toolChangelogLines

## 5) Verification Checklist

- [ ] powershell -File scripts/run-ci-tool-checks.ps1
- [ ] in frontend: pnpm install --frozen-lockfile (if needed) and pnpm run build
- [ ] health check: /health
- [ ] smoke test for affected host/tools
- [ ] external visibility check (ecs): Host: 47.116.180.173
- [ ] version endpoint check: /api/v1/meta/version

## 6) Rollback Boundary

- host_rollback_to: <version/tag>
- tool_rollback_to:
$toolRollbackLines

## 7) Expanded Scope Note (optional)

- Why expanded:
- Impact:
- Risk control:
- Estimated rollback time:
"@

Set-Content -Path $outputPath -Value $content -Encoding UTF8
Write-Host "Created release note: $outputPath"
