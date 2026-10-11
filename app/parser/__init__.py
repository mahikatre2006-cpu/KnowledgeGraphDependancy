"""
PDF Parser module for extracting and normalizing text from syllabus PDF files.
"""
from app.parser.pdf_parser import extract_text_from_pdf_bytes, clean_pdf_text
from app.parser.syllabus_extractor import SyllabusExtractor

__all__ = ["extract_text_from_pdf_bytes", "clean_pdf_text", "SyllabusExtractor"]

