from fastapi import APIRouter, HTTPException, status
from app.api.graph_router import global_graph
from app.services.recommendation_engine import RecommendationEngine
from app.graph.exceptions import ConceptNotFoundError
from app.models.recommendation_schemas import (
    RecommendationRequest,
    RecommendationResult,
    RecommendedTopic
)

router = APIRouter(prefix="/recommendations", tags=["Personalized Recommendation Engine"])


@router.post("/generate", response_model=RecommendationResult, status_code=status.HTTP_200_OK)
def generate_recommended_learning_path(request: RecommendationRequest):
    """
    Generates a personalized, dynamic learning path recommendation based on student mastery,
    bottleneck unlock impact, target goal proximity, and prerequisite readiness.
    """
    try:
        return RecommendationEngine.generate_recommendations(
            graph=global_graph,
            known_concept_ids=request.known_concept_ids,
            target_concept_id=request.target_concept_id,
            max_recommendations=request.max_recommendations
        )
    except ConceptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/next-topic", response_model=RecommendedTopic, status_code=status.HTTP_200_OK)
def get_single_next_best_topic(request: RecommendationRequest):
    """
    Returns the single best next topic for a student to study right now.
    """
    try:
        res = RecommendationEngine.generate_recommendations(
            graph=global_graph,
            known_concept_ids=request.known_concept_ids,
            target_concept_id=request.target_concept_id,
            max_recommendations=1
        )
        if not res.recommended_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No suitable ready topics found. You may have completed the entire curriculum or need to fulfill prerequisites first."
            )
        return res.recommended_path[0]
    except ConceptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
