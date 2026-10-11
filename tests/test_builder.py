import io
import fitz
import pytest
from app.graph.engine import KnowledgeGraph
from app.services.graph_builder import GraphBuilder
from app.services.sequence_engine import SequenceEngine
from app.models.parser_schemas import ParsedSyllabus, ParsedUnit, ParsedTopic
from fastapi.testclient import TestClient
from app.main import app
from app.api.graph_router import global_graph

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_graphs():
    global_graph.clear()
    yield
    global_graph.clear()


def create_sample_pdf_bytes() -> bytes:
    """Helper to create an in-memory PDF file for end-to-end pipeline testing."""
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "CS301: Machine Learning Foundations\n\n"
        "Unit 1: Linear Algebra & Vectors\n"
        "• Vector Spaces\n"
        "• Matrix Multiplication\n\n"
        "Unit 2: Optimization\n"
        "• Gradient Descent\n"
        "• Loss Functions\n"
    )
    page.insert_text((50, 50), text)
    pdf_buffer = io.BytesIO()
    doc.save(pdf_buffer)
    doc.close()
    return pdf_buffer.getvalue()


# ============================================================================
# GraphBuilder Unit Tests
# ============================================================================

def test_graph_builder_service():
    kg = KnowledgeGraph()
    syllabus = ParsedSyllabus(
        course_title="Artificial Intelligence",
        course_code="AI101",
        units=[
            ParsedUnit(
                unit_number=1,
                title="Search Algorithms",
                topics=[
                    ParsedTopic(id="bfs", name="Breadth First Search", unit_number=1, unit_title="Search Algorithms"),
                    ParsedTopic(id="dfs", name="Depth First Search", unit_number=1, unit_title="Search Algorithms")
                ]
            )
        ],
        all_topics=[
            ParsedTopic(id="bfs", name="Breadth First Search", unit_number=1, unit_title="Search Algorithms"),
            ParsedTopic(id="dfs", name="Depth First Search", unit_number=1, unit_title="Search Algorithms")
        ],
        total_topics_count=2
    )

    stats = GraphBuilder.build_from_syllabus(syllabus, kg, add_unit_sequential_edges=True)
    assert stats["nodes_added"] == 2
    assert stats["edges_added"] == 1
    assert kg.node_count() == 2
    assert kg.has_concept("bfs") is True
    assert kg.has_concept("dfs") is True
    assert kg.has_dependency("bfs", "dfs") is True


# ============================================================================
# End-to-End Pipeline API Integration Tests
# ============================================================================

def test_api_build_graph_from_syllabus_json():
    payload = {
        "course_title": "Database Systems",
        "course_code": "CS401",
        "units": [
            {
                "unit_number": 1,
                "title": "Relational Model",
                "topics": [
                    {"id": "sql_basics", "name": "SQL Basics", "unit_number": 1, "unit_title": "Relational Model"},
                    {"id": "relational_algebra", "name": "Relational Algebra", "unit_number": 1, "unit_title": "Relational Model"}
                ]
            }
        ],
        "all_topics": [
            {"id": "sql_basics", "name": "SQL Basics", "unit_number": 1, "unit_title": "Relational Model"},
            {"id": "relational_algebra", "name": "Relational Algebra", "unit_number": 1, "unit_title": "Relational Model"}
        ],
        "total_topics_count": 2
    }

    response = client.post("/api/v1/pipeline/build-graph-from-syllabus", json=payload)
    assert response.status_code == 200
    assert response.json()["nodes_added"] == 2

    # Query Graph Summary to verify global_graph populated
    summary = client.get("/api/v1/graph/summary").json()
    assert summary["node_count"] == 2


def test_api_upload_and_build_full_pipeline_end_to_end():
    pdf_bytes = create_sample_pdf_bytes()
    files = {"file": ("syllabus.pdf", pdf_bytes, "application/pdf")}
    
    response = client.post("/api/v1/pipeline/upload-and-build-graph", files=files)
    assert response.status_code == 200
    data = response.json()

    # 1. Verify Parsed Syllabus
    assert data["parsed_syllabus"]["course_code"] == "CS301"
    assert len(data["parsed_syllabus"]["units"]) == 2

    # 2. Verify Graph Summary
    assert data["graph_summary"]["node_count"] == 4
    assert data["graph_summary"]["edge_count"] == 2

    # 3. Verify Topological Sequence
    seq_ids = [node["id"] for node in data["topological_sequence"]]
    assert len(seq_ids) == 4
    assert "vector_spaces" in seq_ids
    assert "gradient_descent" in seq_ids


def test_build_and_infer_end_to_end_ml_integration():
    """
    P1 Integration Test:
    Verifies that uploading and building a graph via `/pipeline/upload-and-parse`
    followed by `/pipeline/build-and-infer` (the actual frontend flow in FileUpload.jsx):
    1. Returns real backend inference results, not demo nodes.
    2. Validates node IDs and edge endpoints match existing nodes.
    3. Validates no self-loops and strict DAG acyclicity.
    4. Topological sequence covers all extracted topics.
    """
    pdf_bytes = create_sample_pdf_bytes()
    files = {"file": ("syllabus.pdf", pdf_bytes, "application/pdf")}
    parse_resp = client.post("/api/v1/pipeline/upload-and-parse", files=files)
    assert parse_resp.status_code == 200
    parse_data = parse_resp.json()
    doc_id = parse_data["document_id"]
    course_code = parse_data["subjects"][0]["course_code"]

    build_resp = client.post("/api/v1/pipeline/build-and-infer", json={
        "document_id": doc_id,
        "course_code": course_code,
        "clear_existing": True,
        "add_unit_sequential_edges": False
    })
    assert build_resp.status_code == 200
    build_data = build_resp.json()

    nodes = build_data["graph_summary"]["nodes"]
    edges = build_data["graph_summary"]["edges"]
    node_ids = {n["id"] for n in nodes}

    assert len(nodes) == 4
    # All edge endpoints must belong to valid nodes in the graph
    for edge in edges:
        assert edge["source_id"] in node_ids, f"Edge source '{edge['source_id']}' not in nodes!"
        assert edge["target_id"] in node_ids, f"Edge target '{edge['target_id']}' not in nodes!"
        assert edge["source_id"] != edge["target_id"], "Self-loop edge detected!"
        assert edge["relationship_type"] == "inferred_prerequisite"

    # Verify strict acyclicity
    assert SequenceEngine.find_cycle(global_graph) is None

    # Verify topological sequence contains all nodes
    seq_ids = [n["id"] for n in build_data["topological_sequence"]]
    assert len(seq_ids) == len(node_ids)
    assert set(seq_ids) == node_ids

