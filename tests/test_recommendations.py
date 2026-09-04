import pytest
from app.graph.engine import KnowledgeGraph
from app.services.recommendation_engine import RecommendationEngine
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
# Recommendation Engine Unit Tests
# ============================================================================

def test_recommendation_scoring_and_prioritization():
    kg = KnowledgeGraph()
    kg.add_concept("py", "Python", unit="Unit 1")
    kg.add_concept("numpy", "NumPy", unit="Unit 2")
    kg.add_concept("lin_alg", "Linear Algebra", unit="Unit 1")
    kg.add_concept("ml", "Machine Learning", unit="Unit 3")

    kg.add_dependency("py", "numpy")
    kg.add_dependency("numpy", "ml")
    kg.add_dependency("lin_alg", "ml")

    # Student knows: Python
    res = RecommendationEngine.generate_recommendations(
        graph=kg,
        known_concept_ids=["py"],
        max_recommendations=5
    )

    assert res.student_mastery_percentage == 25.0  # 1/4 topics mastered
    assert res.known_concepts_count == 1
    assert res.ready_now_count == 2  # numpy (ready!), lin_alg (ready!)

    now_ids = [item.concept.id for item in res.recommended_path]
    assert "numpy" in now_ids
    assert "lin_alg" in now_ids
    assert "ml" not in now_ids  # ML is blocked by unmet prereqs!

    # Check reason strings are non-jargon
    numpy_rec = next(item for item in res.recommended_path if item.concept.id == "numpy")
    assert "100% ready" in numpy_rec.recommendation_reason


def test_target_goal_priority_boost():
    kg = KnowledgeGraph()
    kg.add_concept("calc", "Calculus", unit="Unit 1")
    kg.add_concept("web", "HTML Basics", unit="Unit 1")
    kg.add_concept("diff_eq", "Differential Equations", unit="Unit 2")

    kg.add_dependency("calc", "diff_eq")

    # Student targets: Differential Equations
    res = RecommendationEngine.generate_recommendations(
        graph=kg,
        known_concept_ids=[],
        target_concept_id="diff_eq",
        max_recommendations=2
    )

    # Calculus must be ranked #1 above HTML Basics because Calculus is a prerequisite for target goal!
    assert res.recommended_path[0].concept.id == "calc"
    assert "target goal" in res.recommended_path[0].recommendation_reason.lower()


# ============================================================================
# API Endpoint Integration Tests
# ============================================================================

def test_api_recommendation_endpoints():
    # Setup graph via API
    client.post("/api/v1/graph/concepts", json={"id": "python", "name": "Python", "unit": "Unit 1"})
    client.post("/api/v1/graph/concepts", json={"id": "ds", "name": "Data Structures", "unit": "Unit 2"})
    client.post("/api/v1/graph/dependencies", json={"source_id": "python", "target_id": "ds"})

    # 1. Generate Recommendations API
    r1 = client.post("/api/v1/recommendations/generate", json={
        "known_concept_ids": ["python"],
        "max_recommendations": 3
    })
    assert r1.status_code == 200
    data = r1.json()
    assert data["student_mastery_percentage"] == 50.0
    assert len(data["recommended_path"]) == 1
    assert data["recommended_path"][0]["concept"]["id"] == "ds"

    # 2. Next Single Topic API
    r2 = client.post("/api/v1/recommendations/next-topic", json={
        "known_concept_ids": ["python"]
    })
    assert r2.status_code == 200
    assert r2.json()["concept"]["id"] == "ds"
    assert r2.json()["status"] == "NOW"
