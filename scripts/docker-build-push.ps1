param(
    [Parameter(Mandatory = $true)]
    [string]$VersionTag
)

$ErrorActionPreference = "Stop"

$Registry = "crpi-02k3y8iudey5q0vb.cn-shanghai.personal.cr.aliyuncs.com"
$Repository = "mirror_ns/tool_box"
$Image = "$Registry/$Repository`:$VersionTag"
$Username = "MjnnAliCloud"

Write-Host "Building image: $Image"
Write-Host "Building Docker image"
docker build -t $Image .

Write-Host "Logging in to registry: $Registry"
docker login --username=$Username $Registry

Write-Host "Pushing image: $Image"
docker push $Image

Write-Host "Done. Pushed image: $Image"

