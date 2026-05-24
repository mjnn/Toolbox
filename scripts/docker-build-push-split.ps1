param(
    [Parameter(Mandatory = $true)]
    [string]$HostVersion,

    [string]$ServiceIdVersion = "",
    [string]$MosVersion = "",
    [string]$RsaVersion = "",
    [string]$DataSecureVersion = "",

    [string]$Registry = "crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com",
    [string]$HostRepo = "mirror_ns/tool_box_host",
    [string]$ToolsRepo = "mirror_ns/tool_box_tools",
    [string]$Username = "MjnnAliCloud"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ServiceIdVersion)) { $ServiceIdVersion = $HostVersion }
if ([string]::IsNullOrWhiteSpace($MosVersion)) { $MosVersion = $HostVersion }
if ([string]::IsNullOrWhiteSpace($RsaVersion)) { $RsaVersion = $HostVersion }
if ([string]::IsNullOrWhiteSpace($DataSecureVersion)) { $DataSecureVersion = $HostVersion }

$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

$localImage = "toolbox-build:split-$HostVersion"
$hostImage = "$Registry/$HostRepo`:$HostVersion"
$toolImageSid = "$Registry/$ToolsRepo`:service-id-registry-$ServiceIdVersion"
$toolImageMos = "$Registry/$ToolsRepo`:mos-integration-toolbox-$MosVersion"
$toolImageRsa = "$Registry/$ToolsRepo`:rsa-token-livestream-$RsaVersion"
$toolImageDs = "$Registry/$ToolsRepo`:data-secure-manage-$DataSecureVersion"

Write-Host "[1/4] Building base image: $localImage"
docker build -t $localImage .

Write-Host "[2/4] Tagging split images"
docker tag $localImage $hostImage
docker tag $localImage $toolImageSid
docker tag $localImage $toolImageMos
docker tag $localImage $toolImageRsa
docker tag $localImage $toolImageDs

Write-Host "[3/4] Docker login: $Registry"
docker login --username=$Username $Registry

Write-Host "[4/4] Pushing images"
docker push $hostImage
docker push $toolImageSid
docker push $toolImageMos
docker push $toolImageRsa
docker push $toolImageDs

Write-Host "Done."
Write-Host "Host image : $hostImage"
Write-Host "Tool image : $toolImageSid"
Write-Host "Tool image : $toolImageMos"
Write-Host "Tool image : $toolImageRsa"
Write-Host "Tool image : $toolImageDs"
