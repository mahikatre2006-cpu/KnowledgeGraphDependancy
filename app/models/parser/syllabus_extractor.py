"""
Backward-compatibility alias. Canonical implementation lives in app.parser.syllabus_extractor.
"""
from app.parser.syllabus_extractor import SyllabusExtractor, slugify

__all__ = ["SyllabusExtractor", "slugify"]
