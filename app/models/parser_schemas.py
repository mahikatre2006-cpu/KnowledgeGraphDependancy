from typing import List, Optional
from pydantic import BaseModel, Field


class ParsedTopic(BaseModel):
    id: str = Field(..., description="Unique slugified ID for the topic")
    name: str = Field(..., description="Cleaned topic title")
    unit_number: int = Field(default=1, description="Unit or module number this topic belongs to")
    unit_title: str = Field(default="", description="Title of the unit/module")


class ParsedUnit(BaseModel):
    unit_number: int = Field(..., description="Unit or module index (1-based)")
    title: str = Field(..., description="Title or header of the unit")
    topics: List[ParsedTopic] = Field(default_factory=list, description="Topics extracted within this unit")


class ParsedSyllabus(BaseModel):
    course_title: str = Field(default="Course Syllabus", description="Detected course name")
    course_code: str = Field(default="", description="Detected course code (e.g. CS101)")
    units: List[ParsedUnit] = Field(default_factory=list, description="Structured units detected")
    all_topics: List[ParsedTopic] = Field(default_factory=list, description="Flat list of all extracted topics")
    total_topics_count: int = Field(..., description="Total number of topics extracted")


class ParseTextRequest(BaseModel):
    text: str = Field(..., description="Raw syllabus text content to parse")
