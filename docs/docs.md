# Medicare PFS Explorer: Complete Build and Deployment Guide

**Project:** Medicare Physician Fee Schedule (PFS) Explorer  
**Repository:** [Mkane8971/IIT-Programming](https://github.com/Mkane8971/IIT-Programming)  
**Implementation environment:** Windows 11, PowerShell, Docker Desktop  
**Cloud:** Microsoft Azure (West US 2) + MongoDB Atlas  
**Build/deployment walkthrough completed:** November 14, 2026  
**Status:** Public React application, internal FastAPI backend, MongoDB cache with CMS fallback, and functioning GitHub Actions CI/CD.

> **About this guide:** This reconstructs the actual sequence of design and implementation decisions from our work together. Commands and important configurations are included so the process can be studied or repeated. Some initial scaffolding details were not captured verbatim; those sections are labeled as representative rather than exact transcripts. Never commit `.env` files, MongoDB credentials, or Azure secrets.

## 1. What we set out to build

The course project needed a **publicly accessible web application**, a **database**, and **deployment from GitHub through CI/CD**. We chose a Medicare Physician Fee Schedule explorer that can retrieve procedure information from CMS and calculate locality-adjusted Medicare payment estimates.

The application accepts a five-character HCPCS/CPT code, calendar year, optional modifier, facility/non-facility setting, and Medicare payment locality. It displays procedure descriptions, RVUs, conversion factors (including distinct price-indicator records), and calculated estimates.

### Final architecture

```text
GitHub repository (feature/azure-deployment)
                |
                v
GitHub Actions: pytest + Docker builds + Nginx validation
                |
                v
GHCR: two versioned container images (tagged by commit SHA)
                |
                v
GitHub OIDC -> Azure managed identity -> az containerapp update
                |
                v
Azure Container Apps environment: cae-medicare-pfs
  +---------------------------------------------------------+
  | pfs-frontend (PUBLIC HTTPS)                             |
  | React / TypeScript build served by Nginx, port 8080     |
  |     |                                                   |
  |     | HTTPS reverse proxy, /api/*                       |
  |     v                                                   |
  | pfs-api (INTERNAL ingress)                              |
  | FastAPI / Python, port 8000                             |
  +---------------------------------------------------------+
                |                           |
                v                           v
       MongoDB Atlas M0             CMS public PFS Data API
       Optional 24-hour cache       Authoritative data source
       25-document LRU cap          Procedure and locality data

If Atlas is unavailable: FastAPI bypasses cache and queries CMS.
```

### Technology choices

| Layer | Technology | Why it was used |
|---|---|---|
| Web application | React + TypeScript + Vite | Typed interactive search UI |
| Frontend web server | Unprivileged Nginx | Serve static assets and reverse-proxy `/api/` |
| Backend | Python + FastAPI + Uvicorn | Typed HTTP endpoints and async CMS integration |
| Database | MongoDB 8 locally; MongoDB Atlas M0 in Azure deployment | Satisfy database requirement and cache CMS responses |
| Data client | `httpx.AsyncClient` | Query CMS APIs asynchronously |
| Database client | PyMongo `AsyncMongoClient` | Async database operations |
| Containers | Dockerfiles + Docker Compose | Reproducible local services |
| Hosting | Azure Container Apps (Consumption / Express) | Public frontend and internal API |
| Image registry | GitHub Container Registry (GHCR) | Store deployable Docker images |
| Automation | GitHub Actions | Test, build, publish, deploy |
| Deployment authorization | Azure user-assigned managed identity + GitHub OIDC | Short-lived credentials, no Azure client secret |

---

## 2. Prepare the local engineering environment

We began in a local Git repository on Windows, with Docker Desktop, Python, Node.js, Git, and PowerShell available. The working repository was `IIT-Programming`, with the application organized as its own microservice project.

Representative tool checks:

```powershell
git --version
python --version
node --version
npm --version
docker --version
docker compose version
```

We deliberately used **Docker Compose** for local orchestration and **separate Dockerfiles** for each application image. We did not use the `uv` package manager.

### Repository structure

The precise initial scaffolding history was not preserved verbatim, but the relevant final files and modules discussed were:

```text
IIT-Programming/
├── .github/
│   └── workflows/
│       └── ci.yml
├── backend/
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── clients/
│   │   │   └── cms.py
│   │   ├── repositories/
│   │   │   └── procedures.py
│   │   ├── routers/
│   │   │   ├── procedures.py
│   │   │   └── pricing.py
│   │   └── services/
│   │       └── pricing.py
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── nginx.azure.conf
│   ├── package.json
│   ├── package-lock.json
│   └── src/
│       └── ... React / TypeScript files
├── compose.yaml           # Docker Compose definition; exact filename may vary
├── .env                   # Local values only, gitignored
└── .gitignore
```

The code uses a separation of concerns: **routers** expose HTTP endpoints, **clients** retrieve CMS data, **repositories** handle MongoDB caching, and **services** perform reimbursement calculations.

---

## 3. Build the FastAPI backend

### 3.1 Initialize a Python backend

We created `backend/app/` as the Python package structure, installed FastAPI, Uvicorn, PyMongo, httpx, and pytest, and ran the service in a Docker image. The backend container listens on `0.0.0.0:8000`.

A representative starting point for `app/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="Medicare PFS Explorer")

@app.get("/health")
async def health():
    return {"status": "ok"}
```

The actual application subsequently integrated lifespan management and routers. The example above illustrates the initial skeleton, not a replacement for the current `main.py`.

### 3.2 Design the API

Working endpoints included:

| Method | Path | Responsibility |
|---|---|---|
| GET | `/health` | Lightweight API health check |
| GET | `/api/v1/procedures/{hcpcs}?year=2026&setting=facility` | Procedure records and RVUs |
| GET | `/api/v1/localities?year=2026` | Medicare locality selection |
| GET | `/api/v1/pricing/estimate?hcpcs=27447&year=2026&locality=0310200&setting=facility` | Locality-adjusted payment estimates |

Input constraints include five alphanumeric HCPCS/CPT characters, a year from 2000 through 2100, an optional two-character alphanumeric modifier, and an allowed facility setting.

### 3.3 Connect to CMS data

Rather than downloading and reprocessing the entire PFS file for every query, the application uses the **CMS PFS Data API**, dynamically discovers the relevant annual resource ID, and issues filtered datastore SQL queries.

CMS endpoint used:

```text
https://pfs.data.cms.gov/api/1/datastore/sql
```

An identified dataset resource in our earlier implementation work was `7c7df311-5315-4f38-b9ed-fd62f8bebe11`; the application evolved toward **discovering resources by year** instead of relying on one fixed resource ID.

`app/clients/cms.py` handles calls such as:

```python
resource_id = await cms.get_resource_id(year)
records = await cms.get_procedure(
    hcpcs, year, modifier, resource_id=resource_id
)
localities = await cms.get_localities(year)
```

A known test procedure was **27447** (total knee arthroplasty). We also tested **99213** (established patient office/outpatient visit). Some CMS records appear more than once because of different **price indicators / conversion-factor categories**; the frontend retains these distinctions.

### 3.4 Implement Medicare payment estimation

`app/services/pricing.py` performs the payment calculations using precise decimal arithmetic. Its inputs include physician work RVUs, practice-expense RVUs, malpractice RVUs, geographical practice cost indices (GPCIs), the applicable conversion factor, and facility/non-facility selection.

Conceptually:

```text
Payment = [Work RVU × Work GPCI
          + PE RVU × PE GPCI
          + MP RVU × MP GPCI] × Conversion Factor
```

The actual service applies the fields and rules supported by its CMS responses. We used Arizona locality `0310200` for payment-estimate testing. Source data and any policy modifiers should be checked before treating a displayed estimate as a final claim payment.

---

## 4. Add MongoDB locally

### 4.1 Create a MongoDB service in Docker Compose

The local deployment included three services:

```text
api       -> FastAPI on localhost:8000
mongo     -> MongoDB 8 inside the Compose network
frontend  -> Nginx/React on localhost:8080
```

The API received MongoDB settings through environment variables such as:

```dotenv
MONGO_HOST=mongo
MONGO_PORT=27017
MONGO_DATABASE=medicare
MONGO_USERNAME=<local-user>
MONGO_PASSWORD=<local-password>
```

`mongo` works as a hostname because Docker Compose provides service-name discovery within its network.

### 4.2 Connect with PyMongo AsyncMongoClient

`app/database.py` initially created an `AsyncMongoClient`, then pinged MongoDB inside the FastAPI lifespan before serving HTTP requests. This worked during local development and made database problems visible, but later required modification for reliability in Azure.

We kept two database connection modes:

- **Local:** `MONGO_HOST`, `MONGO_PORT`, username/password, `authSource="admin"`.
- **Cloud:** `MONGO_URI` for the MongoDB Atlas connection string.

The cloud client uses MongoDB Server API v1 and a server selection timeout. The database name for both was `medicare`.

### 4.3 Build the CMS response cache

`app/repositories/procedures.py` stores records in MongoDB collection `cms_cache`, keyed by:

```text
hcpcs + year + modifier + resource_id
```

The cache retains `records`, `retrieved_at`, and `last_accessed`. Its intended behavior:

- Cached data is reused when retrieved within the previous **24 hours**.
- Cache entries are updated on access.
- The cache retains at most **25 documents**, deleting the least recently accessed documents when necessary.
- Fresh CMS data is cached after retrieval.

### 4.4 Validate local functionality

Useful commands from our workflow:

```powershell
docker compose up -d --build
docker compose ps
Invoke-RestMethod -Uri "http://localhost:8080/api/v1/procedures/27447?year=2026"
```

To test the API directly:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

---

## 5. Initialize the React / TypeScript frontend

We scaffolded a **Vite + React + TypeScript** frontend and built a procedure-search interface. The app permits the user to input a procedure code, select a year, enter an optional modifier, select facility status, and choose a Medicare locality.

Representative Vite initialization command (the exact original interactive scaffold invocation was not retained):

```powershell
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm run dev
```

The frontend calls the FastAPI endpoints and displays loading, result, and error states. It renders CMS procedure records, both relevant price-indicator/conversion-factor results, and Medicare locality-adjusted estimates.

### 5.1 Frontend Dockerfile

We used a multi-stage build:

1. Node `24.12.0-alpine` builds the React app.
2. `nginxinc/nginx-unprivileged:alpine3.22` serves the generated `/app/dist` files on port **8080**.

We added a configurable Nginx file to keep Docker Compose and Azure deployment compatible:

```dockerfile
ARG NGINX_CONFIG=nginx.conf
COPY ${NGINX_CONFIG} /etc/nginx/nginx.conf
```

### 5.2 Local Nginx reverse proxy

In `frontend/nginx.conf`, Nginx forwards same-origin API requests to Docker Compose's `api` hostname:

```nginx
location /api/ {
    proxy_pass http://api:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

The app itself is served on port 8080 and React client-side routing is supported with `try_files $uri $uri/ /index.html;`.

---

## 6. Put the code in GitHub and set up initial CI

The repository was pushed to GitHub under the branch `feature/azure-deployment`. We created `.github/workflows/ci.yml` with two jobs:

1. **`test-and-build`:** Docker-build FastAPI, run pytest, build React, validate Nginx.
2. **`publish`:** After tests pass on a push, publish public GHCR Docker images with the repository's `GITHUB_TOKEN`.

Images:

```text
ghcr.io/mkane8971/medicare-pfs-api:development
ghcr.io/mkane8971/medicare-pfs-frontend:development
```

We verified GitHub Actions succeeded and that both GHCR packages could be pulled locally. The GHCR packages were made public so Azure could pull them without container-registry credentials.

**Important distinction:** At this point we had **continuous integration and image publication**, but **not yet continuous deployment** to Azure. The deployment job was added later.

---

## 7. Provision the Azure foundation

### 7.1 Create the Azure resource group

We created:

| Azure resource | Name / setting |
|---|---|
| Subscription ID | `b1a34bbc-c635-47be-9dba-b43f65aa8cbd` |
| Resource group | `rg-medicare-pfs` |
| Region | `westus2` |
| Resource provider | `Microsoft.App` (registered) |
| Container Apps environment | `cae-medicare-pfs` |
| Workload/billing model | Consumption / Express |
| Environment application logs destination | None (no Log Analytics workspace provisioned) |

Representative creation and inspection commands:

```powershell
az login
az group create --name rg-medicare-pfs --location westus2
az provider register --namespace Microsoft.App
az extension add --name containerapp --upgrade
```

The environment was created with `--logs-destination none`, which avoided provisioning a Log Analytics workspace. Azure CLI's message that the `containerapp` extension altered command behavior was informational.

**Cost considerations:** Resource-group creation does not incur a standalone charge. Container Apps Consumption uses compute/request metering with applicable free allowances. NAT gateways, private networks, dedicated database tiers, and extra logging were intentionally avoided to minimize costs.

### 7.2 Create MongoDB Atlas M0

We created the free-tier Atlas cluster **`medicare-pfs-db`**, configured a database user, and obtained a TLS-enabled `mongodb+srv://...` URI. The URI is stored in Azure as a **Container App secret**, never embedded in source code or GHCR images.

The Atlas project also uses an **IP Access List**. During our debugging we observed Azure outbound IP `20.83.114.69`, but found that the source IP can change. We retained a restricted IP allowlist for the course project and made MongoDB an optional cache so IP changes would not break CMS lookups.

**Security:** Prefer a user with `readWrite` limited to the `medicare` database, TLS enabled, and the narrowest practical access list. `0.0.0.0/0` was used as a temporary diagnostic test only, then removed.

---

## 8. Deploy FastAPI to Azure Container Apps

The backend Container App is named `pfs-api`. It runs on target port **8000** and uses **internal** ingress.

Our initial deployment command followed this structure:

```powershell
az containerapp create `
  --name pfs-api `
  --resource-group rg-medicare-pfs `
  --environment cae-medicare-pfs `
  --image ghcr.io/mkane8971/medicare-pfs-api:development `
  --ingress internal `
  --target-port 8000 `
  --cpu 0.5 `
  --memory 1.0Gi `
  --min-replicas 0 `
  --max-replicas 1 `
  --secrets "mongo-uri=$env:MONGO_URI" `
  --env-vars "MONGO_URI=secretref:mongo-uri" "MONGO_DATABASE=medicare" "CMS_PFS_API_URL=https://pfs.data.cms.gov/api/1/datastore/sql"
```

> The command assumes `$env:MONGO_URI` has been securely set in the current PowerShell session. **Never paste an actual Atlas URI into documentation, terminal screenshots, or Git.** When possible, use an appropriately secure secret-handling mechanism and avoid exposing the secret in command history/process arguments.

The backend ingress FQDN reported by Azure was:

```text
pfs-api.wonderfulpebble-55b2f0ff.westus2.azurecontainerapps.io
```

Even though it has a hostname, `pfs-api` uses **internal ingress** and is intended to be reached by the frontend inside the Container Apps environment.

### 8.1 Diagnose the first unhealthy revision

The original API revision reported:

```text
pfs-api--latest  Active=True  Health=Unhealthy  Replicas=1
```

We used:

```powershell
az containerapp revision list --name pfs-api --resource-group rg-medicare-pfs --output table
az containerapp logs show --name pfs-api --resource-group rg-medicare-pfs --type console --tail 50
```

**First error:** PyMongo attempted to connect to an invalid host represented by `\x16:27017`. We replaced the improperly stored MongoDB URI secret.

**Second error:** MongoDB Atlas reported an SSL/TLS handshake failure against valid Atlas shard hostnames. Temporarily broadening Atlas network access confirmed the **Atlas IP allowlist** was the blocker; we restored restrictive access afterward.

We discovered one observed Azure outbound IP from inside the API container:

```powershell
az containerapp exec --name pfs-api --resource-group rg-medicare-pfs
```

Then in its Linux shell:

```bash
python -c "import urllib.request; print(urllib.request.urlopen('https://api.ipify.org', timeout=10).read().decode())"
```

It returned `20.83.114.69` during one test, but later changed. An observed IP is **not a reserved egress IP**.

### 8.2 Express environment restart limitation

Attempting `az containerapp revision restart` returned an error that **Express environments do not support revision restart**. We also discovered `az containerapp stop` was unavailable in the local CLI extension. We used the **Azure Portal Stop and Start buttons** to recycle the application. Future image changes were performed through `az containerapp update`.

---

## 9. Deploy React + Nginx to Azure

The frontend Container App is named `pfs-frontend`, using the same managed environment, with **external HTTPS ingress** and target port **8080**.

Initial deployment command:

```powershell
az containerapp create `
  --name pfs-frontend `
  --resource-group rg-medicare-pfs `
  --environment cae-medicare-pfs `
  --image ghcr.io/mkane8971/medicare-pfs-frontend:development `
  --ingress external `
  --target-port 8080 `
  --transport auto `
  --cpu 0.25 `
  --memory 0.5Gi `
  --min-replicas 0 `
  --max-replicas 1
```

Public URL:

**https://pfs-frontend.wonderfulpebble-55b2f0ff.westus2.azurecontainerapps.io**

### 9.1 Preserve local development with a second Nginx config

We kept:

- `frontend/nginx.conf` for Docker Compose, proxying to `http://api:8000`.
- `frontend/nginx.azure.conf` for Container Apps, proxying to the Azure backend FQDN.

The frontend Dockerfile accepts `NGINX_CONFIG` as a build argument, and GitHub Actions builds the Azure image with:

```yaml
build-args: |
  NGINX_CONFIG=nginx.azure.conf
```

### 9.2 Fix Nginx startup DNS failure

Our first Azure-specific Nginx configuration used:

```nginx
proxy_pass http://pfs-api;
```

The frontend repeatedly failed to start:

```text
nginx: [emerg] host not found in upstream "pfs-api"
{"error":"App port is not ready"}
```

The solution was to use Azure's actual backend FQDN and defer DNS resolution until request time through a variable and an explicit resolver.

### 9.3 Fix HTTP redirect and browser CORS failure

After Nginx started, the React page loaded, but localities failed because Nginx proxied via `http://`, Azure redirected the response to `https://pfs-api...`, and the browser blocked the cross-origin redirect.

We corrected the Azure Nginx block to proxy upstream **over HTTPS** and send SNI:

```nginx
location /api/ {
    resolver 168.63.129.16 valid=30s ipv6=off;
    set $api_host pfs-api.wonderfulpebble-55b2f0ff.westus2.azurecontainerapps.io;

    proxy_pass https://$api_host;
    proxy_ssl_server_name on;
    proxy_ssl_name $api_host;

    proxy_set_header Host $api_host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
}
```

> This is the configuration used during our troubleshooting. For a production deployment, verify the environment's DNS behavior and TLS upstream validation (`proxy_ssl_verify` and trusted CA configuration) rather than assuming development defaults provide complete upstream certificate verification.

The browser then accessed `/api/v1/localities` on the **frontend origin** without needing broad FastAPI CORS access.

### 9.4 Verify Nginx before publishing

```powershell
docker build --build-arg NGINX_CONFIG=nginx.azure.conf -t medicare-pfs-frontend:azure ./frontend

docker run --rm --entrypoint nginx medicare-pfs-frontend:azure -t -c /etc/nginx/nginx.conf
```

When an earlier Nginx file resolved `pfs-api` at startup, local validation required the temporary mapping `--add-host pfs-api:127.0.0.1`. After switching to request-time DNS resolution, the syntax check no longer needed that mapping.

### 9.5 Update existing containers by immutable image digest

We published updated images to GHCR and retrieved the exact digest:

```powershell
docker buildx imagetools inspect ghcr.io/mkane8971/medicare-pfs-frontend:development
```

Then deployed without creating another Container App:

```powershell
az containerapp update `
  --name pfs-frontend `
  --resource-group rg-medicare-pfs `
  --image "ghcr.io/mkane8971/medicare-pfs-frontend@sha256:<image-digest>"
```

The same pattern was later used for the API. Image digest pinning helped ensure Azure pulled the exact corrected image, rather than relying on a mutable `development` tag.

---

## 10. Make MongoDB optional and FastAPI resilient

After the frontend worked, we observed the API become unhealthy again when Atlas blocked a changing Azure egress IP. We chose to **leave the Atlas allowlist restricted** and make database failures nonfatal because CMS is the primary data source.

### 10.1 Remove the database ping from startup

Previously, the FastAPI lifespan required:

```python
await client.admin.command({"ping": 1})
```

An unreachable database prevented the entire app from starting. We changed it to configure the client and yield without forcing a successful database connection:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    client = create_mongo_client()
    try:
        app.state.db = client[os.environ["MONGO_DATABASE"]]
        print("FastAPI initialized; MongoDB cache is optional.")
        yield
    finally:
        await client.close()
```

We reduced `serverSelectionTimeoutMS` from 5000 to 2000 milliseconds in the connection factory to fail faster when Atlas is unreachable.

### 10.2 Add repository-level circuit breaker

`backend/app/repositories/procedures.py` was updated so failed MongoDB operations:

- Catch `PyMongoError` and record a warning.
- Return a cache miss instead of raising a fatal error.
- Temporarily **bypass cache operations for 60 seconds**.
- Retry after the cooldown; successful operations restore cache status.
- Preserve the existing 24-hour TTL and 25-document LRU behavior.

The breaker is **process-local**. Separate replicas or workers would each have their own state.

### 10.3 Preserve the API response and report cache state

We added `cache_status` while leaving existing response keys intact. A CMS response while MongoDB is offline looks like:

```json
{
  "source": "cms",
  "cache_status": "unavailable",
  "setting": "facility",
  "records": ["... CMS procedure records ..."]
}
```

`cache_status` can report availability or a retry-pending condition; the CMS record retrieval is independent of cache connectivity.

### 10.4 Test the failure mode locally

We stopped the MongoDB Compose service:

```powershell
docker compose stop mongo
```

Then called:

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8080/api/v1/procedures/99213?year=2026" |
  ConvertTo-Json -Depth 5
```

**Observed successful result:** `source: "cms"`, `cache_status: "unavailable"`, and **two real 2026 records** for CPT `99213` (with distinct price indicators `1` and `9`).

We subsequently tested reconnection after starting MongoDB, the 60-second cooldown, and the pricing endpoint fallback. These manual tests passed.

```powershell
docker compose start mongo
```

**Engineering note:** Manual tests confirmed the behavior. Automated regression tests for read failures, write failures, cooldown state, and pricing fallback were recommended; the conversation does not establish that all of those specific tests were committed.

### 10.5 Correct a `.env` formatting mistake

At one point, Docker Compose failed parsing `.env` because a PowerShell statement had been accidentally pasted into it:

```text
$mongoDatabase = Read-Host "MongoDB database name"
```

A Compose `.env` file must contain `KEY=value` entries. We cleaned it up and validated with:

```powershell
docker compose config --quiet
```

Always ensure `.env` is gitignored:

```powershell
git check-ignore .env
```

---

## 11. Configure complete GitHub Actions CI/CD

### 11.1 Create an Azure deployment identity

Our first attempt to create an Entra application failed:

```text
Insufficient privileges to complete the operation.
```

Instead, we created a **user-assigned managed identity** without manually registering an Entra application:

```powershell
az identity create `
  --name github-pfs-deploy `
  --resource-group rg-medicare-pfs `
  --location westus2
```

Azure registered `Microsoft.ManagedIdentity` automatically. The identity's values were:

| Identifier | Value |
|---|---|
| Identity name | `github-pfs-deploy` |
| Client ID | `bba023d5-b9de-4839-a18b-9bc24b5fe99c` |
| Principal ID | `682b3e23-da3c-4406-9269-0ea48af78e20` |
| Tenant ID | `da90653e-1e02-4208-b68a-6224891bea63` |
| Subscription ID | `b1a34bbc-c635-47be-9dba-b43f65aa8cbd` |

These are identifiers, not client secrets.

### 11.2 Grant least-privilege Azure RBAC

We assigned **Container Apps Contributor** at the resource scope of only `pfs-api` and `pfs-frontend`:

```powershell
$principalId = "682b3e23-da3c-4406-9269-0ea48af78e20"
foreach ($app in @("pfs-api", "pfs-frontend")) {
    $scope = az containerapp show `
      --name $app `
      --resource-group rg-medicare-pfs `
      --query id --output tsv

    az role assignment create `
      --assignee-object-id $principalId `
      --assignee-principal-type ServicePrincipal `
      --role "Container Apps Contributor" `
      --scope $scope
}
```

We verified both role assignments through `az role assignment list`.

### 11.3 Establish GitHub OIDC federation

Federation allows a trusted GitHub Actions job to exchange its OIDC token for short-lived Azure credentials. It eliminates the need to store a long-lived client secret.

Initial command:

```powershell
az identity federated-credential create `
  --name github-feature-deploy `
  --identity-name github-pfs-deploy `
  --resource-group rg-medicare-pfs `
  --issuer "https://token.actions.githubusercontent.com" `
  --subject "repo:Mkane8971/IIT-Programming:ref:refs/heads/feature/azure-deployment" `
  --audiences "api://AzureADTokenExchange"
