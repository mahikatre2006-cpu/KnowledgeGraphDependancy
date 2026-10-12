"""
gemini_service.py
=================
Optional Gemini layer (self-contained; delete this file with gemini_router.py,
gemini_pipeline.py and gemini_app.py to remove the feature).

Gemini only does the language work: reading messy syllabus text and returning clean
topics plus the foundational concepts the syllabus assumes but never teaches.
Prerequisite edges are still predicted by the trained XGBoost classifier.

The API key is read from GEMINI_API_KEY in the project's .env file.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MODELS = ["gemini-2.5-flash", "gemini-flash-latest"]
MAX_TEXT_CHARS = 600_000


class GeminiError(Exception):
    """Raised for any Gemini failure (missing key, HTTP error, unusable response)."""


def _api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key and ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if line.startswith("GEMINI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        raise GeminiError("GEMINI_API_KEY is not set in .env")
    return key


def _call(prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    """Sends one prompt, forces JSON output matching `schema`, retries transient errors."""
    key = _api_key()
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    }
    last_error = "unknown error"
    for model in MODELS:
        for attempt in range(3):
            try:
                resp = httpx.post(
                    API_URL.format(model=model),
                    params={"key": key},
                    json=body,
                    timeout=180,
                )
            except httpx.HTTPError as exc:
                last_error = f"network error: {type(exc).__name__}"
                time.sleep(2 * (attempt + 1))
                continue

            if resp.status_code == 200:
                try:
                    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(text)
                except (KeyError, IndexError, ValueError):
                    last_error = "Gemini returned an unreadable response"
                    break
            last_error = f"Gemini HTTP {resp.status_code}"
            if resp.status_code in (429, 500, 503):
                time.sleep(3 * (attempt + 1))
                continue
            break  # 400/403 etc: retrying the same model will not help
    raise GeminiError(last_error)


_SUBJECTS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "subjects": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "course_code": {"type": "STRING"},
                    "course_title": {"type": "STRING"},
                },
                "required": ["course_code", "course_title"],
            },
        }
    },
    "required": ["subjects"],
}

_ANALYSIS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "course_title": {"type": "STRING"},
        "course_code": {"type": "STRING"},
        "topics": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "unit_number": {"type": "INTEGER"},
                    "unit_title": {"type": "STRING"},
                },
                "required": ["name", "unit_number", "unit_title"],
            },
        },
        "missing_prerequisites": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "reason": {"type": "STRING"},
                    "needed_for": {"type": "ARRAY", "items": {"type": "STRING"}},
                },
                "required": ["name", "reason", "needed_for"],
            },
        },
    },
    "required": ["course_title", "course_code", "topics", "missing_prerequisites"],
}


def list_subjects(text: str) -> List[Dict[str, str]]:
    """Lists the distinct subjects (course code + title) found in a syllabus document."""
    prompt = (
        "The text below is a university syllabus document. It may contain one subject or many.\n"
        "List every distinct subject that has its own syllabus content (course code and title).\n"
        "Ignore lab, mini-project, workshop and capstone subjects. Do not invent subjects.\n\n"
        f"SYLLABUS TEXT:\n{text[:MAX_TEXT_CHARS]}"
    )
    return _call(prompt, _SUBJECTS_SCHEMA).get("subjects", [])


def extract_syllabus(text: str, subject: Optional[str] = None) -> Dict[str, Any]:
    """Extracts clean topics and assumed-but-untaught prerequisites for one subject."""
    focus = (
        f"Analyse ONLY the subject '{subject}'. Ignore every other subject in the text.\n"
        if subject
        else "The text is a single subject's syllabus.\n"
    )
    prompt = (
        "You are building a prerequisite map from a university syllabus.\n"
        f"{focus}\n"
        "1. topics: the real teachable topics of the subject, in syllabus order. Rules:\n"
        "   - Each name is a short concept (2 to 6 words), e.g. 'Binary Search Trees'.\n"
        "   - Split comma-separated lists into separate topics, but merge trivial sub-points.\n"
        "   - Target 20 to 45 topics in total. unit_number starts at 1 and follows the syllabus units.\n"
        "   - Exclude cover-page text, watermarks, page numbers, headers, exam schemes, marks,\n"
        "     hours, credits, course outcomes, references, textbooks, authors and publishers.\n"
        "2. missing_prerequisites: 3 to 8 foundational concepts a student must already know to\n"
        "   follow this subject but that the syllabus does NOT teach. For each give a one-sentence\n"
        "   reason and needed_for: the exact names (copied from your topics list) that depend on it.\n"
        "3. course_title and course_code as printed (empty string if absent).\n\n"
        f"SYLLABUS TEXT:\n{text[:MAX_TEXT_CHARS]}"
    )
    return _call(prompt, _ANALYSIS_SCHEMA)
