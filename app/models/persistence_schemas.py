from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SaveProgressRequest(BaseModel):
    user_id: str = Field(..., json_schema_extra={"example": "user_123"}, description="User ID")
    known_concept_ids: List[str] = Field(..., json_schema_extra={"example": ["python", "vectors"]}, description="List of mastered concept IDs")


class PersistenceStatusResponse(BaseModel):
    success: bool
    message: str
    postgres_status: str
    neo4j_status: str
