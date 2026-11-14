# Medicare PFS Explorer — Resume Guide

**Checkpoint:** November 14, 2026  
**Repository:** [Mkane8971/IIT-Programming](https://github.com/Mkane8971/IIT-Programming)  
**Live app:** https://pfs-frontend.wonderfulpebble-55b2f0ff.westus2.azurecontainerapps.io

## Current state

The application is deployed and working: React/TypeScript with Nginx is public over HTTPS; FastAPI runs as an **internal** Azure Container App; MongoDB Atlas is an optional 25-record, 24-hour CMS response cache; and CMS provides Physician Fee Schedule procedures, localities, and pricing inputs. If Atlas is unreachable because Azure's outbound IP changes, FastAPI uses CMS directly and reports `cache_status: "unavailable"`. A 60-second circuit breaker limits failed database calls. The app also has an expandable **How to Use This Explorer** guide.

| Component | Location / name |
|---|---|
| Azure resource group / region | `rg-medicare-pfs` / `westus2` |
| Container Apps environment | `cae-medicare-pfs` |
| Backend / frontend apps | `pfs-api` (internal), `pfs-frontend` (public) |
| MongoDB Atlas | Free-tier cluster; database `medicare` |
| Container images | `ghcr.io/mkane8971/medicare-pfs-api` and `.../medicare-pfs-frontend` |
| GitHub Actions | `.github/workflows/ci.yml`: test → publish to GHCR → Azure deploy |
| Deployment identity | `github-pfs-deploy` (managed identity + GitHub OIDC) |

## Git branches and release process

- **`main`**: merged Azure application, last observed at commit `93f4cbe` (PR #4).
- **`localdev1`**: preserved snapshot of the **pre-merge** `main`, at commit `44ffa4e`.
- **`feature/azure-deployment`**: original feature branch; retain until release workflow is verified.
- A proposed **`feature/main-cicd`** branch was discussed for switching automated deployment from the feature branch to `main`. **Its creation/merge was not confirmed.** Check the actual workflow and Azure OIDC credential before assuming pushes to `main` deploy automatically.

To resume work safely:

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
git switch -c feature/your-next-change
# edit code, then test
git add <changed-files>
git commit -m "Describe change"
git push -u origin feature/your-next-change
```

Open a PR targeting `main`; confirm the CI tests pass before merging. Avoid committing directly to `main`.

## Local development and tests

```powershell
docker compose up -d --build
# Frontend: http://localhost:8080
# Backend health: http://localhost:8000/health
docker compose run --rm api python -m pytest tests/ -v -p no:cacheprovider
```

Local Docker uses `frontend/nginx.conf` (`api:8000`); Azure builds use `frontend/nginx.azure.conf` (HTTPS upstream). To check the Azure frontend build:

```powershell
docker build --build-arg NGINX_CONFIG=nginx.azure.conf -t medicare-pfs-frontend:azure ./frontend
docker run --rm --entrypoint nginx medicare-pfs-frontend:azure -t -c /etc/nginx/nginx.conf
```

Quick application checks: search **CPT 27447**, year **2026**, facility, Arizona; also test **2010** and **2024**. Historical CMS release values such as `210B`/`224B` are preserved as `cms_release`, while the requested `year` remains numeric. Confirm pricing, not just procedure retrieval, and verify historical release/locality effective-period alignment before treating old estimates as authoritative.

## Operational commands

```powershell
az containerapp revision list --name pfs-api --resource-group rg-medicare-pfs --output table
az containerapp revision list --name pfs-frontend --resource-group rg-medicare-pfs --output table
az containerapp logs show --name pfs-api --resource-group rg-medicare-pfs --type console --tail 30
az containerapp logs show --name pfs-frontend --resource-group rg-medicare-pfs --type console --tail 30
```

**Security and cost:** Keep Atlas IP access limited to verified addresses; **never** leave `0.0.0.0/0` enabled. Azure Container Apps outbound IPs can change, so cache availability is intermittent by design. Keep credentials in `.env` (gitignored) or Azure secrets, never in the repository. Azure for Students Cost Analysis showed **$0.02** of `pfs-api` active CPU/memory usage on November 14; check spending periodically and consider a small budget alert. Both apps were configured for **min 0 / max 1** replicas.

## Next work

1. **Verify production CD branch:** Check whether `ci.yml` deploys from `main`; if not, create `feature/main-cicd`, update the push trigger, add a **main-branch federated OIDC credential**, open a PR, and verify the first main deployment.
2. **Regression coverage:** Keep tests for MongoDB fallback/recovery and historical CMS release IDs (2010, 2024, 2026).
3. **Possible next feature (parked):** CPT-to-ICD-10-CM associations via the CMS Medicare Coverage API. Confirmed article **A59811** accepts numeric `articleid=59811`; `GET /v1/data/article/icd10-covered` returned paginated diagnosis groups after license-token authorization. Check `/v1/data/article/hcpc-code` and match article groups, versions, jurisdiction, and effective dates before claiming procedure-specific coverage.

**Detailed reference:** `docs/docs.md` in the repository contains the longer build and deployment guide.
