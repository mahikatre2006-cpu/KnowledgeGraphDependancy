"""
format_router.py
================
Format detector, router, and confidence gate for Mumbai University syllabi.
Routes to:
 - nep_2026: delegates to nep_parse_v2.py unchanged
 - rev2019_comps: Computer Engineering REV-2019
 - rev2019_it: Information Technology REV-2019
 - nep_2025: NEP 2025-26 Second Year (7-digit codes)
 - unknown: unhandled formats or non-syllabi
"""
import re
import time
from typing import List, Tuple, Optional
import fitz

from app.parser.nep_parse_v2 import (
    NEPCourse,
    NEPModule,
    is_syllabus,
    parse_nep_text,
    _GENERIC,
    _PROC,
    _CAL,
)
from app.parser.adapters_rev2019_comps import parse_rev2019_comps_text
from app.parser.adapters_rev2019_it import parse_rev2019_it_text
from app.parser.adapters_nep_2025 import parse_nep_2025_text

_JUNK_PATTERNS = [
    re.compile(r'\b(break|holiday|vacation)\b', re.IGNORECASE),
    re.compile(r'\bunit\s+test\b', re.IGNORECASE),
    re.compile(r'\bcarried\b', re.IGNORECASE),
    re.compile(r'\ball\s+subjects\b', re.IGNORECASE),
    re.compile(r'^Mod\.?\s*\d', re.IGNORECASE),
    re.compile(r'^\d+[-–]\d+$'),
    re.compile(r'^\d{4}$'),
    re.compile(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b.*\d{4}', re.IGNORECASE),
    re.compile(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', re.IGNORECASE),
    re.compile(r'^\d+$'),
    re.compile(r'^[-–—\s]+$'),
    re.compile(r'^(?:co|lo)\s*\d', re.IGNORECASE),
    re.compile(r'https?://', re.IGNORECASE),
    re.compile(r'\.(?:org|com|edu|net|gov)/', re.IGNORECASE),
    re.compile(r'\b(?:tenenbaum|thareja|forouzan|tremblay|balagurusamy|shukla|kruse|press|pearson|oxford|wiley|mcgraw|edition|isbn)\b', re.IGNORECASE),
    re.compile(r'^(?:textbooks?|references?|assessment):?$', re.IGNORECASE),
    re.compile(r'\bdraft\s+copy\b', re.IGNORECASE),
    re.compile(r'\b(?:self[\s-]*(?:learning|study)|explore online|nptel)\b', re.IGNORECASE),
]


def is_junk_topic(topic: str) -> bool:
    """Returns True if topic matches noise or junk patterns."""
    t = topic.strip()
    if not (2 <= len(t) <= 120) or len(t.split()) > 10 or not re.search(r'[A-Za-z]', t):
        return True
    t_low = t.lower()
    if t_low in _GENERIC or bool(_PROC.match(t)) or bool(_CAL.search(t_low)):
        return True
    return any(bool(pat.search(t)) for pat in _JUNK_PATTERNS)


def calculate_course_junk_rate(course: NEPCourse) -> float:
    """Calculate ratio of junk topics to total topics in course."""
    topics = [
        t[0] if isinstance(t, (tuple, list)) else (t["name"] if isinstance(t, dict) else str(t))
        for t in course.topics
    ]
    if not topics:
        return 1.0
    n_junk = sum(1 for t in topics if is_junk_topic(t))
    return n_junk / len(topics)


def is_confident_course(course: NEPCourse) -> bool:
    """
    Confidence gate per course:
     - junk_rate <= 0.05
     - n_topics >= 8
     - at least 60% of modules have >= 3 topics
    """
    n_topics = len(course.topics)
    if n_topics < 8:
        return False
    junk_rate = calculate_course_junk_rate(course)
    if junk_rate > 0.05:
        return False
    n_mods = len(course.modules)
    if n_mods == 0:
        return False
    mods_ge_3 = sum(1 for m in course.modules if len(m.topics) >= 3)
    if (mods_ge_3 / n_mods) < 0.60:
        return False
    return True


def detect_format(text: str) -> str:
    """
    Detects syllabus format:
      "nep_2026" | "rev2019_comps" | "rev2019_it" | "nep_2025" | "unknown"
    """
    if not is_syllabus(text):
        return "unknown"

    has_comps = bool(re.search(r'\b(?:CSC|CSL)\d{3}\b', text))
    has_it = bool(re.search(r'\b(?:ITC|ITL)\d{3}\b', text))
    has_nep_26_codes = bool(re.search(r'\b23[4-9]\d{4,5}\b', text))
    has_nep_25_codes = bool(re.search(r'\b2\d{6}\b', text))

    if has_comps and not has_it and not has_nep_26_codes:
        return "rev2019_comps"
    if has_it and not has_comps and not has_nep_26_codes:
        return "rev2019_it"

    if has_nep_26_codes:
        ok, cs = parse_nep_text(text)
        if ok and cs:
            return "nep_2026"

    if has_nep_25_codes:
        return "nep_2025"

    return "unknown"


def parse_syllabus_pdf_bytes_routed(
    pdf_bytes: bytes
) -> Tuple[bool, List[NEPCourse], str, float, Optional[str]]:
    """
    Routes PDF bytes to appropriate format adapter and applies confidence gate.
    Returns: (ok, surviving_courses, format_name, parse_time_s, error_reason)
    error_reason is None or "not_a_syllabus" or "low_confidence" or "unknown_format".
    """
    t0 = time.perf_counter()
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "\n".join(p.get_text() for p in doc)
    except Exception:
        return False, [], "unknown", time.perf_counter() - t0, "not_a_syllabus"

    if not is_syllabus(text):
        return False, [], "unknown", time.perf_counter() - t0, "not_a_syllabus"

    fmt = detect_format(text)
    if fmt == "nep_2026":
        ok, raw_courses = parse_nep_text(text)
    elif fmt == "rev2019_comps":
        ok, raw_courses = parse_rev2019_comps_text(text)
    elif fmt == "rev2019_it":
        ok, raw_courses = parse_rev2019_it_text(text)
    elif fmt == "nep_2025":
        ok, raw_courses = parse_nep_2025_text(text)
    else:
        return False, [], "unknown", time.perf_counter() - t0, "low_confidence"

    elapsed = time.perf_counter() - t0

    if not ok or not raw_courses:
        return False, [], fmt, elapsed, "low_confidence"

    # Apply Confidence Gate per course
    surviving_courses = [c for c in raw_courses if is_confident_course(c)]
    if not surviving_courses:
        return False, [], fmt, elapsed, "low_confidence"

    return True, surviving_courses, fmt, elapsed, None

