import pytest
import numpy as np
from app.graph.engine import KnowledgeGraph
from app.services.embedding_service import LocalEmbeddingService
from app.services.relationship_inferencer import RelationshipInferencer
from fastapi.testclient import TestClient
from app.main import app
from app.api.graph_router import global_graph

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_graphs():
    global_graph.clear()
    yield
    global_graph.clear()


# ============================================================================
# Local Embedding Service Tests
# ============================================================================

def test_local_embedding_service_shape():
    vector = LocalEmbeddingService.encode_text("Linear Algebra & Vectors")
    assert isinstance(vector, np.ndarray)
    assert vector.shape == (384,)

    batch_vectors = LocalEmbeddingService.encode_batch(["Vector Spaces", "Matrix Calculus", "Python Programming"])
    assert batch_vectors.shape == (3, 384)


def test_semantic_cosine_similarity():
    v1 = LocalEmbeddingService.encode_text("Linear Algebra and Matrices")
    v2 = LocalEmbeddingService.encode_text("Matrix Multiplication and Vector Spaces")
    v3 = LocalEmbeddingService.encode_text("History of Renaissance Art")

    sim_related = LocalEmbeddingService.compute_cosine_similarity(v1, v2)
    sim_unrelated = LocalEmbeddingService.compute_cosine_similarity(v1, v3)

    assert sim_related > 0.45
    assert sim_unrelated < sim_related


# ============================================================================
# Relationship Inferencer Unit Tests
# ============================================================================

def test_relationship_inferencer():
    kg = KnowledgeGraph()
    kg.add_concept("linear_algebra", "Linear Algebra and Matrices", unit="Unit 1: Foundations")
    kg.add_concept("deep_learning", "Deep Neural Networks", unit="Unit 3: Advanced ML")

    inferred_edges = RelationshipInferencer.infer_prerequisites(
        graph=kg,
        similarity_threshold=0.25,
        min_confidence=0.45,
        auto_add_to_graph=True
    )

    assert len(inferred_edges) >= 1
    edge = inferred_edges[0]
    assert edge.source_id == "linear_algebra"
    assert edge.target_id == "deep_learning"
    assert edge.confidence >= 0.45
    assert "SentenceTransformer" in edge.reason
    assert kg.has_dependency("linear_algebra", "deep_learning") is True


# ============================================================================
# API Endpoint Integration Tests
# ============================================================================

def test_api_infer_relationships():
    # Setup concepts via API
    client.post("/api/v1/graph/concepts", json={
        "id": "py_basics",
        "name": "Python Programming Fundamentals",
        "unit": "Unit 1"
    })
    client.post("/api/v1/graph/concepts", json={
        "id": "pandas_data",
        "name": "Data Wrangling with Pandas",
        "unit": "Unit 2"
    })

    response = client.post("/api/v1/graph/infer-relationships", json={
        "similarity_threshold": 0.25,
        "min_confidence": 0.45,
        "auto_add_to_graph": True
    })

    assert response.status_code == 200
    data = response.json()
    assert data["inferred_edges_count"] >= 1
    assert data["inferred_edges"][0]["source_id"] == "py_basics"
    assert data["inferred_edges"][0]["target_id"] == "pandas_data"
