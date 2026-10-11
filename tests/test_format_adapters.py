"""
tests/test_format_adapters.py
=============================
Tests for Mumbai University syllabus format router, adapters, and confidence gate.
Uses real files from DATA/raw and tests/fixtures only.
"""
import json
import re
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.parser.nep_parse_v2 import parse_nep_pdf_bytes
from app.parser.format_router import (
    parse_syllabus_pdf_bytes_routed,
    calculate_course_junk_rate,
    is_confident_course,
    detect_format,
)

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "DATA" / "raw"
GOLDEN_PATH = BASE_DIR / "tests" / "golden" / "nep_real_topics.json"
REAL_NEP_PATH = BASE_DIR / "tests" / "fixtures" / "REAL_nep.pdf"

client = TestClient(app)


def norm_str(s: str) -> str:
    """Normalize apostrophes, quotes, and case for substring checks."""
    s_clean = s.lower()
    for ch in ["’", "‘", "`", "´", "\u2019", "\u2018", "\x92"]:
        s_clean = s_clean.replace(ch, "'")
    return s_clean


# ---------------------------------------------------------------------------
# Test 1: Assert REAL_nep golden parse is unchanged
# ---------------------------------------------------------------------------

def test_real_nep_golden_topics_unchanged():
    """Asserts that current REAL_nep parse matches golden topics exactly."""
    assert GOLDEN_PATH.exists(), f"Golden file missing: {GOLDEN_PATH}"
    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        golden_data = json.load(f)

    with open(REAL_NEP_PATH, "rb") as f:
        ok, courses, _ = parse_nep_pdf_bytes(f.read())

    assert ok, "REAL_nep.pdf must parse successfully"
    real_data = {
        c.code: {
            "title": c.title,
            "kind": c.kind,
            "modules": [
                {"index": m.index, "name": m.name, "topics": m.topics}
                for m in c.modules
            ]
        }
        for c in courses
    }
    assert real_data == golden_data, "REAL_nep parse has changed from golden reference"


# ---------------------------------------------------------------------------
# Test 2: Comps REV-2019 — CSC303 Data Structure
# ---------------------------------------------------------------------------

def test_csc303_data_structure():
    """
    CSC303 Data Structure:
     - 6 modules
     - MUST: adt of stack, infix to postfix, binary search tree, huffman, depth first search, hash functions, collision resolution
     - MUST NOT: tenenbaum, nptel, textbooks
    """
    pdf_path = RAW_DIR / "2019-scheme" / "Computer-Engineering" / "be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf"
    assert pdf_path.exists(), f"Missing file: {pdf_path}"

    with open(pdf_path, "rb") as f:
        ok, courses, fmt, _, _ = parse_syllabus_pdf_bytes_routed(f.read())

    assert ok, f"Failed to parse {pdf_path}"
    assert fmt == "rev2019_comps"

    csc303 = next((c for c in courses if c.code == "CSC303"), None)
    assert csc303 is not None, "CSC303 not found in parsed courses"
    assert len(csc303.modules) == 6, f"Expected 6 modules in CSC303, got {len(csc303.modules)}"

    topics_blob = " ".join(norm_str(t[0]) for t in csc303.topics)

    must_have = [
        "adt of stack",
        "infix to postfix",
        "binary search tree",
        "huffman",
        "depth first search",
        "hash functions",
        "collision resolution",
    ]
    for m in must_have:
        assert m in topics_blob, f"CSC303 missing required golden topic: '{m}'"

    must_not_have = ["tenenbaum", "nptel", "textbooks"]
    for mn in must_not_have:
        assert mn not in topics_blob, f"CSC303 leaked forbidden topic: '{mn}'"


# ---------------------------------------------------------------------------
# Test 3: IT REV-2019 — ITC302 Data Structure and Analysis
# ---------------------------------------------------------------------------

def test_itc302_data_structure_and_analysis():
    """
    ITC302 Data Structure and Analysis:
     - 6 modules
     - MUST: circular queue, avl tree, breadth first search, dijkstra, radix sort
     - MUST NOT: implementation of avl and b+ tree, linked list implementation of stack, structure variables
    Note: Real files in DATA/raw contain TE IT (6.12) and BE IT (6.23).
    If ITC302 is present in any IT file in DATA/raw, verify; otherwise skip with UNVERIFIED note.
    """
    itc302_course = None
    for p in RAW_DIR.rglob("*.pdf"):
        with open(p, "rb") as f:
            data = f.read()
        ok, courses, fmt, _, _ = parse_syllabus_pdf_bytes_routed(data)
        if ok and fmt == "rev2019_it":
            for c in courses:
                if c.code == "ITC302" or "data structure and analysis" in norm_str(c.title):
                    itc302_course = c
                    break
        if itc302_course:
            break

    if itc302_course is None:
        pytest.skip(
            "ITC302 Data Structure and Analysis is not present in DATA/raw "
            "(only TE IT 6.12 and BE IT 6.23 are in DATA/raw; SE IT is absent). UNVERIFIED."
        )

    assert len(itc302_course.modules) == 6
    topics_blob = " ".join(norm_str(t[0]) for t in itc302_course.topics)

    must_have = [
        "circular queue",
        "avl tree",
        "breadth first search",
        "dijkstra",
        "radix sort",
    ]
    for m in must_have:
        assert m in topics_blob, f"ITC302 missing required topic: '{m}'"

    must_not_have = [
        "implementation of avl and b+ tree",
        "linked list implementation of stack",
        "structure variables",
    ]
    for mn in must_not_have:
        assert mn not in topics_blob, f"ITC302 leaked forbidden topic: '{mn}'"


# ---------------------------------------------------------------------------
# Test 4: NEP 2025 — Discrete Structures and Graph Theory (2163112 / 2023112)
# ---------------------------------------------------------------------------