```

**Problem encountered:** The GitHub token actually presented a subject containing immutable numeric owner/repository identifiers:

```text
repo:Mkane8971@143722404/IIT-Programming@1456707596:ref:refs/heads/feature/azure-deployment
```

Entra rejected the initial token with `AADSTS700213: No matching federated identity record found`. We updated the existing federated credential subject to match the **actual token claim**:

```powershell
az identity federated-credential update `
  --name github-feature-deploy `
  --identity-name github-pfs-deploy `
  --resource-group rg-medicare-pfs `
  --subject "repo:Mkane8971@143722404/IIT-Programming@1456707596:ref:refs/heads/feature/azure-deployment"
```

After updating the subject, rerunning the failed GitHub Actions job succeeded.

### 11.4 Add GitHub Actions repository secrets

In GitHub repository **Settings → Secrets and variables → Actions**, we saved:

```text
AZURE_CLIENT_ID
AZURE_TENANT_ID
AZURE_SUBSCRIPTION_ID
```

Values were the managed identity client ID, tenant ID, and subscription ID shown above. No Azure client secret was created.

### 11.5 Final workflow: test → publish → deploy

`.github/workflows/ci.yml` retained `test-and-build` and `publish`, then added a `deploy` job. Deployment was restricted to successful **push** events on `feature/azure-deployment`, not pull requests.

Core deployment job:

```yaml
deploy:
  name: Deploy to Azure
  needs: publish
  if: github.event_name == 'push'
  runs-on: ubuntu-latest

  permissions:
    contents: read
    id-token: write

  steps:
    - name: Sign in to Azure using OIDC
      uses: azure/login@v3
      with:
        client-id: ${{ secrets.AZURE_CLIENT_ID }}
        tenant-id: ${{ secrets.AZURE_TENANT_ID }}
        subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

    - name: Deploy FastAPI
      run: |
        az containerapp update \
          --name pfs-api \
          --resource-group rg-medicare-pfs \
          --image "ghcr.io/mkane8971/medicare-pfs-api:${{ github.sha }}"

    - name: Deploy React frontend
      run: |
        az containerapp update \
          --name pfs-frontend \
          --resource-group rg-medicare-pfs \
          --image "ghcr.io/mkane8971/medicare-pfs-frontend:${{ github.sha }}"
