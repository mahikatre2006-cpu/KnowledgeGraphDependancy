from fastapi import APIRouter, HTTPException, Query, status
from app.api.graph_router import global_graph
from app.services.analytics_engine import AnalyticsEngine
from app.graph.exceptions import ConceptNotFoundError
from app.models.analytics_schemas import (
    MissingPrerequisitesRequest,
    MissingPrerequisitesResponse,
    BottlenecksResponse,
    ReadinessRequest,
    ReadinessResponse
)

router = APIRouter(prefix="/analytics", tags=["Graph Analytics & Diagnostics Engine"])


@router.post("/missing-prerequisites", response_model=MissingPrerequisitesResponse, status_code=status.HTTP_200_OK)
def get_missing_prerequisites(request: MissingPrerequisitesRequest):
    """
    Calculates missing prerequisite concepts for a student targeting a specific concept,
    given their currently mastered concepts.
    """
    try:
        return AnalyticsEngine.get_missing_prerequisites(
            graph=global_graph,
            target_concept_id=request.target_concept_id,
            known_concept_ids=request.known_concept_ids
        )
    except ConceptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/bottlenecks", response_model=BottlenecksResponse, status_code=status.HTTP_200_OK)
def analyze_learning_bottlenecks(top_n: int = Query(default=10, ge=1, le=50, description="Top N bottleneck concepts to return")):
    """
    Ranks concept nodes in the knowledge graph by their downstream reachability centrality.
    Identifies learning bottleneck concepts that unlock the largest portion of the curriculum.
    """
    return AnalyticsEngine.analyze_bottlenecks(graph=global_graph, top_n=top_n)


@router.post("/readiness", response_model=ReadinessResponse, status_code=status.HTTP_200_OK)
def check_student_readiness(request: ReadinessRequest):
    """
    Evaluates whether a student has satisfied all immediate prerequisites to start learning a target concept.
    """
    try:
        return AnalyticsEngine.check_readiness(
            graph=global_graph,
            concept_id=request.concept_id,
            known_concept_ids=request.known_concept_ids
        )
    except ConceptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
