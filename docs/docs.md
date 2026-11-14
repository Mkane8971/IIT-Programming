# Medicare PFS Explorer: Deployment Documentation

**Project:** Medicare Physician Fee Schedule Explorer  
**Source code:** [GitHub – IIT-Programming](https://github.com/Mkane8971/IIT-Programming)  
**User stories and requirements:** [GitHub Issues](https://github.com/Mkane8971/IIT-Programming/issues?q=is%3Aissue+state%3Aclosed)  
**Prototyping and mockup documentation:** [docs/prototyping/mockup_documentation.md](https://github.com/Mkane8971/IIT-Programming/blob/main/docs/prototyping/mockup_documentation.md)  
**Live application:** [Medicare PFS Explorer](https://pfs-frontend.wonderfulpebble-55b2f0ff.westus2.azurecontainerapps.io)  
**Hosting:** Microsoft Azure, West US 2

## Overview

The Medicare PFS Explorer is a deployed web application that retrieves Medicare Physician Fee Schedule (PFS) information from CMS. Users can search by CPT/HCPCS code and year, select a facility setting and Medicare locality, and review RVUs, conversion factors, and estimated reimbursement. The application is containerized to support local development, testing, and consistent deployment to Azure.

The architecture uses a React and TypeScript frontend, a Python FastAPI backend, and MongoDB for caching. The CMS PFS Data API supplies procedure and locality data. Nginx is used to serve the compiled React application and forward requests to FastAPI.

```text
Browser → Azure Container Apps (public React + Nginx)
        → Azure Container Apps (internal FastAPI)
        → CMS PFS Data API
        ↘ MongoDB Atlas (optional cache)
```

## Local development and containerization

The backend is organized into routers, API clients, services, and a repository layer. FastAPI handles procedure searches and reimbursement calculations, while the CMS client retrieves the source records. The pricing service uses `Decimal` arithmetic for the payment formula to avoid floating-point rounding errors.

The frontend was initialized with Vite, React, and TypeScript. Its multi-stage Dockerfile uses two stages: Node.js builds the frontend, and an unprivileged Nginx image serves the compiled files on port `8080`. The backend runs with Uvicorn on port `8000`.

Docker Compose manages three services locally: `api`, `frontend`, and `mongo`. The application is started or rebuilt locally with:

```powershell
docker compose up -d --build
```

Backend unit tests run before changes are published:

```powershell
docker compose run --rm api python -m pytest tests/ -v -p no:cacheprovider
```

Separate Nginx configurations are maintained for local development and Azure. Locally, Nginx forwards `/api/` requests to `api:8000` within the Docker Compose network. The Azure version forwards requests over HTTPS to the internal FastAPI Container App. This allows the React application to use relative API URLs in both environments.

## Azure resources

The application uses the following cloud resources:

| Resource | Name or configuration | Purpose |
|---|---|---|
| Resource group | `rg-medicare-pfs` | Groups the Azure resources |
| Container Apps environment | `cae-medicare-pfs` | Hosts both application containers |
| Frontend Container App | `pfs-frontend` | Public HTTPS site, Nginx on port `8080` |
| Backend Container App | `pfs-api` | Internal FastAPI service on port `8000` |
| Managed identity | `github-pfs-deploy` | Authorizes GitHub Actions deployments |
| MongoDB Atlas | Free M0 cluster, `medicare-pfs-db` | Stores cached CMS responses |
| GitHub Container Registry | GHCR | Stores the backend and frontend container images |

Azure Container Apps Consumption and MongoDB Atlas M0 were selected to limit operating costs. The deployment does not include a NAT Gateway or a Log Analytics workspace.

## Database and API configuration

Development began with MongoDB in Docker Compose and later transitioned to MongoDB Atlas for cloud caching. The Atlas connection URI is stored as an Azure Container App secret, keeping credentials out of source control.

The backend implements a cache that retains up to 25 procedure results and reuses records for up to 24 hours. During deployment, changing Azure outbound IP addresses sometimes prevented Atlas connections under a restricted IP allowlist. Atlas access remains restricted, and FastAPI treats MongoDB as an optional dependency. If the cache is unavailable, the API logs the issue, skips database calls temporarily, and retrieves the data directly from CMS. The fallback was tested locally by stopping MongoDB and confirming that procedure and pricing requests still succeeded.

## Deployment and CI/CD

Initial container images were deployed manually to verify the Azure configuration. The React application has external ingress; FastAPI has internal ingress. Nginx proxies browser API requests to the backend over HTTPS.

The `.github/workflows/ci.yml` workflow automates the process:

1. **Test and build:** Build Docker images, run Python tests, and validate Nginx.
2. **Publish:** Push the API and frontend images to GHCR with Git commit SHA tags.
3. **Deploy:** Authenticate to Azure using GitHub OIDC and update the existing Container Apps with those images.

Deployment authentication uses an Azure user-assigned managed identity, avoiding stored client secrets in GitHub. Its `Container Apps Contributor` permissions are scoped to the two application resources. GitHub Actions stores the Azure client, tenant, and subscription IDs as repository secrets. After correcting the federated credential to match GitHub’s OIDC subject, all three jobs completed successfully.

Development follows a feature-branch and pull-request workflow before changes are merged into `main`. The exact branch that triggers production deployment is controlled by the workflow's `push.branches` setting and its matching Azure OIDC federated credential.

## Verification and lessons learned

Deployment verification includes testing the public URL, procedure searches, locality selection, and reimbursement estimates. Azure CLI also provides revision health information and logs:

```powershell
az containerapp revision list --name pfs-api --resource-group rg-medicare-pfs --output table
az containerapp logs show --name pfs-api --resource-group rg-medicare-pfs --type console --tail 50
```

Key deployment issues included an incorrectly stored Atlas connection string, Atlas IP restrictions, Nginx hostname resolution, and an HTTP-to-HTTPS redirect that interrupted API requests. Historical CMS release identifiers, such as `210B`, were also handled separately from calendar years.

The final result is a publicly accessible application with separate frontend and backend containers, a cloud database used for optional caching, and an automated testing and deployment workflow. The implementation demonstrates how application code, container networking, cloud identity, and operational troubleshooting work together in a production-style deployment.