```

The publish job now adds **commit-SHA image tags** alongside `development`, which ensures Azure deploys the specific build created by that workflow run. The frontend publish action uses `NGINX_CONFIG=nginx.azure.conf`.

### 11.6 Confirm final CI/CD success

The final GitHub Actions run on November 14, 2026 showed:

| Job | Result | Approximate duration |
|---|---|---|
| `test-and-build` | Success | 1m 21s |
| `publish` | Success | 1m 34s |
| `Deploy to Azure` | Success | 1m 47s |

This established **working automated deployment**: pushing the deployment branch triggers tests, GHCR publication, OIDC login, and updates to both existing Azure Container Apps.

---

## 12. Final Azure resource inventory

| Resource | Name / value | Purpose |
|---|---|---|
| Resource group | `rg-medicare-pfs` | Contains project Azure resources |
| Region | `westus2` | Azure hosting location |
| Container Apps environment | `cae-medicare-pfs` | Shared app environment |
| Container App | `pfs-api` | Internal FastAPI, port 8000, 0.5 vCPU / 1.0 GiB |
| Container App | `pfs-frontend` | Public React/Nginx, port 8080, 0.25 vCPU / 0.5 GiB |
| Managed identity | `github-pfs-deploy` | GitHub Actions OIDC deployment identity |
| Federated credential | `github-feature-deploy` | Trust deployment branch's GitHub token |
| RBAC | Container Apps Contributor scoped to both apps | Authorize updates |
| Secrets | `mongo-uri` on `pfs-api` | Atlas connection string |
| External database | Atlas M0 `medicare-pfs-db`; database `medicare` | Optional CMS cache |
| External image registry | GHCR | Publishes backend/frontend containers |
| External data source | CMS PFS Data API | Procedure and locality data |

**Public website:** https://pfs-frontend.wonderfulpebble-55b2f0ff.westus2.azurecontainerapps.io

**Billing strategy:** Use Container Apps Consumption and Atlas M0; avoid Log Analytics workspace, Azure NAT Gateway, dedicated database tiers, and private endpoints for this class demonstration. Actual Azure charges depend on consumption and free allowances. The Atlas IP restriction remains an acknowledged reliability limitation; the API's CMS fallback handles cache outages.

---

## 13. Operating and troubleshooting the finished system

### 13.1 Local development

```powershell
# Build and start all local services
docker compose up -d --build