def test_nep_2025_discrete_structures():
    """
    Discrete Structures and Graph Theory (NEP 2025):
     - 6 modules
     - MUST: propositional logic, warshall, hasse diagram, injective, pigeonhole, cut vertex
     - MUST NOT: prolog, network flow, draft copy
    """
    pdf_path = RAW_DIR / "2019-scheme" / "AI-ML" / "6.21-N-B.E.-AI-ML-sem-III-IV.pdf"
    assert pdf_path.exists(), f"Missing file: {pdf_path}"

    with open(pdf_path, "rb") as f:
        ok, courses, fmt, _, _ = parse_syllabus_pdf_bytes_routed(f.read())

    assert ok, f"Failed to parse {pdf_path}"
    assert fmt == "nep_2025"

    ds = next(
        (c for c in courses if c.code in ("2163112", "2023112") or "discrete structures" in norm_str(c.title)),
        None
    )
    assert ds is not None, "Discrete Structures and Graph Theory not found"
    assert len(ds.modules) == 6, f"Expected 6 modules, got {len(ds.modules)}"

    topics_blob = " ".join(norm_str(t[0]) for t in ds.topics)

    must_have = [
        "propositional logic",
        "warshall",
        "hasse diagram",
        "injective",
        "pigeonhole",
        "cut vertex",
    ]
    for m in must_have:
        assert m in topics_blob, f"Discrete Structures missing required topic: '{m}'"

    must_not_have = ["prolog", "network flow", "draft copy"]
    for mn in must_not_have:
        assert mn not in topics_blob, f"Discrete Structures leaked forbidden topic: '{mn}'"


# ---------------------------------------------------------------------------
# Test 5: NEP 2025 — Operating System (2164113 / 2024113)
# ---------------------------------------------------------------------------

def test_nep_2025_operating_system():
    """
    Operating System (NEP 2025):
     - MUST: peterson, page replacement, banker
     - MUST NOT: real-time scheduling algorithms
    """
    pdf_path = RAW_DIR / "2019-scheme" / "AI-ML" / "6.21-N-B.E.-AI-ML-sem-III-IV.pdf"
    assert pdf_path.exists(), f"Missing file: {pdf_path}"

    with open(pdf_path, "rb") as f:
        ok, courses, fmt, _, _ = parse_syllabus_pdf_bytes_routed(f.read())

    assert ok, f"Failed to parse {pdf_path}"
    assert fmt == "nep_2025"

    os_c = next(
        (c for c in courses if c.code in ("2164113", "2024113") or "operating system" in norm_str(c.title)),
        None
    )
    assert os_c is not None, "Operating System not found"

    topics_blob = " ".join(norm_str(t[0]) for t in os_c.topics)

    must_have = ["peterson", "page replacement", "banker"]
    for m in must_have:
        assert m in topics_blob, f"Operating System missing required topic: '{m}'"

    must_not_have = ["real-time scheduling algorithms"]
    for mn in must_not_have:
        assert mn not in topics_blob, f"Operating System leaked forbidden topic: '{mn}'"


# ---------------------------------------------------------------------------
# Test 6: Every PDF in DATA/raw passes confidence gate (junk_rate <= 0.05) or is rejected
# ---------------------------------------------------------------------------

def test_all_data_raw_pdfs_confidence_and_junk_rate():
    """
    Every PDF in DATA/raw:
     - Either passes with junk_rate <= 0.05 over surviving courses
     - Or is rejected as low_confidence / not_a_syllabus
    """
    pdf_files = list(RAW_DIR.rglob("*.pdf"))
    assert len(pdf_files) > 0, "DATA/raw must contain PDFs"

    passed_count = 0
    rejected_count = 0

    for pdf_path in pdf_files:
        with open(pdf_path, "rb") as f:
            data = f.read()
        ok, courses, fmt, _, err = parse_syllabus_pdf_bytes_routed(data)
        if ok:
            passed_count += 1
            assert len(courses) > 0
            for c in courses:
                jr = calculate_course_junk_rate(c)
                assert jr <= 0.05, f"Course {c.code} in {pdf_path.name} has junk_rate {jr:.4f} > 0.05"
                assert is_confident_course(c), f"Course {c.code} failed confidence criteria"
        else:
            rejected_count += 1
            assert err in ("low_confidence", "not_a_syllabus")

    assert passed_count > 0, "At least some PDFs must pass"


# ---------------------------------------------------------------------------
# Test 7: API upload route confidence gate integration
# ---------------------------------------------------------------------------

def test_api_upload_route_confidence_gate():
    """
    Verifies that the /pipeline/upload-and-parse route:
     - Returns 200 with document_id and subjects for valid format
     - Returns 422 {"error": "not_a_syllabus"} for calendar text
    """
    # Valid PDF
    valid_pdf = RAW_DIR / "2019-scheme" / "Computer-Engineering" / "be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf"
    with open(valid_pdf, "rb") as f:
        resp = client.post(
            "/api/v1/pipeline/upload-and-parse",
            files={"file": (valid_pdf.name, f.read(), "application/pdf")}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "document_id" in data
    assert "subjects" in data
    assert len(data["subjects"]) >= 5
    codes = {s["course_code"] for s in data["subjects"]}
    assert "CSC303" in codes

    # Calendar text -> 422 not_a_syllabus
    import fitz, io
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((40, 40), "Oct 20, 2026 Tuesday all subjects DIWALI BREAK UNIT TEST 2")
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()

    resp_cal = client.post(
        "/api/v1/pipeline/upload-and-parse",
        files={"file": ("cal.pdf", buf.getvalue(), "application/pdf")}
    )
    assert resp_cal.status_code == 422
    assert resp_cal.json().get("detail", {}).get("error") == "not_a_syllabus"

