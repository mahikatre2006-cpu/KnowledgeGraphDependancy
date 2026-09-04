import io
import fitz  # PyMuPDF
import pytest
from app.parser.pdf_parser import extract_text_from_pdf_bytes
from app.parser.syllabus_extractor import SyllabusExtractor
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def create_sample_pdf_bytes() -> bytes:
    """Helper to create an in-memory PDF file using PyMuPDF for testing."""
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "CS201: Data Structures and Algorithms\n\n"
        "Unit 1: Foundations\n"
        "• Arrays and Linked Lists\n"
        "• Stacks and Queues\n"
        "• Asymptotic Notation (Big O)\n\n"
        "Unit 2: Trees and Graphs\n"
        "• Binary Search Trees\n"
        "• Graph Traversals (DFS, BFS)\n"
        "• Shortest Path Algorithms\n"
    )
    page.insert_text((50, 50), text)
    pdf_buffer = io.BytesIO()
    doc.save(pdf_buffer)
    doc.close()
    return pdf_buffer.getvalue()


# ============================================================================
# PDF Parser Unit Tests
# ============================================================================

def test_extract_text_from_pdf_bytes():
    pdf_bytes = create_sample_pdf_bytes()
    text = extract_text_from_pdf_bytes(pdf_bytes)
    assert "CS201: Data Structures and Algorithms" in text
    assert "Unit 1: Foundations" in text
    assert "Binary Search Trees" in text


def test_invalid_pdf_bytes_raises_error():
    with pytest.raises(ValueError) as exc_info:
        extract_text_from_pdf_bytes(b"invalid corrupt data")
    assert "Failed to open PDF" in str(exc_info.value)


# ============================================================================
# Syllabus Extractor Unit Tests
# ============================================================================

def test_syllabus_extractor_parse():
    sample_text = (
        "CS101: Introduction to Computer Science\n\n"
        "Unit 1: Python Basics\n"
        "• Variables and Data Types\n"
        "• Control Flow (If, Loops)\n\n"
        "Unit 2: Object-Oriented Programming\n"
        "• Classes and Objects\n"
        "• Inheritance and Polymorphism\n"
    )

    parsed = SyllabusExtractor.parse(sample_text)
    assert parsed.course_code == "CS101"
    assert parsed.course_title == "Introduction to Computer Science"
    assert len(parsed.units) == 2
    assert parsed.total_topics_count == 4

    unit1_topics = [t.name for t in parsed.units[0].topics]
    assert "Variables and Data Types" in unit1_topics
    assert "Control Flow (If, Loops)" in unit1_topics

    unit2_topics = [t.name for t in parsed.units[1].topics]
    assert "Classes and Objects" in unit2_topics
    assert "Inheritance and Polymorphism" in unit2_topics


# ============================================================================
# API Endpoint Integration Tests
# ============================================================================

def test_api_parse_text_endpoint():
    response = client.post("/api/v1/syllabus/parse-text", json={
        "text": "Unit 1: Linear Algebra\n• Matrices\n• Vectors\n\nUnit 2: Calculus\n• Derivatives"
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["units"]) == 2
    assert data["total_topics_count"] == 3


def test_api_pdf_upload_endpoint():
    pdf_bytes = create_sample_pdf_bytes()
    files = {"file": ("syllabus.pdf", pdf_bytes, "application/pdf")}
    response = client.post("/api/v1/syllabus/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["course_code"] == "CS201"
    assert len(data["units"]) == 2
    assert data["total_topics_count"] == 6


def test_api_pdf_upload_invalid_filetype():
    files = {"file": ("test.txt", b"plain text", "text/plain")}
    response = client.post("/api/v1/syllabus/upload", files=files)
    assert response.status_code == 400
    assert "Only PDF (.pdf) files are supported" in response.json()["detail"]
