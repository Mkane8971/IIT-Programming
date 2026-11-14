# Medicare PFS Explorer: Deployment Documentation

**Project:** Medicare Physician Fee Schedule Explorer  
**Source code:** [GitHub – IIT-Programming](https://github.com/Mkane8971/IIT-Programming)  
**Live application:** [Medicare PFS Explorer](https://pfs-frontend.wonderfulpebble-55b2f0ff.westus2.azurecontainerapps.io)  
**Hosting:** Microsoft Azure, West US 2

## Overview

I developed and deployed a web application that retrieves Medicare Physician Fee Schedule (PFS) information from CMS. Users can search by CPT/HCPCS code and year, select a facility setting and Medicare locality, and review RVUs, conversion factors, and estimated reimbursement. I built it as a containerized application so I could develop and test locally before deploying the same components to Azure.

My architecture uses a React and TypeScript frontend, a Python FastAPI backend, and MongoDB for caching. The CMS PFS Data API supplies procedure and locality data. I use Nginx to serve the compiled React application and forward requests to FastAPI.

```text
Browser → Azure Container Apps (public React + Nginx)
        → Azure Container Apps (internal FastAPI)
        → CMS PFS Data API
        ↘ MongoDB Atlas (optional cache)
```

## Local development and containerization

I organized the backend into routers, API clients, services, and a repository layer. FastAPI handles procedure searches and reimbursement calculations, while the CMS client retrieves the source records. I used `Decimal` arithmetic for the payment formula to avoid floating-point rounding errors.

I initialized the frontend with Vite, React, and TypeScript. I used a multi-stage Dockerfile: Node.js builds the frontend, and an unprivileged Nginx image serves the compiled files on port `8080`. The backend runs with Uvicorn on port `8000`.

Docker Compose manages three services locally: `api`, `frontend`, and `mongo`. I start or rebuild the application with:

```powershell
docker compose up -d --build
```

I run the backend unit tests before publishing changes:

```powershell
docker compose run --rm api python -m pytest tests/ -v -p no:cacheprovider
```

I maintain separate Nginx configurations for local development and Azure. Locally, Nginx forwards `/api/` requests to `api:8000` within the Docker Compose network. The Azure version forwards requests over HTTPS to the internal FastAPI Container App. This allows the React application to use relative API URLs in both environments.

## Azure resources

I deployed the application using the following resources:

| Resource | Name or configuration | Purpose |
|---|---|---|
| Resource group | `rg-medicare-pfs` | Groups the Azure resources |
| Container Apps environment | `cae-medicare-pfs` | Hosts both application containers |
| Frontend Container App | `pfs-frontend` | Public HTTPS site, Nginx on port `8080` |
| Backend Container App | `pfs-api` | Internal FastAPI service on port `8000` |
| Managed identity | `github-pfs-deploy` | Authorizes GitHub Actions deployments |
| MongoDB Atlas | Free M0 cluster, `medicare-pfs-db` | Stores cached CMS responses |
| GitHub Container Registry | GHCR | Stores the backend and frontend container images |

I selected Azure Container Apps Consumption and MongoDB Atlas M0 to keep operating costs low. I did not provision a NAT Gateway or a Log Analytics workspace for this project.

## Database and API configuration

I initially used MongoDB in Docker Compose, then created a MongoDB Atlas cluster for the cloud deployment. I stored the Atlas connection URI as an Azure Container App secret and kept credentials out of my source code.

I implemented a cache that retains up to 25 procedure results and reuses records for up to 24 hours. During deployment, I found that Azure's outbound IP address could change, preventing Atlas connections under a restricted IP allowlist. I kept Atlas network access restricted and updated FastAPI so MongoDB is optional. If the cache is unavailable, the API logs the issue, skips database calls temporarily, and retrieves the data directly from CMS. I tested this behavior locally by stopping MongoDB and confirming that procedure and pricing requests still succeeded.

## Deployment and CI/CD

I first deployed the container images manually to confirm the Azure configuration. The React application has external ingress; FastAPI has internal ingress. Nginx proxies browser API requests to the backend over HTTPS.

I then configured `.github/workflows/ci.yml` to automate the process:

1. **Test and build:** Build Docker images, run Python tests, and validate Nginx.
2. **Publish:** Push the API and frontend images to GHCR with Git commit SHA tags.
3. **Deploy:** Authenticate to Azure using GitHub OIDC and update the existing Container Apps with those images.

I used an Azure user-assigned managed identity rather than storing a client secret in GitHub. Its `Container Apps Contributor` permissions are scoped to the two application resources. GitHub Actions stores the Azure client, tenant, and subscription IDs as repository secrets. Once I configured the federated credential to match GitHub's OIDC subject, all three jobs completed successfully.

I use feature branches and pull requests to review changes before merging them into `main`. The exact branch that triggers production deployment is controlled by the workflow's `push.branches` setting and its matching Azure OIDC federated credential.

## Verification and lessons learned

I verify the deployed application by opening the public URL and testing procedure searches, locality selection, and reimbursement estimates. I also use Azure CLI to inspect revision health and logs:

```powershell
az containerapp revision list --name pfs-api --resource-group rg-medicare-pfs --output table
az containerapp logs show --name pfs-api --resource-group rg-medicare-pfs --type console --tail 50
```

The main issues I resolved were an incorrectly stored Atlas connection string, Atlas IP restrictions, Nginx hostname resolution, and an HTTP-to-HTTPS redirect that interrupted API requests. I also corrected historical CMS release identifiers, such as `210B`, so they can be displayed without being parsed as calendar years.

The final result is a publicly accessible application with separate frontend and backend containers, a cloud database used for optional caching, and an automated testing and deployment workflow. The project showed me how application code, container networking, cloud identity, and operational troubleshooting fit together in a production-style deployment.
