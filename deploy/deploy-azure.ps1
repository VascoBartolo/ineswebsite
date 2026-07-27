<#
    deploy-azure.ps1 — build + deploy IB Nutrição to Azure Container Apps.

    Reflects the live setup for subscription 8a6d121a-...:
      * ACR Tasks (`az acr build`) are BLOCKED on this subscription, so images are
        built locally with Docker and pushed (Docker Desktop must be running).
      * The subscription allows only ONE Container Apps environment, already used by
        `parcel-env` (France Central). We REUSE it — the two apps run there.
      * Postgres Flexible Server (Burstable B1ms, cheapest dev) lives in France Central.
      * ACR (Basic) is in West Europe; cross-region pulls are fine.

    Prereqs: `az login` on the right subscription; Docker running; backend/.env and
    backend/credentials.json present. Run from the repo root:  .\deploy\deploy-azure.ps1

    First run generates + prints the Postgres admin password — SAVE IT, and pass it back
    with -PgPassword on later runs.
#>

[CmdletBinding()]
param(
    [string]$ResourceGroup = "rg-ibnutricao-prod",
    [string]$Location      = "francecentral",                 # must match the shared ACA env region
    [string]$AcrName       = "acribnutricao",
    [string]$AcrLocation   = "westeurope",
    [string]$EnvResourceId = "/subscriptions/8a6d121a-51ff-446b-ab5b-dbce1beae7d0/resourceGroups/parcel-rg/providers/Microsoft.App/managedEnvironments/parcel-env",
    [string]$PgServer      = "psql-ibnutricao-01",
    [string]$PgAdmin       = "ibadmin",
    [string]$PgDb          = "ibnutricao",
    [string]$PgPassword    = "",                               # blank => generate
    [string]$ImageTag      = "v1",
    [string]$BackendApp    = "ib-backend",
    [string]$FrontendApp   = "ib-frontend"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

# Neutralize any stray default resource group/location in the user's az config so
# lookups resolve against THIS deployment (does not modify the config file).
$env:AZURE_DEFAULTS_GROUP    = $ResourceGroup
$env:AZURE_DEFAULTS_LOCATION = $Location

$acrServer = "$AcrName.azurecr.io"
function Section($t) { Write-Host "`n=== $t ===" -ForegroundColor Cyan }

# ---------------------------------------------------------------------------
# 1. Read config from backend/.env
# ---------------------------------------------------------------------------
Section "Reading backend/.env"
$cfg = @{}
Get-Content (Join-Path $repoRoot "backend\.env") | ForEach-Object {
    $l = $_.Trim()
    if ($l -and -not $l.StartsWith("#") -and $l.Contains("=")) {
        $i = $l.IndexOf("="); $cfg[$l.Substring(0,$i).Trim()] = $l.Substring($i+1).Trim()
    }
}
$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $repoRoot "backend\credentials.json")))
if ([string]::IsNullOrEmpty($PgPassword)) {
    $chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789".ToCharArray()
    $PgPassword = (-join (1..27 | ForEach-Object { $chars | Get-Random })) + "aA7"
    Write-Host "Generated Postgres admin password (SAVE THIS): $PgPassword" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 2. Resource group + ACR (Basic) in West Europe
# ---------------------------------------------------------------------------
Section "Resource group + ACR"
az group create --name $ResourceGroup --location $Location --only-show-errors | Out-Null
$acrExists = az acr show -n $AcrName -g $ResourceGroup --query name -o tsv 2>$null
if (-not $acrExists) {
    az acr create -g $ResourceGroup -n $AcrName --sku Basic --admin-enabled true --location $AcrLocation --only-show-errors | Out-Null
}

# ---------------------------------------------------------------------------
# 3. Build images LOCALLY and push (ACR Tasks are blocked on this subscription)
# ---------------------------------------------------------------------------
Section "Docker build + push"
az acr login -n $AcrName                                       # AAD token auth for docker
docker build -t "${acrServer}/ib-backend:${ImageTag}"  ./backend
docker push  "${acrServer}/ib-backend:${ImageTag}"
docker build -t "${acrServer}/ib-frontend:${ImageTag}" ./website
docker push  "${acrServer}/ib-frontend:${ImageTag}"

# ---------------------------------------------------------------------------
# 4. Postgres Flexible Server (Burstable B1ms) + DB + firewall
# ---------------------------------------------------------------------------
Section "Postgres Flexible Server"
$pgExists = az postgres flexible-server show -n $PgServer -g $ResourceGroup --query name -o tsv 2>$null
if (-not $pgExists) {
    az postgres flexible-server create -g $ResourceGroup -n $PgServer --location $Location `
        --tier Burstable --sku-name Standard_B1ms --storage-size 32 --version 16 `
        --admin-user $PgAdmin --admin-password $PgPassword `
        --high-availability Disabled --public-access None --yes --only-show-errors | Out-Null
    az postgres flexible-server db create -g $ResourceGroup -s $PgServer -d $PgDb --only-show-errors | Out-Null
}
# Allow Azure-internal services (covers ACA egress, which can vary) + this machine.
az postgres flexible-server firewall-rule create -g $ResourceGroup -n $PgServer `
    --rule-name allow-azure-services --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0 --only-show-errors | Out-Null
$myIp = (Invoke-RestMethod -Uri "https://api.ipify.org").Trim()
az postgres flexible-server firewall-rule create -g $ResourceGroup -n $PgServer `
    --rule-name deployer --start-ip-address $myIp --end-ip-address $myIp --only-show-errors | Out-Null
$pgFqdn = az postgres flexible-server show -n $PgServer -g $ResourceGroup --query "fullyQualifiedDomainName" -o tsv
$databaseUrl = "postgresql://${PgAdmin}:${PgPassword}@${pgFqdn}:5432/${PgDb}?sslmode=require"

# ---------------------------------------------------------------------------
# 5. Backend app (internal ingress) in the shared environment
# ---------------------------------------------------------------------------
Section "Backend app"
$backendExists = az containerapp show -n $BackendApp -g $ResourceGroup --query name -o tsv 2>$null
if (-not $backendExists) {
    az containerapp create --name $BackendApp --resource-group $ResourceGroup --environment $EnvResourceId `
        --image "${acrServer}/ib-backend:${ImageTag}" --registry-server $acrServer `
        --target-port 5000 --ingress internal --min-replicas 1 --max-replicas 3 --cpu 0.25 --memory 0.5Gi `
        --secrets "database-url=$databaseUrl" "smtp-user=$($cfg['SMTP_USER'])" "smtp-pass=$($cfg['SMTP_PASS'])" "google-b64=$b64" `
        --env-vars `
            "DATABASE_URL=secretref:database-url" "SMTP_USER=secretref:smtp-user" "SMTP_PASS=secretref:smtp-pass" `
            "GOOGLE_CREDENTIALS_B64=secretref:google-b64" "SMTP_HOST=$($cfg['SMTP_HOST'])" "SMTP_PORT=$($cfg['SMTP_PORT'])" `
            "GOOGLE_CALENDAR_ID=$($cfg['GOOGLE_CALENDAR_ID'])" "NUTRITIONIST_EMAIL=$($cfg['NUTRITIONIST_EMAIL'])" `
            "SITE_URL=$($cfg['SITE_URL'])" "FRONTEND_URL=$($cfg['FRONTEND_URL'])" "GOOGLE_CREDENTIALS_FILE=/app/credentials.json" `
        --only-show-errors | Out-Null
} else {
    az containerapp secret set -n $BackendApp -g $ResourceGroup `
        --secrets "database-url=$databaseUrl" "smtp-user=$($cfg['SMTP_USER'])" "smtp-pass=$($cfg['SMTP_PASS'])" "google-b64=$b64" --only-show-errors | Out-Null
    az containerapp update -n $BackendApp -g $ResourceGroup --image "${acrServer}/ib-backend:${ImageTag}" --only-show-errors | Out-Null
}
$backendFqdn = az containerapp show -n $BackendApp -g $ResourceGroup --query "properties.configuration.ingress.fqdn" -o tsv

# ---------------------------------------------------------------------------
# 6. Frontend app (external ingress). nginx proxies /api over HTTPS to the
#    backend's internal FQDN (ACA ingress terminates TLS + redirects HTTP->HTTPS).
# ---------------------------------------------------------------------------
Section "Frontend app"
$backendUrl = "https://$backendFqdn"
$frontendExists = az containerapp show -n $FrontendApp -g $ResourceGroup --query name -o tsv 2>$null
if (-not $frontendExists) {
    az containerapp create --name $FrontendApp --resource-group $ResourceGroup --environment $EnvResourceId `
        --image "${acrServer}/ib-frontend:${ImageTag}" --registry-server $acrServer `
        --target-port 80 --ingress external --min-replicas 1 --max-replicas 3 --cpu 0.25 --memory 0.5Gi `
        --env-vars "BACKEND_INTERNAL_URL=$backendUrl" --only-show-errors | Out-Null
} else {
    az containerapp update -n $FrontendApp -g $ResourceGroup --image "${acrServer}/ib-frontend:${ImageTag}" `
        --set-env-vars "BACKEND_INTERNAL_URL=$backendUrl" --revision-suffix ("r" + (Get-Date -Format "MMddHHmm")) --only-show-errors | Out-Null
}
$frontendFqdn = az containerapp show -n $FrontendApp -g $ResourceGroup --query "properties.configuration.ingress.fqdn" -o tsv

Section "Done"
Write-Host "Frontend : https://$frontendFqdn"
Write-Host "Backend  : $backendFqdn (internal)"
Write-Host "Postgres : $pgFqdn"
Write-Host "Smoke    : curl https://$frontendFqdn/api/health   # {\"status\":\"ok\"}" -ForegroundColor Green
