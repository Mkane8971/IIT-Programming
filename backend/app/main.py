from fastapi import FastAPI
from app.database import lifespan

app = FastAPI(
    title="Medicare PFS Explorer",
    description="A tool to explore Medicare Physician Fee Schedule data.",
    version="1.0.0",
    lifespan=lifespan
    )


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/v1/status")
def status():
    return {
        "application": "Medicare PFS Explorer",
        "status": "operational",
        "services": ["react", "fastapi", "mongodb"]
    }