# Backend unit tests
docker compose run --rm api python -m pytest tests/ -v -p no:cacheprovider

# Monitor logs
docker compose logs api --tail 50

# Stop/restart MongoDB for fallback testing
docker compose stop mongo
docker compose start mongo
```

### 13.2 Azure health and logs

```powershell
# Both Container Apps in one command
foreach ($app in @("pfs-api", "pfs-frontend")) {
    az containerapp revision list `
      --name $app `
      --resource-group rg-medicare-pfs `
      --query "[].{Name:name,Active:properties.active,Health:properties.healthState,Replicas:properties.replicas}" `
      --output table
}

# Backend logs
az containerapp logs show --name pfs-api --resource-group rg-medicare-pfs --type console --tail 50

# Frontend logs
az containerapp logs show --name pfs-frontend --resource-group rg-medicare-pfs --type console --tail 50
```

### 13.3 Verify live endpoints

```text
https://pfs-frontend.wonderfulpebble-55b2f0ff.westus2.azurecontainerapps.io/
https://pfs-frontend.wonderfulpebble-55b2f0ff.westus2.azurecontainerapps.io/api/v1/localities?year=2026
https://pfs-frontend.wonderfulpebble-55b2f0ff.westus2.azurecontainerapps.io/api/v1/procedures/99213?year=2026
https://pfs-frontend.wonderfulpebble-55b2f0ff.westus2.azurecontainerapps.io/api/v1/pricing/estimate?hcpcs=27447&year=2026&locality=0310200&setting=facility
```

### 13.4 Common failures we encountered

| Symptom | Cause found | Resolution |
|---|---|---|
| Docker Compose `.env` parse failure | PowerShell command pasted into `.env` | Remove command; validate `docker compose config --quiet` |
| API unhealthy, `\x16:27017` | Incorrectly stored Atlas URI | Replace secret and recycle application |
| API SSL/TLS handshake error | Atlas IP Access List blocked Azure egress | Correct allowlist; add optional-cache fallback |
| `az containerapp revision restart` rejected | Express environment restriction | Portal Stop/Start for restart; use update for deployment |
| Frontend `host not found in upstream` | Nginx resolved `pfs-api` before valid DNS availability | Use backend FQDN and request-time resolution |
| Browser CORS failure loading localities | HTTP reverse proxy redirected to HTTPS backend origin | Proxy to backend over HTTPS and set TLS SNI |
| `{"error":"App port is not ready"}` | Unready frontend or backend app port | Inspect both revision health states and logs |
| `AADSTS700213` in GitHub Actions | GitHub token's subject differed from Azure federation record | Update subject to exact immutable-ID claim |

### 13.5 Daily Git workflow

```powershell
git status
git add <changed-files>
git commit -m "Describe the change"
git push origin feature/azure-deployment
```

Expected pipeline:

```text
Push -> tests -> Docker image builds -> GHCR commit tags -> OIDC login
     -> update pfs-api -> update pfs-frontend -> test live URL
