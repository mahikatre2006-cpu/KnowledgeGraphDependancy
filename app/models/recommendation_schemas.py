from typing import List, Optional
from pydantic import BaseModel, Field
from app.graph.models import ConceptNode


class RecommendationRequest(BaseModel):
    known_concept_ids: List[str] = Field(
        default_factory=list,
        json_schema_extra={"example": ["python", "vectors"]},
        description="List of concept IDs student has already mastered"
    )
    target_concept_id: Optional[str] = Field(
        default=None,
        json_schema_extra={"example": "deep_learning"},
        description="Optional target concept ID student wants to reach"
    )
    max_recommendations: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of topics to recommend in the immediate path"
    )


class RecommendedTopic(BaseModel):
    concept: ConceptNode = Field(..., description="Concept node object")
    score: float = Field(..., description="Recommendation score (0.0 to 1.0)")
    status: str = Field(..., description="Status category: 'NOW' (Ready to study), 'NEXT' (1 prereq remaining), 'LATER' (Blocked)")
    readiness_percentage: float = Field(..., description="Percentage of prerequisites satisfied (0.0 to 100.0%)")
    downstream_unlocked_count: int = Field(..., description="Number of downstream topics this concept unlocks")
    unmet_prerequisites_count: int = Field(..., description="Number of remaining unsatisfied prerequisites")
    recommendation_reason: str = Field(..., description="Clear, human-readable practical reason for recommendation")


class RecommendationResult(BaseModel):
    target_concept_id: Optional[str] = Field(default=None, description="Target concept ID if specified")
    student_mastery_percentage: float = Field(..., description="Overall percentage of curriculum mastered by student")
    total_concepts_in_curriculum: int = Field(..., description="Total number of concepts in graph")
    known_concepts_count: int = Field(..., description="Number of concepts mastered")
    ready_now_count: int = Field(..., description="Number of concepts ready to study immediately ('NOW')")
    recommended_path: List[RecommendedTopic] = Field(..., description="Prioritized list of topics to study next ('NOW')")
    upcoming_next: List[RecommendedTopic] = Field(..., description="Upcoming topics almost ready to study ('NEXT')")
