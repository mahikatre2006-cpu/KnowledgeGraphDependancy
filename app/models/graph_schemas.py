from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.graph.models import ConceptNode, DependencyEdge


class AddConceptRequest(BaseModel):
    id: str = Field(..., json_schema_extra={"example": "linear_algebra"}, description="Unique concept ID")
    name: str = Field(..., json_schema_extra={"example": "Linear Algebra"}, description="Concept name")
    unit: str = Field(default="", json_schema_extra={"example": "Unit 1"}, description="Module/Unit name")
    description: str = Field(default="", description="Detailed description")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AddDependencyRequest(BaseModel):
    source_id: str = Field(..., json_schema_extra={"example": "linear_algebra"}, description="Prerequisite concept ID")
    target_id: str = Field(..., json_schema_extra={"example": "neural_networks"}, description="Dependent concept ID")
    relationship_type: str = Field(default="prerequisite")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reason: str = Field(default="")


class GraphSummaryResponse(BaseModel):
    node_count: int
    edge_count: int
    nodes: List[ConceptNode]
    edges: List[DependencyEdge]
