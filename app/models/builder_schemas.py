from typing import List, Dict, Any
from pydantic import BaseModel, Field
from app.models.parser_schemas import ParsedSyllabus
from app.models.graph_schemas import GraphSummaryResponse
from app.graph.models import ConceptNode


class BuildGraphResponse(BaseModel):
    message: str = Field(..., description="Success message")
    course_title: str = Field(..., description="Course title")
    course_code: str = Field(..., description="Course code")
    nodes_added: int = Field(..., description="Total concept nodes created")
    units_processed: int = Field(..., description="Total units processed")


class FullPipelineResponse(BaseModel):
    message: str = Field(..., description="Success message for end-to-end processing")
    parsed_syllabus: ParsedSyllabus = Field(..., description="Extracted syllabus units and topics")
    graph_summary: GraphSummaryResponse = Field(..., description="Summary of created concept graph")
    topological_sequence: List[ConceptNode] = Field(..., description="Generated topological study sequence")
