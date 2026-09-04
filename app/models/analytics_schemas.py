from typing import List, Dict, Any
from pydantic import BaseModel, Field
from app.graph.models import ConceptNode


class MissingPrerequisitesRequest(BaseModel):
    target_concept_id: str = Field(..., json_schema_extra={"example": "deep_learning"}, description="Target concept student wants to learn")
    known_concept_ids: List[str] = Field(default_factory=list, json_schema_extra={"example": ["python", "calculus_1"]}, description="List of concept IDs student has already mastered")


class MissingPrerequisitesResponse(BaseModel):
    target_concept_id: str = Field(..., description="Target concept ID")
    target_concept_name: str = Field(..., description="Target concept name")
    progress_percentage: float = Field(..., description="Percentage of required prerequisites already mastered (0.0 to 100.0%)")
    total_prerequisites_count: int = Field(..., description="Total number of prerequisite concepts required")
    missing_count: int = Field(..., description="Number of missing prerequisite concepts")
    missing_concepts: List[ConceptNode] = Field(..., description="Topologically ordered list of missing prerequisite concepts to study")
    known_ancestors: List[ConceptNode] = Field(..., description="List of prerequisite concepts already mastered by student")


class BottleneckItem(BaseModel):
    concept: ConceptNode = Field(..., description="Concept node object")
    downstream_count: int = Field(..., description="Total downstream concepts unlocked by mastering this topic")
    direct_dependents_count: int = Field(..., description="Immediate downstream concepts directly depending on this topic")
    unlocked_concept_ids: List[str] = Field(..., description="List of all downstream concept IDs unlocked")
    impact_score: float = Field(..., description="Normalized bottleneck impact score (0.0 to 1.0)")
    description: str = Field(..., description="Human-readable analysis explanation")


class BottlenecksResponse(BaseModel):
    total_concepts: int = Field(..., description="Total concepts in graph")
    bottlenecks: List[BottleneckItem] = Field(..., description="Ranked list of learning bottleneck concepts")


class ReadinessRequest(BaseModel):
    concept_id: str = Field(..., description="Concept ID to evaluate readiness for")
    known_concept_ids: List[str] = Field(default_factory=list, description="List of concept IDs mastered by student")


class ReadinessResponse(BaseModel):
    concept_id: str = Field(..., description="Evaluated concept ID")
    concept_name: str = Field(..., description="Evaluated concept name")
    is_ready: bool = Field(..., description="True if all prerequisites are satisfied and concept is ready to learn")
    unmet_prerequisites: List[ConceptNode] = Field(..., description="List of immediate unsatisfied prerequisite concept nodes")
