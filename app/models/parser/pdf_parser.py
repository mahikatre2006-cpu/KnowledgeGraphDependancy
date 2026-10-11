"""
Backward-compatibility alias. Canonical implementation lives in app.parser.pdf_parser.
"""
from app.parser.pdf_parser import extract_text_from_pdf_bytes, clean_pdf_text

__all__ = ["extract_text_from_pdf_bytes", "clean_pdf_text"]
