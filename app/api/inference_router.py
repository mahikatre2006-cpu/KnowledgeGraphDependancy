from fastapi import APIRouter, status
from app.api.graph_router import global_graph
from app.services.relationship_inferencer import RelationshipInferencer
from app.models.inference_schemas import InferenceRequest, InferenceResponse

router = APIRouter(prefix="/graph", tags=["AI & NLP Relationship Inference"])


@router.post("/infer-relationships", response_model=InferenceResponse, status_code=status.HTTP_200_OK)
def infer_prerequisite_relationships(request: InferenceRequest):
    """
    Uses 100% local open-source HuggingFace sentence-transformers (all-MiniLM-L6-v2) embeddings
    and multi-factor ML heuristics to infer missing prerequisite relationships between concepts.
    """
    inferred_edges = RelationshipInferencer.infer_prerequisites(
        graph=global_graph,
        similarity_threshold=request.similarity_threshold,
        min_confidence=request.min_confidence,
        auto_add_to_graph=request.auto_add_to_graph
    )

    return InferenceResponse(
        message=f"Successfully inferred {len(inferred_edges)} prerequisite relationships using local open-source models.",
        inferred_edges_count=len(inferred_edges),
        inferred_edges=inferred_edges
    )
