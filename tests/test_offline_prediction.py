"""
test_offline_prediction.py
==========================
Acceptance Test AC-0: Offline Prediction & Deterministic Path
Verifies that the entire prediction pipeline:
  Syllabus PDF / Text -> SyllabusExtractor -> GraphBuilder -> RelationshipInferencer -> SequenceEngine
runs 100% offline with GEMINI_API_KEY unset and zero network/API dependencies.
"""

import os
import io
import fitz
import pytest
from app.graph.engine import KnowledgeGraph
from app.parser.syllabus_extractor import SyllabusExtractor
from app.parser.pdf_parser import extract_text_from_pdf_bytes
from app.services.graph_builder import GraphBuilder
from app.services.relationship_inferencer import RelationshipInferencer
from app.services.sequence_engine import SequenceEngine


def test_offline_prediction_ac0(monkeypatch):
    # Enforce offline doctrine: GEMINI_API_KEY must be empty
    monkeypatch.setenv("GEMINI_API_KEY", "")
    assert os.environ.get("GEMINI_API_KEY") == ""

    # Create in-memory PDF
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "CSC303: Data Structures\n\n"
        "Unit 1: Linear Data Structures\n"
        "• Arrays and Dynamic Arrays\n"
        "• Linked Lists\n"
        "• Stacks and Queues\n\n"
        "Unit 2: Non-Linear Data Structures\n"
        "• Binary Trees and Tree Traversals\n"
        "• Binary Search Trees\n"
        "• Graph Representations and Traversals\n"
    )
    page.insert_text((50, 50), text)
    pdf_buffer = io.BytesIO()
    doc.save(pdf_buffer)
    doc.close()
    pdf_bytes = pdf_buffer.getvalue()

    # Step 1: Offline Text Extraction
    extracted_text = extract_text_from_pdf_bytes(pdf_bytes)
    assert "CSC303" in extracted_text

    # Step 2: Deterministic Syllabus Extraction
    parsed = SyllabusExtractor.parse(extracted_text)
    assert parsed.course_code == "CSC303"
    assert parsed.total_topics_count == 6

    # Step 3: Graph Construction
    kg = KnowledgeGraph()
    GraphBuilder.build_from_syllabus(parsed, kg, clear_existing=True, add_unit_sequential_edges=False)
    assert kg.node_count() == 6
    assert kg.edge_count() == 0  # No sequential edges added

    # Step 4: 100% Local ML Prerequisite Inference (SentenceTransformers + XGBoost v4)
    inferred_edges = RelationshipInferencer.infer_prerequisites(
        graph=kg,
        auto_add_to_graph=True
    )

    # Acceptance Criteria AC-0 checks:
    # 1. Must return >= 1 inferred prerequisite edge
    assert len(inferred_edges) >= 1
    assert kg.edge_count() >= 1

    # 2. Every edge must connect existing nodes
    node_ids = {n.id for n in kg.get_all_nodes()}
    for edge in inferred_edges:
        assert edge.source_id in node_ids
        assert edge.target_id in node_ids
        assert edge.source_id != edge.target_id
        assert edge.relationship_type == "inferred_prerequisite"
        assert edge.tier in ("strong", "weak")

    # 3. Graph must be an acyclic DAG
    cycle = SequenceEngine.find_cycle(kg)
    assert cycle is None, f"Cycle detected in inferred graph: {cycle}"

    # 4. Topological sequence must resolve all nodes
    seq = SequenceEngine.get_topological_sequence(kg)
    assert len(seq) == 6

