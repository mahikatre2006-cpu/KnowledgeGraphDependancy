from typing import List, Optional
from pydantic import BaseModel, Field
from app.graph.models import ConceptNode


class TopologicalSequenceResponse(BaseModel):
    count: int = Field(..., description="Number of concepts in the sequence")
    has_cycle: bool = Field(default=False, description="Whether a cycle was detected")
    sequence: List[ConceptNode] = Field(..., description="Ordered list of concepts from foundational to advanced")


class PrerequisiteChainResponse(BaseModel):
    target_concept_id: str = Field(..., description="Target concept ID requested")
    chain_length: int = Field(..., description="Total concepts required in chain including target")
    chain: List[ConceptNode] = Field(..., description="Ordered prerequisite chain leading to target concept")


class CycleCheckResponse(BaseModel):
    has_cycle: bool = Field(..., description="True if graph contains circular dependencies")
    cycle_path: Optional[List[str]] = Field(default=None, description="Path of concept IDs forming the cycle if detected")
