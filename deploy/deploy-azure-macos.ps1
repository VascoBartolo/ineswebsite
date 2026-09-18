<#
    deploy-azure-macos.ps1 — deploy IB Nutrição to Azure from a Mac.

    WHY THIS EXISTS
    Azure Container Apps runs linux/amd64. On Apple Silicon a plain `docker build`
    produces an arm64 image, which ACA accepts into the registry and then fails to
    start — the deploy reports success while the app crash-loops. deploy-azure.ps1
    is correct on Windows, where the host architecture already matches.

    This script cross-builds both images for linux/amd64 with buildx, pushes them,
    then hands off to deploy-azure.ps1 -SkipBuild for every other step, so the
    Azure logic lives in exactly one place.

    Cross-building runs under emulation and is slower than a native build.

    Prereqs: pwsh, Docker running, `az login` on subscription 8a6d121a-...,
    backend/.env and backend/credentials.json present.

    Usage (from the repo root):
        pwsh ./deploy/deploy-azure-macos.ps1
        pwsh ./deploy/deploy-azure-macos.ps1 -PgPassword '<db password>'
#>

[CmdletBinding()]
param(
    [string]$ResourceGroup = "rg-ibnutricao-prod",
    [string]$AcrName       = "acribnutricao",
    [string]$ImageTag      = (Get-Date -Format "yyyyMMdd-HHmm"),
    [string]$BackendImage  = "ibnutricao-backend",
    [string]$FrontendImage = "ibnutricao-frontend",
    [string]$PgPassword    = "",
    [string]$Platform      = "linux/amd64"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

function Section($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan }

$acrServer   = "$AcrName.azurecr.io"
$backendRef  = "${acrServer}/${BackendImage}:${ImageTag}"
$frontendRef = "${acrServer}/${FrontendImage}:${ImageTag}"

Section "Host check"
$hostArch = (uname -m)
Write-Host "Host $hostArch -> building $Platform (emulated if these differ)"
if (-not (docker buildx version 2>$null)) { throw "docker buildx not available; it is required to cross-build for $Platform." }

Section "Cross-build + push ($Platform)"
az acr login -n $AcrName
# --push because a cross-platform buildx image cannot be loaded into the local
# docker image store; it goes straight to the registry.
docker buildx build --platform $Platform -t $backendRef  ./backend --push
if ($LASTEXITCODE -ne 0) { throw "backend build/push failed" }
docker buildx build --platform $Platform -t $frontendRef ./website --push
if ($LASTEXITCODE -ne 0) { throw "frontend build/push failed" }

Section "Verify architecture before deploying"
# Guards the whole point of this script: refuse to point production at an image
# ACA cannot execute.
foreach ($ref in @($backendRef, $frontendRef)) {
    $name = ($ref -split '/')[-1]
    $arch = (az acr manifest show -r $AcrName -n $name --query "architecture" -o tsv 2>$null)
    if (-not $arch) {
        $arch = (az acr manifest show -r $AcrName -n $name --query "manifests[0].platform.architecture" -o tsv 2>$null)
    }
    Write-Host "  $name -> $arch"
    if ($arch -and $arch -ne "amd64") { throw "$name is '$arch', expected amd64. Refusing to deploy." }
}

Section "Handing off to deploy-azure.ps1 -SkipBuild"
$fwd = @{ ResourceGroup = $ResourceGroup; AcrName = $AcrName; ImageTag = $ImageTag
          BackendImage = $BackendImage; FrontendImage = $FrontendImage; SkipBuild = $true }
if ($PgPassword) { $fwd.PgPassword = $PgPassword }
& (Join-Path $PSScriptRoot "deploy-azure.ps1") @fwd
