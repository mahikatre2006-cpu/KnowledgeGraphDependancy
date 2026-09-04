import pytest
from app.graph.engine import KnowledgeGraph
from app.services.analytics_engine import AnalyticsEngine
from app.graph.exceptions import ConceptNotFoundError
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
# Analytics Engine Unit Tests
# ============================================================================

def test_missing_prerequisites_calculation():
    kg = KnowledgeGraph()
    kg.add_concept("py", "Python")
    kg.add_concept("numpy", "NumPy")
    kg.add_concept("ml", "Machine Learning")
    kg.add_concept("calc", "Calculus")
    kg.add_concept("dl", "Deep Learning")

    kg.add_dependency("py", "numpy")
    kg.add_dependency("numpy", "ml")
    kg.add_dependency("ml", "dl")
    kg.add_dependency("calc", "dl")

    # Target: Deep Learning. Student knows: Python, NumPy
    result = AnalyticsEngine.get_missing_prerequisites(
        graph=kg,
        target_concept_id="dl",
        known_concept_ids=["py", "numpy"]
    )

    assert result.target_concept_id == "dl"
    assert result.total_prerequisites_count == 4  # py, numpy, ml, calc
    assert result.missing_count == 2             # ml, calc
    assert result.progress_percentage == 50.0

    missing_ids = [node.id for node in result.missing_concepts]
    assert "ml" in missing_ids
    assert "calc" in missing_ids
    assert "py" not in missing_ids


def test_bottleneck_analysis():
    kg = KnowledgeGraph()
    kg.add_concept("lin_alg", "Linear Algebra")
    kg.add_concept("reg", "Linear Regression")
    kg.add_concept("pca", "PCA Dimensionality Reduction")
    kg.add_concept("nn", "Neural Networks")
    kg.add_concept("web", "Web Development")  # Isolated node

    # Linear Algebra unlocks Regression, PCA, and Neural Networks
    kg.add_dependency("lin_alg", "reg")
    kg.add_dependency("lin_alg", "pca")
    kg.add_dependency("lin_alg", "nn")

    response = AnalyticsEngine.analyze_bottlenecks(graph=kg, top_n=5)
    assert response.total_concepts == 5
    assert len(response.bottlenecks) > 0

    top_bottleneck = response.bottlenecks[0]
    assert top_bottleneck.concept.id == "lin_alg"
    assert top_bottleneck.downstream_count == 3
    assert top_bottleneck.direct_dependents_count == 3


def test_student_readiness_check():
    kg = KnowledgeGraph()
    kg.add_concept("c1", "Calculus I")
    kg.add_concept("c2", "Calculus II")
    kg.add_concept("diff", "Differential Equations")

    kg.add_dependency("c1", "diff")
    kg.add_dependency("c2", "diff")

    # Case 1: Student knows only Calculus I -> Not ready for Differential Equations
    r1 = AnalyticsEngine.check_readiness(graph=kg, concept_id="diff", known_concept_ids=["c1"])
    assert r1.is_ready is False
    assert len(r1.unmet_prerequisites) == 1
    assert r1.unmet_prerequisites[0].id == "c2"

    # Case 2: Student knows Calculus I & Calculus II -> Ready!
    r2 = AnalyticsEngine.check_readiness(graph=kg, concept_id="diff", known_concept_ids=["c1", "c2"])
    assert r2.is_ready is True
    assert len(r2.unmet_prerequisites) == 0


# ============================================================================
# API Endpoint Integration Tests
# ============================================================================

def test_api_analytics_endpoints():
    # Setup graph via API
    client.post("/api/v1/graph/concepts", json={"id": "python", "name": "Python"})
    client.post("/api/v1/graph/concepts", json={"id": "pandas", "name": "Pandas"})
    client.post("/api/v1/graph/concepts", json={"id": "ml", "name": "Machine Learning"})

    client.post("/api/v1/graph/dependencies", json={"source_id": "python", "target_id": "pandas"})
    client.post("/api/v1/graph/dependencies", json={"source_id": "pandas", "target_id": "ml"})

    # 1. Missing Prerequisites API
    r1 = client.post("/api/v1/analytics/missing-prerequisites", json={
        "target_concept_id": "ml",
        "known_concept_ids": ["python"]
    })
    assert r1.status_code == 200
    assert r1.json()["missing_count"] == 1
    assert r1.json()["missing_concepts"][0]["id"] == "pandas"

    # 2. Bottlenecks API
    r2 = client.get("/api/v1/analytics/bottlenecks?top_n=3")
    assert r2.status_code == 200
    assert r2.json()["total_concepts"] == 3
    assert r2.json()["bottlenecks"][0]["concept"]["id"] == "python"

    # 3. Readiness API
    r3 = client.post("/api/v1/analytics/readiness", json={
        "concept_id": "ml",
        "known_concept_ids": ["python"]
    })
    assert r3.status_code == 200
    assert r3.json()["is_ready"] is False
    assert r3.json()["unmet_prerequisites"][0]["id"] == "pandas"