```

**Release-branch note:** Deployment is currently restricted to `feature/azure-deployment`. Moving deployment to `main` would require updating the GitHub Actions push trigger and the federated OIDC credential's subject.

---

## 14. Lessons learned and possible improvements

1. **Keep dependencies optional when possible.** CMS remains the source of truth; MongoDB improves response performance but should not prevent the API from starting.
2. **Treat container DNS and ingress as separate concerns.** Service discovery, HTTP versus HTTPS routing, and Nginx startup-time resolution can produce different failures.
3. **Prefer immutable deployment references.** Commit-SHA tags and image digests make deployed versions traceable.
4. **Separate CI from CD.** Successful builds and publishing do not by themselves prove automated cloud deployment; the additional Azure deploy job completed that requirement.
5. **Use narrow permissions and short-lived credentials.** The user-assigned identity has app-scoped RBAC and GitHub OIDC trust, avoiding an Azure client secret.
6. **Understand consumption-networking tradeoffs.** Avoiding paid static egress reduces costs but makes Atlas allowlist maintenance less predictable.
7. **Distinguish liveness from dependency health.** A running API can continue using CMS when cache connectivity is unavailable; a separate dependency-status endpoint would be a useful future enhancement.
8. **Improve release robustness later.** Consider automatic smoke tests, stricter upstream TLS certificate verification in Nginx, and tests for circuit-breaker state and caching failures.
9. **Be careful with sensitive configuration.** `.env`, Atlas URI, passwords, and credentials must never be included in Git commits or log output.

## 15. Final outcome

By the end of the build, the project had a **working public Medicare PFS Explorer** with React/TypeScript, an internal FastAPI API, optional MongoDB Atlas caching, live CMS procedure and locality retrieval, Medicare payment estimation, Dockerized local development, and GitHub Actions **CI/CD all the way to Azure Container Apps**.

The final GitHub Actions run confirmed all three stages: **test-and-build**, **publish**, and **Deploy to Azure**.

The remaining known infrastructure tradeoff is the lack of a guaranteed static outbound IP from the current Container Apps environment. Instead of adding paid networking, we kept Atlas network restrictions and implemented CMS fallback, so the public application's main functions remain available if caching cannot connect.
