from fastapi import FastAPI
from app.database import lifespan
from app.routers.procedures import router as procedures_router
from app.routers.localities import router as localities_router

app = FastAPI(
    title="Medicare PFS Explorer",
    description="A tool to explore Medicare Physician Fee Schedule data.",
    version="1.0.0",
    lifespan=lifespan
    )

# register endpoints
app.include_router(procedures_router)
app.include_router(localities_router)


@app.get("/health")
def health():
    return {"status": "healthy"}


# @app.get("/api/v1/status")
# def status():
#     return {
#         "application": "Medicare PFS Explorer",
#         "status": "operational",
#         "services": ["react", "fastapi", "mongodb"]
#     }
