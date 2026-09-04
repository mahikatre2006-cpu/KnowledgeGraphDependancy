from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ConceptNode(BaseModel):
    """Represents a single topic or concept within the knowledge graph."""
    id: str = Field(..., description="Unique identifier for the concept node (e.g. 'linear_algebra')")
    name: str = Field(..., description="Human-readable title of the concept (e.g. 'Linear Algebra')")
    unit: str = Field(default="", description="Unit or module this concept belongs to")
    description: str = Field(default="", description="Detailed summary or description of the concept")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary additional key-value metadata")

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, ConceptNode):
            return self.id == other.id
        return False


class DependencyEdge(BaseModel):
    """Represents a directed dependency edge from source (prerequisite) to target (dependent)."""
    source_id: str = Field(..., description="Concept ID of the prerequisite topic")
    target_id: str = Field(..., description="Concept ID of the dependent topic")
    relationship_type: str = Field(default="prerequisite", description="Type of relationship (e.g. 'prerequisite', 'co-requisite')")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score of relationship (0.0 to 1.0)")
    reason: str = Field(default="", description="Textual explanation of why this prerequisite relationship exists")

    def __hash__(self):
        return hash((self.source_id, self.target_id))

    def __eq__(self, other):
        if isinstance(other, DependencyEdge):
            return self.source_id == other.source_id and self.target_id == other.target_id
        return False
