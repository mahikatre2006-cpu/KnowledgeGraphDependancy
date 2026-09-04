from typing import List
from pydantic import BaseModel, Field
from app.graph.models import DependencyEdge


class InferenceRequest(BaseModel):
    similarity_threshold: float = Field(
        default=0.30,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity threshold to consider topic pairs related"
    )
    min_confidence: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Minimum overall confidence score required to propose a prerequisite edge"
    )
    auto_add_to_graph: bool = Field(
        default=True,
        description="If True, automatically adds inferred prerequisite edges directly into the Knowledge Graph"
    )


class InferenceResponse(BaseModel):
    message: str = Field(..., description="Summary message of inference operation")
    inferred_edges_count: int = Field(..., description="Number of edges inferred")
    inferred_edges: List[DependencyEdge] = Field(..., description="List of inferred dependency edges")
