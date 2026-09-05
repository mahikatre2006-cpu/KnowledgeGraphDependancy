from fastapi import FastAPI
from app.core.config import settings
from app.db.session import engine, Base
from app.db.postgres_models import User, SyllabusDocument, UserProgress, ConceptEmbedding
from app.api.graph_router import router as graph_router
from app.api.sequence_router import router as sequence_router
from app.api.parser_router import router as parser_router
from app.api.builder_router import router as builder_router
from app.api.inference_router import router as inference_router
from app.api.analytics_router import router as analytics_router
from app.api.recommendation_router import router as recommendation_router
from app.api.persistence_router import router as persistence_router
from app.api.metrics_router import router as metrics_router

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Knowledge Dependency Graph API — Transform syllabi into interactive prerequisite graphs."
)

app.include_router(graph_router, prefix=settings.API_V1_STR)
app.include_router(sequence_router, prefix=settings.API_V1_STR)
app.include_router(parser_router, prefix=settings.API_V1_STR)
app.include_router(builder_router, prefix=settings.API_V1_STR)
app.include_router(inference_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(recommendation_router, prefix=settings.API_V1_STR)
app.include_router(persistence_router, prefix=settings.API_V1_STR)
app.include_router(metrics_router, prefix=settings.API_V1_STR)









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

