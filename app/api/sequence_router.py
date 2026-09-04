from fastapi import APIRouter, HTTPException, status
from app.api.graph_router import global_graph
from app.services.sequence_engine import SequenceEngine
from app.graph.exceptions import ConceptNotFoundError, CycleDetectedError
from app.models.sequence_schemas import (
    TopologicalSequenceResponse,
    PrerequisiteChainResponse,
    CycleCheckResponse
)

router = APIRouter(prefix="/sequence", tags=["Learning-Sequence Engine"])


@router.get("/topological", response_model=TopologicalSequenceResponse)
def get_topological_learning_sequence():
    """Returns a valid prerequisite-first learning sequence for all concepts in the graph."""
    try:
        sequence = SequenceEngine.get_topological_sequence(global_graph)
        return TopologicalSequenceResponse(
            count=len(sequence),
            has_cycle=False,
            sequence=sequence
        )
    except CycleDetectedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "CycleDetected",
                "message": str(e),
                "cycle_path": e.cycle_path
            }
        )


@router.get("/prerequisite-chain/{concept_id}", response_model=PrerequisiteChainResponse)
def get_prerequisite_chain(concept_id: str):
    """Returns the complete topological prerequisite chain required to master a specific target concept."""
    try:
        chain = SequenceEngine.get_prerequisite_chain(global_graph, concept_id)
        return PrerequisiteChainResponse(
            target_concept_id=concept_id,
            chain_length=len(chain),
            chain=chain
        )
    except ConceptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CycleDetectedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "CycleDetected",
                "message": str(e),
                "cycle_path": e.cycle_path
            }
        )


@router.get("/cycle-check", response_model=CycleCheckResponse)
def check_graph_cycles():
    """Checks whether the knowledge graph contains any circular prerequisite dependencies."""
    cycle = SequenceEngine.find_cycle(global_graph)
    if cycle:
        return CycleCheckResponse(has_cycle=True, cycle_path=cycle)
    return CycleCheckResponse(has_cycle=False, cycle_path=None)
