# Medicare PFS Explorer: Prototyping and Mockup Documentation

## Project Background and Original Concept

The idea for the Medicare Physician Fee Schedule (PFS) Explorer came from a use case I encountered in my professional work with healthcare reimbursement and payer contracting. In that environment, I worked with large sets of procedure codes, fee schedules, and reimbursement data to support pricing analysis. A common task involved taking source files from CMS, transforming them into a consistent structure, and joining them with other tables so that a procedure could be evaluated in the context of its year, geographic locality, place of service, and payment rules.

That work was performed through a different data architecture. Source files were loaded, transformed, and merged within a warehouse-oriented workflow. Once the relationships and calculations were established, the resulting data could be queried or presented through analytical tools. The process was useful, although it required substantial preparation before a user could look up a single procedure and understand its reimbursement components. It provided the starting point for this project: build a small public web application that exposes the underlying calculation in a more approachable format.

For my Programming and Application Foundations project, I wanted to revisit the same business problem from a software engineering perspective. Instead of relying on an existing analytical workflow, I would design the application interfaces, implement an API, create a database integration, containerize the services, and deploy a working system. The intended user could enter a CPT or HCPCS code and immediately inspect the Medicare PFS information used in a payment estimate.

## Initial Prototype and Interface Mockup

The original prototype centered on one user interaction: search for a procedure and review its fee schedule values. I kept the interface deliberately narrow so that the application could demonstrate an end-to-end request without introducing unrelated features. The initial requirements were a five-character CPT/HCPCS input, calendar year, optional modifier, facility or non-facility setting, and a results area for the procedure description and relative value units (RVUs).

As the pricing calculation developed, Medicare payment locality became another required input. Locality determines which Geographic Practice Cost Indices (GPCIs) apply to the work, practice expense, and malpractice RVUs. The result set also needed to distinguish multiple CMS payment records, including different conversion-factor categories, rather than assume that every procedure returned one rate.

The following is a **retrospective, simplified wireframe** showing the interface concept. It documents the layout and interaction that guided implementation; it is not presented as an original dated design artifact.

```text
+----------------------------------------------------------+
|                  Medicare PFS Explorer                   |
|                                                          |
|  Procedure Search                                        |
|  CPT/HCPCS Code       [ 27447                         ]  |
|  Calendar Year        [ 2026                          ]  |
|  Modifier (optional)  [                               ]  |
|  Setting              [ Facility                  v  ]  |
|  Medicare Locality    [ Arizona                   v  ]  |
|                         [ Search ]                       |
|                                                          |
|  Procedure Results                                       |
|  Description | Work RVU | PE RVU | MP RVU | CF | Source  |
|                                                          |
|  Payment Estimate                                        |
|  Locality | GPCI adjustments | Estimated Medicare amount |
+----------------------------------------------------------+
```

The completed React interface follows this general arrangement. A short “How to Use This Explorer” section was later added to help someone unfamiliar with Medicare fee schedules enter a meaningful example and interpret the results. This was especially useful for a classroom demonstration because the application exposes several healthcare reimbursement terms that may be unfamiliar to a general software user.

## Evolution of the Data and Application Design

My first concept was influenced by the warehouse-based method I had used at work: obtain CMS fee schedule files, normalize the data, build relationships across years and localities, and then query a prepared dataset. During development, I identified the CMS PFS Data API as a way to retrieve the relevant records directly. That changed the implementation approach. The application could request procedure and locality records on demand, which reduced the need to maintain a complete historical copy of CMS files for this course project.

The backend was built with FastAPI, with separate routes for procedure searches, locality retrieval, and payment estimates. A CMS client handles the external requests, and a pricing service applies the PFS calculation using `Decimal` arithmetic. The calculation combines geographically adjusted work, practice expense, and malpractice RVUs and multiplies the total by the applicable conversion factor. Keeping these responsibilities in separate modules made it easier to test the calculation independently of the web interface and external API.

The frontend was initialized with React and TypeScript using Vite. I used Nginx to serve the compiled React application and reverse-proxy `/api/` requests to FastAPI. The services run in separate Docker containers, which allowed the same application structure to be developed locally and deployed to Azure Container Apps. The public frontend communicates with the internal backend through Nginx, while the backend handles CMS retrieval and pricing logic.

The database architecture evolved as well. MongoDB was retained to satisfy the project's database requirement and to cache recently retrieved procedure records. For cloud deployment, the application was updated to connect to **MongoDB Atlas** instead of depending on a MongoDB container running inside Azure. The cache retains up to 25 procedure entries using a least-recently-used approach, with records considered fresh for 24 hours. This provides a useful database integration without requiring the application to maintain the entire CMS PFS dataset.

That decision exposed a practical availability issue. Azure Container Apps can change its outbound IP address, and Atlas network access is restricted to allowlisted addresses. I therefore updated the FastAPI design so that MongoDB is an optional cache dependency. If Atlas becomes unreachable, the application reports the cache as unavailable, temporarily skips additional cache operations, and continues retrieving procedure data from CMS. A circuit breaker retries the database after a cooldown period. I tested this behavior locally by stopping MongoDB and confirming that procedure searches and pricing estimates continued to work.

## Iteration, Testing, and Final Implementation

Development included several rounds of testing that influenced the prototype. Historical CMS records, for example, sometimes contain release identifiers such as `210B` and `224B` in a field named `year`. An early pricing implementation treated that field as a calendar-year integer and failed. The calculation was revised to accept the requested numeric calendar year separately while preserving the CMS release identifier in the results. This improved traceability and supported older fee schedule records without losing source information. Historical reimbursement values still require attention to effective dates and corresponding releases.

I also used deployment issues as part of the engineering iteration. The Nginx configuration had to be adapted from local Docker Compose service names to Azure-hosted service routing, and the upstream request was changed to HTTPS to avoid redirects interfering with API requests. GitHub Actions now tests the backend, builds both Docker images, publishes them to GitHub Container Registry, and deploys the application to Azure using OpenID Connect authentication. The final deployment uses a public React/Nginx Container App, an internal FastAPI Container App, the CMS Data API, and MongoDB Atlas as an optional cache.

The prototype began as a simple procedure lookup based on an established healthcare contracting workflow. It evolved into a small, working distributed web application with a defined frontend, backend, external data source, cache, tests, and automated deployment. The largest design lesson was how source-data assumptions and infrastructure constraints affect application behavior. A useful interface depends on accurate fee schedule interpretation, and a reliable backend needs to continue serving valid requests when a secondary dependency becomes unavailable.

**Implementation references:** 
[Working application](https://pfs-frontend.wonderfulpebble-55b2f0ff.westus2.azurecontainerapps.io) · 
[Source repository](https://github.com/Mkane8971/IIT-Programming) · 
[Deployment documentation](./docs.md)
