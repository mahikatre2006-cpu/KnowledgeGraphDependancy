from typing import List
from fastapi import APIRouter, HTTPException, status
from app.graph.engine import KnowledgeGraph
from app.graph.exceptions import (
    ConceptNotFoundError,
    DuplicateConceptError,
    SelfLoopError,
    InvalidDependencyError
)
from app.graph.models import ConceptNode, DependencyEdge
from app.models.graph_schemas import (
    AddConceptRequest,
    AddDependencyRequest,
    GraphSummaryResponse
)

router = APIRouter(prefix="/graph", tags=["Knowledge Graph Engine"])

# Global in-memory graph instance for V1
global_graph = KnowledgeGraph()


@router.post("/concepts", response_model=ConceptNode, status_code=status.HTTP_201_CREATED)
def add_concept(request: AddConceptRequest):
    try:
        return global_graph.add_concept(
            id=request.id,
            name=request.name,
            unit=request.unit,
            description=request.description,
            metadata=request.metadata
        )
    except DuplicateConceptError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/concepts", response_model=List[ConceptNode])
def get_all_concepts():
    return global_graph.get_all_nodes()


@router.get("/concepts/{concept_id}", response_model=ConceptNode)
def get_concept(concept_id: str):
    node = global_graph.get_concept(concept_id)
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Concept with ID '{concept_id}' not found."
        )
    return node


@router.delete("/concepts/{concept_id}", status_code=status.HTTP_200_OK)
def remove_concept(concept_id: str):
    try:
        global_graph.remove_concept(concept_id)
        return {"message": f"Concept '{concept_id}' and associated edges removed."}
    except ConceptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/dependencies", response_model=DependencyEdge, status_code=status.HTTP_201_CREATED)
def add_dependency(request: AddDependencyRequest):
    try:
        return global_graph.add_dependency(
            source_id=request.source_id,
            target_id=request.target_id,
            relationship_type=request.relationship_type,
            confidence=request.confidence,
            reason=request.reason
        )
    except SelfLoopError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ConceptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/dependencies", status_code=status.HTTP_200_OK)
def remove_dependency(source_id: str, target_id: str):
    try:
        global_graph.remove_dependency(source_id, target_id)
        return {"message": f"Dependency '{source_id} -> {target_id}' removed."}
    except InvalidDependencyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/concepts/{concept_id}/prerequisites", response_model=List[ConceptNode])
def get_prerequisites(concept_id: str):
    try:
        return global_graph.get_prerequisites(concept_id)
    except ConceptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/concepts/{concept_id}/dependents", response_model=List[ConceptNode])
def get_dependents(concept_id: str):
    try:
        return global_graph.get_dependents(concept_id)
    except ConceptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/summary", response_model=GraphSummaryResponse)
def get_graph_summary():
    return GraphSummaryResponse(
        node_count=global_graph.node_count(),
        edge_count=global_graph.edge_count(),
        nodes=global_graph.get_all_nodes(),
        edges=global_graph.get_all_edges()
    )
