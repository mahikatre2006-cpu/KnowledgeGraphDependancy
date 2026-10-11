"""
nep_syllabus_parser.py
======================
NEP 2026 University of Mumbai — IT/CE Semester V & VI Syllabus Parser.

Format expectations (per spec):
 - Course header: "Course Code | Course Name | Teaching Scheme" + 7-8 digit code
 - Labs: title contains "Lab" / "Mini Project" / "Professional Skill" / "Indian Knowledge"
 - Detailed Syllabus table: Sr.No | Name of Module | Detailed Content | Hours | CO Mapping
 - Module 0 = Prerequisites -> EXCLUDE
 - "Self-Learning Topics:" through row tail -> EXCLUDE
 - Tail strip: \\b\\d{1,2}\\s+(CO|LO)\\d... at end of module row
 - Section ends at "Total Hours"
 - Fallback: if no Detailed Syllabus span found, use SyllabusExtractor (existing), same filter
"""

import re
import tempfile
import os
from time import perf_counter
from typing import List, Dict, Tuple, Optional
from app.parser.nep_parse_v2 import * 
# ---------------------------------------------------------------------------
# Compiled regexes
# ---------------------------------------------------------------------------

# 7-8 digit course codes used by Mumbai University NEP scheme
_COURSE_CODE_RE = re.compile(r'\b(\d{7,8})\b')

# Course header line — code followed by course name
_COURSE_HEADER_RE = re.compile(
    r'(?:Course\s+Code|Course\s+Name|Teaching\s+Scheme)',
    re.IGNORECASE
)

# Full syllabus section markers
_DETAILED_SYLLABUS_START_RE = re.compile(
    r'(?:DETAILED\s+SYLLABUS|Detailed\s+Syllabus)\s*:?',
    re.IGNORECASE
)
_TOTAL_HOURS_RE = re.compile(r'\bTotal\s+Hours\b', re.IGNORECASE)

# Module header: row starting with 0..6 or I..VI (Roman IKS)
_MODULE_NUM_RE = re.compile(
    r'^(?P<num>0|[1-6]|[IVX]+)\s+(?P<title>.+)$',
    re.IGNORECASE
)
_ROMAN_MAP = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6}

# Self-learning marker (strip from this point to row end)
_SELF_LEARNING_RE = re.compile(
    r'Self[\s\-]*Learning\s+Topics?\s*:',
    re.IGNORECASE
)

# CO/LO tail at end of content column: e.g. "06 CO1" or "04 CO2, CO3"
_CO_LO_TAIL_RE = re.compile(
    r'\s*\b\d{1,2}\s+(?:CO|LO)\d(?:\s*[,\-]\s*(?:CO|LO)?\d)*\s*$',
    re.IGNORECASE
)

# "N Hours CO..." at end of content string
_HOURS_CO_TAIL_RE = re.compile(
    r'\s*\d{1,2}\s+(?:CO|LO)\d[\d,\s]*$',
    re.IGNORECASE
)

# Topic split: comma / semicolon / " - " but NOT inside parens and NOT & or "and"
_SPLIT_CHARS_RE = re.compile(
    r'(?<!\w)(?:[;,]|\s+[-–—]\s+)(?![^(]*\))',
)

# Sub-label ending in ":"  e.g. "Black Box Testing:" — strip as separator
_SUB_LABEL_RE = re.compile(r'^[A-Za-z][^:]{1,40}:\s*')

# Generic singletons to reject (generalised — word-level, not string-match)
_GENERIC_WORDS = frozenset({
    'introduction', 'overview', 'basics', 'best', 'practices', 'applications',
    'challenges', 'case', 'studies', 'installation', 'installing', 'libraries',
    'environment', 'setup', 'first', 'app', 'folder', 'file', 'structure',
    'break', 'holiday', 'vacation', 'unit', 'test', 'carried', 'subjects',
    'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
    'september', 'october', 'november', 'december',
    'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
})

