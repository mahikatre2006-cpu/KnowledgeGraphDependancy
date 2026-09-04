import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.graph_router import global_graph
from app.db.session import get_db
from app.services.persistence_service import PersistenceService
from app.db.neo4j_driver import Neo4jService
from app.models.persistence_schemas import SaveProgressRequest, PersistenceStatusResponse

router = APIRouter(prefix="/persistence", tags=["Database Persistence Engine (Supabase & Neo4j)"])


@router.post("/sync-to-neo4j", status_code=status.HTTP_200_OK)
def sync_graph_to_neo4j():
    """
    Synchronizes active in-memory KnowledgeGraph concept nodes and prerequisite relationships to Neo4j.
    """
    res = PersistenceService.sync_to_neo4j(global_graph)
    if not res.get("success"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=res.get("message")
        )
    return res


@router.post("/user-progress", status_code=status.HTTP_200_OK)
def save_user_progress(request: SaveProgressRequest, db: Session = Depends(get_db)):
    """
    Saves a student's mastered concepts to PostgreSQL (Supabase).
    """
    saved_count = PersistenceService.save_user_progress_to_postgres(
        db=db,
        user_id=request.user_id,
        known_concept_ids=request.known_concept_ids
    )
    return {
        "message": f"Successfully saved {saved_count} mastered concepts for user '{request.user_id}' to PostgreSQL.",
        "user_id": request.user_id,
        "saved_count": saved_count
    }


@router.get("/status", response_model=PersistenceStatusResponse, status_code=status.HTTP_200_OK)
def check_persistence_status():
    """
    Checks connection readiness of Supabase PostgreSQL and Neo4j.
    """
    db_url = os.getenv("DATABASE_URL", "")
    pg_status = "Supabase PostgreSQL Configured" if ("supabase" in db_url or "postgresql" in db_url) else "Local SQLite Fallback Active"
    
    neo4j_driver = Neo4jService.get_driver()
    neo4j_status = "Neo4j Graph Database Connected" if neo4j_driver else "Neo4j Unconfigured (NEO4J_URI & NEO4J_PASSWORD required)"

    return PersistenceStatusResponse(
        success=True,
        message="Persistence Layer Status",
        postgres_status=pg_status,
        neo4j_status=neo4j_status
    )
