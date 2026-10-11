"""
gemini_router.py
================
One endpoint: upload a syllabus PDF, get back the full teacher-facing result.
Self-contained (no shared state). Removed together with gemini_app.py,
gemini_service.py and gemini_pipeline.py.
"""

import hashlib
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.parser.pdf_parser import extract_text_from_pdf_bytes
from app.services import gemini_pipeline, gemini_service

router = APIRouter(prefix="/gemini", tags=["Gemini Syllabus Analysis"])

MULTI_SUBJECT_MIN_CHARS = 30_000
_cache: Dict[str, Dict[str, Any]] = {}


@router.post("/analyze")
async def analyze_syllabus(file: UploadFile = File(...), subject: Optional[str] = Form(default=None)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    content = await file.read()
    try:
        text = extract_text_from_pdf_bytes(content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not read this PDF: {exc}")

    cache_key = hashlib.sha256(content).hexdigest() + "|" + (subject or "")
    if cache_key in _cache:
        return _cache[cache_key]

    try:
        # Large PDFs usually hold many subjects: let the user pick one first.
        if not subject and len(text) > MULTI_SUBJECT_MIN_CHARS:
            subjects = gemini_service.list_subjects(text)
            if len(subjects) > 1:
                return {"needs_subject": True, "subjects": subjects}

        extracted = gemini_service.extract_syllabus(text, subject)
        result = gemini_pipeline.build_result(extracted)
    except gemini_service.GeminiError as exc:
        raise HTTPException(status_code=502, detail=f"AI service unavailable ({exc}). Please try again.")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    _cache[cache_key] = result
    return result