# Procedural / calendar / junk patterns
_JUNK_PATTERNS = [
    re.compile(r'\b(break|holiday|vacation)\b', re.IGNORECASE),
    re.compile(r'\bunit\s+test\b', re.IGNORECASE),
    re.compile(r'\bcarried\b', re.IGNORECASE),
    re.compile(r'\ball\s+subjects\b', re.IGNORECASE),
    re.compile(r'^Mod\.?\s*\d', re.IGNORECASE),
    re.compile(r'^\d+[-–]\d+$'),          # numeric ranges like "1-3"
    re.compile(r'^\d{4}$'),               # years
    re.compile(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b.*\d{4}', re.IGNORECASE),
    re.compile(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', re.IGNORECASE),
    re.compile(r'^\d+$'),                 # bare number
    re.compile(r'^[-–—\s]+$'),            # dashes only
    re.compile(r'^(co|lo)\s*\d', re.IGNORECASE),   # CO1, LO2 alone
    re.compile(r'https?://', re.IGNORECASE),
    re.compile(r'\.(org|com|edu|net|gov)/', re.IGNORECASE),
]

# Acronym detector — all uppercase 2-8 chars: must survive filter
_ACRONYM_RE = re.compile(r'^[A-Z]{2,8}(?:\*|\+)?$')

# Words that indicate IS-SYLLABUS gate
_IS_SYLLABUS_KEYWORDS = {
    'detailed syllabus', 'course objectives', 'course outcomes',
    'name of module', 'self-learning topics', 'course code',
}


# ---------------------------------------------------------------------------
# Public data classes (simple dicts for now — avoids Pydantic overhead)
# ---------------------------------------------------------------------------

class NEPCourse:
    __slots__ = ('code', 'title', 'kind', 'modules', 'topics')

    def __init__(self, code: str, title: str, kind: str):
        self.code: str = code
        self.title: str = title
        self.kind: str = kind           # 'theory' | 'lab'
        self.modules: List[Dict] = []   # [{idx, title, topics:[str]}]
        self.topics: List[Dict] = []    # flat [{name, module_idx, course_code}]


# ---------------------------------------------------------------------------
# is_syllabus gate
# ---------------------------------------------------------------------------

def is_syllabus(text: str) -> bool:
    """
    Returns True if text contains >=2 of the 6 NEP gate keywords.
    Used to reject calendars, timetables, etc.
    """
    t_low = text.lower()
    hits = sum(1 for kw in _IS_SYLLABUS_KEYWORDS if kw in t_low)
    return hits >= 2


# ---------------------------------------------------------------------------
# Main parser entry point
# ---------------------------------------------------------------------------

def parse_nep_pdf_bytes(pdf_bytes: bytes) -> Tuple[bool, List[NEPCourse], float]:
    """
    Parse a NEP 2026 Mumbai University IT/CE syllabus PDF.

    Returns:
        (gate_passed: bool, courses: List[NEPCourse], parse_time_s: float)

    If gate_passed is False, courses is [] and callers should raise HTTP 422.
    Uses PyMuPDF — writes to a temp file to avoid the deprecated stream API warning.
    """
    t0 = perf_counter()

    # Extract text via PyMuPDF
    import fitz
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        doc = fitz.open(tmp_path)
        pages_text = []
        for pg in range(doc.page_count):
            page = doc.load_page(pg)
            blocks = [b for b in page.get_text("blocks") if b[6] == 0]
            blocks_sorted = sorted(blocks, key=lambda b: (b[1], b[0]))
            page_lines = []
            for b in blocks_sorted:
                for line in b[4].splitlines():
                    if line.strip():
                        page_lines.append(line.strip())
            pages_text.append('\n'.join(page_lines))
        doc.close()
    finally:
        os.unlink(tmp_path)

    full_text = '\n'.join(pages_text)

    # Gate check
    if not is_syllabus(full_text):
        return False, [], perf_counter() - t0

    # Segment and parse courses
    courses = _segment_and_parse(full_text)
    return True, courses, perf_counter() - t0


def parse_nep_text(text: str) -> Tuple[bool, List[NEPCourse]]:
    """
    Parse pre-extracted text (used in tests / fallback).
    Returns (gate_passed, courses).
    """
    if not is_syllabus(text):
        return False, []
    courses = _segment_and_parse(text)
    return True, courses


# ---------------------------------------------------------------------------
# Segmentation by course header
# ---------------------------------------------------------------------------

def _segment_and_parse(full_text: str) -> List[NEPCourse]:
    """
    Splits full PDF text into per-course segments, then parses each.
    Strategy: find lines where a 7-digit code appears + surrounding context
    looks like a course header (next or same line has a course name).
    """
    lines = full_text.split('\n')
    # Find course-start positions
    course_starts: List[Tuple[int, str, str]] = []  # (line_idx, code, title)

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = _COURSE_CODE_RE.search(line)
        if m:
            code = m.group(1)
            # Try to extract title from same line or adjacent lines
            title = _extract_title_near(lines, i, code)
            if title:
                course_starts.append((i, code, title))
        i += 1

    if not course_starts:
        return []

    # Deduplicate: keep first occurrence of each code
    seen_codes: set = set()
    unique_starts: List[Tuple[int, str, str]] = []
    for entry in course_starts:
        if entry[1] not in seen_codes:
            seen_codes.add(entry[1])
            unique_starts.append(entry)

    # Build per-course text slices
    courses: List[NEPCourse] = []
    for idx_in_list, (line_start, code, title) in enumerate(unique_starts):
        if idx_in_list + 1 < len(unique_starts):
            line_end = unique_starts[idx_in_list + 1][0]
        else:
            line_end = len(lines)

        course_lines = lines[line_start:line_end]
        course_text = '\n'.join(course_lines)

        kind = _detect_kind(title, course_text=course_text, code=code)
        course = NEPCourse(code=code, title=title, kind=kind)

        # Check if there's a Detailed Syllabus section
        if _DETAILED_SYLLABUS_START_RE.search(course_text):
            _parse_detailed_syllabus_section(course, course_text)
        else:
            # Fallback to existing SyllabusExtractor
            _parse_fallback(course, course_text)

        if course.topics:
            courses.append(course)

    return courses


def _extract_title_near(lines: List[str], idx: int, code: str) -> Optional[str]:
    """
    Title = join header lines until the 'Teaching Scheme' line.
    """
    title_parts: List[str] = []
    line = lines[idx].strip()
    rem = _COURSE_CODE_RE.sub('', line)
    rem = re.sub(r'Course\s+Code\s*\|\s*Course\s+Name(?:\s*\|\s*Teaching\s+Scheme)?', '', rem, flags=re.IGNORECASE)
    rem = re.sub(r'^[\|\s\-]+|[\|\s\-]+$', '', rem).strip()
    if rem and not re.search(r'\b(Teaching\s+Scheme|Theory|Practical|Tutorial|Credits?|Marks?)\b', rem, re.IGNORECASE):
        title_parts.append(rem)

    j = idx + 1
    while j < len(lines):
        nxt = lines[j].strip()
        if re.search(r'\b(Teaching\s+Scheme|Theory\s+Practical)\b', nxt, re.IGNORECASE):
            break
        cleaned = re.sub(r'^[\|\s\-]+|[\|\s\-]+$', '', nxt).strip()
        if cleaned and not _COURSE_CODE_RE.search(cleaned):
            if not re.search(r'\b(Credits?|Marks?|Hours?)\b', cleaned, re.IGNORECASE):
                title_parts.append(cleaned)
        j += 1

    if title_parts:
        return ' '.join(title_parts).strip()

    return None


def _detect_kind(title: str, course_text: str = "", code: str = "") -> str:
    """Kind = lab if the code is the lab code per the 'Lab Description' table or the text contains 'Lab Objectives'."""
    if "lab objectives" in course_text.lower():
        return "lab"
    if "lab description" in course_text.lower():
        return "lab"
    if code.endswith("L") or code.endswith("P"):
        return "lab"
    lab_markers = re.compile(
        r'\b(Lab|Laboratory|Mini\s+Project|Professional\s+Skill|Indian\s+Knowledge)\b',
        re.IGNORECASE
    )
    return 'lab' if lab_markers.search(title) else 'theory'


# ---------------------------------------------------------------------------
# Detailed Syllabus section parser
# ---------------------------------------------------------------------------

def _parse_detailed_syllabus_section(course: NEPCourse, text: str) -> None:
    """
    Finds the "DETAILED SYLLABUS" ... "Total Hours" span and parses modules.
    Module 0 (Prerequisites) is excluded.
    """
    # Find start
    start_m = _DETAILED_SYLLABUS_START_RE.search(text)
    if not start_m:
        return
    body = text[start_m.end():]

    # Find end
    end_m = _TOTAL_HOURS_RE.search(body)
    if end_m:
        body = body[:end_m.start()]

    # Dump ONLY the text between "Detailed Syllabus" and "Total Hours" for course 2345113 to /tmp/c.txt
    if course.code == '2345113':
        try:
            os.makedirs('/tmp', exist_ok=True)
            with open('/tmp/c.txt', 'w', encoding='utf-8') as f:
                f.write(body.strip() + '\n')
        except Exception:
            pass

    # Now parse module rows out of `body`
    # The table has: Sr.No | Name of Module | Detailed Content | Hours | CO Mapping
    # Lines often wrap. Strategy: detect module number lines, collect content between them.
    _extract_modules_from_body(course, body)


def _extract_modules_from_body(course: NEPCourse, body: str) -> None:
    """
    Parse module blocks from syllabus table body text.
    Handles column-scrambled / line-wrapped text from PyMuPDF.
    """
    lines = [l.rstrip() for l in body.split('\n')]
    lines = _fix_hyphen_linebreaks(lines)

    # Join wrapped lines: accumulate until we hit a new module number
    module_blocks: List[Tuple[int, str, List[str]]] = []  # (mod_num, mod_title, content_lines)
    current_num: Optional[int] = None
    current_title: str = ''
    current_content: List[str] = []

    def _roman_to_int(s: str) -> Optional[int]:
        s = s.upper()
        return _ROMAN_MAP.get(s)

    def _flush():
        if current_num is not None and current_num > 0:
            module_blocks.append((current_num, current_title, current_content[:]))

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Try to detect a module header row
        # Pattern: line starts with "0", "1"-"6", or Roman "I".."VI"
        m = re.match(r'^\s*([0-6]|I{1,3}V?|VI?|IV|IX|V?I{0,3})\s+(\S.*)', stripped, re.IGNORECASE)
        if m:
            raw_num = m.group(1)
            rest = m.group(2).strip()

            # Resolve number
            if raw_num.isdigit():
                num = int(raw_num)
            else:
                num = _roman_to_int(raw_num)
                if num is None:
                    # Not a real module header, treat as content
                    if current_num is not None:
                        current_content.append(stripped)
                    continue

            _flush()
            current_num = num
            current_title = rest
            current_content = []
        else:
            if current_num is not None:
                current_content.append(stripped)

    _flush()

    # Now extract topics from each module
    seen_global: set = set()
    for mod_num, mod_title, content_lines in module_blocks:
        content_text = ' '.join(content_lines)

        # Strip Self-Learning part from content
        sl_m = _SELF_LEARNING_RE.search(content_text)
        if sl_m:
            content_text = content_text[:sl_m.start()]

        # Strip CO/LO tail
        content_text = _CO_LO_TAIL_RE.sub('', content_text)
        content_text = _HOURS_CO_TAIL_RE.sub('', content_text)

        topics = _extract_topics_from_content(content_text)

        # Deduplicate globally within course
        deduped = []
        for t in topics:
            norm = _normalize(t)
            if norm and norm not in seen_global:
                seen_global.add(norm)
                deduped.append(t)

        if deduped:
            course.modules.append({
                'idx': mod_num,
                'title': mod_title,
                'topics': deduped,
            })
            for t in deduped:
                course.topics.append({
                    'name': t,
                    'module_idx': mod_num,
                    'course_code': course.code,
                })


def _fix_hyphen_linebreaks(lines: List[str]) -> List[str]:
    """Join lines where a word was broken with a hyphen at end of line."""
    result: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.rstrip().endswith('-') and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line and next_line[0].islower():
                result.append(line.rstrip()[:-1] + next_line)
                i += 2
                continue
        result.append(line)
        i += 1
    return result


def _extract_topics_from_content(content: str) -> List[str]:
    """
    Split module content text into individual topics.
    Splits on: comma, semicolon, " - " (not inside parens), colon sub-labels.
    Does NOT split on & or "and".
    """
    # First handle sub-labels ending in ":" — they act as category separators
    # E.g. "Black Box Testing: equivalence, boundary" -> two splits at ":"
    # But keep the label text as a potential topic too
    # Strategy: split on ":" only when remainder > 2 chars and label is word-like
    content = re.sub(r'\s+', ' ', content).strip()

    # Replace "sub-label:" with "sub-label, " so the label survives splitting
    content = re.sub(r'([A-Za-z][A-Za-z\s]{1,35}):\s+', r'\1, ', content)

    # Split on , ; or " - " but not inside parentheses
    parts = _split_outside_parens(content)

    topics = []
    for part in parts:
        part = part.strip().strip('.,;:')
        if not part:
            continue
        # Strip leading bullets/numbers
        part = re.sub(r'^[•\*\-–—\d]+[.)]\s*', '', part).strip()
        part = re.sub(r'^\d+\s+', '', part).strip()
        # Normalise whitespace
        part = re.sub(r'\s+', ' ', part).strip()
        if _is_valid_topic(part):
            topics.append(part)
    return topics


def _split_outside_parens(text: str) -> List[str]:
    """Split text on comma/semicolon/ ' - ' but not inside parentheses."""
    parts = []
    depth = 0
    current = []
    i = 0
    while i < len(text):
        c = text[i]
        if c == '(':
            depth += 1
            current.append(c)
        elif c == ')':
            depth = max(0, depth - 1)
            current.append(c)
        elif depth == 0:
            # Check for split patterns
            if c in (',', ';', ':'):
                parts.append(''.join(current))
                current = []
            elif c == ' ' and i + 2 < len(text) and text[i:i+3] in (' - ', ' – ', ' — '):
                parts.append(''.join(current))
                current = []
                i += 3
                continue
            else:
                current.append(c)
        else:
            current.append(c)
        i += 1
    if current:
        parts.append(''.join(current))
    return parts


# ---------------------------------------------------------------------------
# Topic validity filter (generalised — not string-matching)
# ---------------------------------------------------------------------------

def _is_valid_topic(text: str) -> bool:
    """
    Returns True if `text` is a valid, retainable topic name.
    Rules per spec:
    - 1-8 words, >= 2 chars, must contain a letter
    - Acronyms (DOM, REPL, RMMM, CSP, SQL) MUST survive
    - Reject generic singletons, procedural terms, dates/weekdays
    - Reject junk patterns
    """
    if not text or len(text) < 2:
        return False

    # Must contain at least one letter
    if not re.search(r'[A-Za-z]', text):
        return False

    words = text.split()
    n_words = len(words)

    # Word count: 1-8
    if n_words < 1 or n_words > 8:
        return False

    # Acronyms always pass
    if _ACRONYM_RE.match(text):
        return True

    # Single generic words are rejected
    if n_words == 1 and words[0].lower() in _GENERIC_WORDS:
        return False

    # Multi-word phrases containing ONLY generic words are rejected
    if all(w.lower() in _GENERIC_WORDS for w in words):
        return False

    # Junk patterns
    for pat in _JUNK_PATTERNS:
        if pat.search(text):
            return False

    return True


def _normalize(text: str) -> str:
    """Normalise for deduplication (lowercase, collapse spaces, strip punct)."""
    return re.sub(r'\s+', ' ', text.lower().strip().strip('.,;:'))


# ---------------------------------------------------------------------------
# Fallback: use existing SyllabusExtractor + same filter
# ---------------------------------------------------------------------------

def _parse_fallback(course: NEPCourse, text: str) -> None:
    """
    For 2019-style format (no 'Detailed Syllabus' header), fall back to the
    existing regex-based SyllabusExtractor, then apply the same topic filter.
    """
    from app.parser.syllabus_extractor import SyllabusExtractor

    parsed = SyllabusExtractor.parse(text)
    seen: set = set()
    for unit in parsed.units:
        topics: List[str] = []
        for topic in unit.topics:
            if _is_valid_topic(topic.name):
                norm = _normalize(topic.name)
                if norm not in seen:
                    seen.add(norm)
                    topics.append(topic.name)
        if topics:
            course.modules.append({
                'idx': unit.unit_number,
                'title': unit.title,
                'topics': topics,
            })
            for t in topics:
                course.topics.append({
                    'name': t,
                    'module_idx': unit.unit_number,
                    'course_code': course.code,
                })

