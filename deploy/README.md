# Azure deployment — IB Nutrição

Frontend (nginx) + backend (Flask/gunicorn) on **Azure Container Apps**, with **Azure Database for
PostgreSQL Flexible Server** (Burstable B1ms — cheapest dev tier). Mirrors the local `docker-compose`
topology.

## Live resources (subscription `8a6d121a-…`)

| Piece | Value |
|---|---|
| Resource group | `rg-ibnutricao-prod` |
| Region (apps + DB) | **France Central** |
| ACA environment | **`parcel-env`** (in `parcel-rg`) — *shared*, see note below |
| Frontend (public) | `https://ib-frontend.gentlesky-0a0d734f.francecentral.azurecontainerapps.io` |
| Backend (internal) | `ib-backend.internal.gentlesky-0a0d734f.francecentral.azurecontainerapps.io` |
| Postgres | `psql-ibnutricao-01.postgres.database.azure.com` (DB `ibnutricao`, user `ibadmin`) |
| Registry | `acribnutricao.azurecr.io` (Basic, West Europe) |

**Why France Central + a shared environment:** this subscription is capped at **one** Container Apps
environment, already occupied by the `parcel-env` (France Central) from another project. The two IB
apps were placed **inside that environment** (apps can live in a different resource group than their
environment, but must share its region). West/North Europe also refused new ACA environments for this
subscription ("region not accepting new customers").

## Architecture

```
Internet ─▶ ib-frontend (nginx, external :80)
               │  /api/  ──HTTPS──▶ ib-backend (gunicorn, INTERNAL ingress)
               │                        ├─▶ Postgres Flexible Server (:5432, sslmode=require)
               └── serves SPA           ├─▶ Gmail SMTP  (sender: ibnutricao.noreply@gmail.com)
                                        └─▶ Google Calendar (service account)
```

nginx proxies `/api/` to the backend's internal FQDN **over HTTPS**, sending `Host: <backend-fqdn>`
and SNI — required because ACA's internal ingress routes by Host and redirects HTTP→HTTPS. The
service-account key is injected as an ACA secret (base64) and written to `/app/credentials.json` by
`backend/entrypoint.sh` at boot (never baked into the image; `.dockerignore` excludes it).

## Redeploy

```powershell
# from repo root; Docker Desktop must be running (ACR Tasks are blocked on this sub)
.\deploy\deploy-azure.ps1 -PgPassword '<saved-postgres-password>'
```

The script builds both images locally, pushes to ACR, and updates the apps. Omit `-PgPassword` only
on a first-ever run (it will generate + print one). Smoke test:

```powershell
curl https://ib-frontend.gentlesky-0a0d734f.francecentral.azurecontainerapps.io/api/health   # {"status":"ok"}
```

## Custom domain (ibnutricao.pt) + free TLS

Requires control of the domain's DNS (currently pointed at Vercel — move it here).

```powershell
$RG="rg-ibnutricao-prod"; $APP="ib-frontend"
$ENVID="/subscriptions/8a6d121a-51ff-446b-ab5b-dbce1beae7d0/resourceGroups/parcel-rg/providers/Microsoft.App/managedEnvironments/parcel-env"
az containerapp hostname add -n $APP -g $RG --hostname ibnutricao.pt
az containerapp show -n $APP -g $RG --query "properties.customDomainVerificationId" -o tsv   # asuid TXT
az containerapp show -n $APP -g $RG --query "properties.configuration.ingress.fqdn" -o tsv    # CNAME/A target
```

At the registrar, create `TXT asuid.ibnutricao.pt = <verificationId>`, then the apex `A`/`www` CNAME
to the target, and bind with a free managed cert:

```powershell
az containerapp hostname bind -n $APP -g $RG --hostname ibnutricao.pt --environment $ENVID --validation-method CNAME
```

Once HTTPS serves, switch the backend's public URLs to the domain and unlink Vercel:

```powershell
az containerapp update -n ib-backend -g $RG --set-env-vars "SITE_URL=https://ibnutricao.pt" "FRONTEND_URL=https://ibnutricao.pt"
```

## Cost control

- Stop Postgres when idle: `az postgres flexible-server stop -g rg-ibnutricao-prod -n psql-ibnutricao-01`
  (`start` to resume). Rough total ≈ **€20–35/mo** (Postgres ~€13–16, ACR Basic ~€4, ACA mostly within
  the free grant). ACA min-replicas is 1 to avoid booking cold-starts.

## Teardown

```powershell
# Removes only the IB resources. Does NOT touch parcel-env / parcel-rg.
az containerapp delete -n ib-frontend -g rg-ibnutricao-prod --yes
az containerapp delete -n ib-backend  -g rg-ibnutricao-prod --yes
az group delete --name rg-ibnutricao-prod --yes --no-wait
```

## Troubleshooting

- **`/api/*` returns 404 (Azure page) or 301:** nginx must proxy over **HTTPS** with
  `Host $proxy_host` + `proxy_ssl_server_name on` (already in `website/nginx.conf`), and
  `BACKEND_INTERNAL_URL` must be `https://…`. A 404 = wrong Host; a 301 = proxying over HTTP.
- **Backend can't reach Postgres:** confirm the `allow-azure-services` firewall rule (0.0.0.0) exists.
- **Calendar 403 / no events:** Calendar API enabled in GCP `ineswebsite-501315`, and the calendar
  shared with `ib-nutricao-calendar@ineswebsite-501315.iam.gserviceaccount.com` ("Make changes to events").
- **Emails:** logs via `az containerapp logs show -n ib-backend -g rg-ibnutricao-prod --type console`.
  Rotate the Gmail App Password before go-live; never commit `backend/.env` or `credentials.json`.
