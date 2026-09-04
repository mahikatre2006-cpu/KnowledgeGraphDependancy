from fastapi import FastAPI
from app.core.config import settings
from app.api.graph_router import router as graph_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Knowledge Dependency Graph API — Transform syllabi into interactive prerequisite graphs."
)

app.include_router(graph_router, prefix=settings.API_V1_STR)


@app.get("/")
def read_root():
    return {
        "message": "Welcome to Knowledge Dependency Graph API",
        "version": settings.VERSION,
        "docs_url": "/docs"
    }


@app.get("/healthz", status_code=200)
def health_check():
    return {
        "status": "ok",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

