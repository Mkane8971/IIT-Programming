from fastapi import FastAPI


app = FastAPI(title="Medicare PFS Explorer", description="A tool to explore Medicare Physician Fee Schedule data.", version="1.0.0")


@app.get("/health")
def health():
    return {"status": "healthy"}


