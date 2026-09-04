import pytest
from app.graph.engine import KnowledgeGraph
from app.graph.exceptions import (
    ConceptNotFoundError,
    DuplicateConceptError,
    SelfLoopError,
    InvalidDependencyError
)
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
# Engine Unit Tests
# ============================================================================

def test_add_and_get_concept():
    kg = KnowledgeGraph()
    node = kg.add_concept(id="calc1", name="Calculus I", unit="Unit 1")
    assert node.id == "calc1"
    assert node.name == "Calculus I"
    assert kg.has_concept("calc1") is True
    assert kg.node_count() == 1

    fetched = kg.get_concept("calc1")
    assert fetched == node


def test_duplicate_concept_error():
    kg = KnowledgeGraph()
    kg.add_concept(id="calc1", name="Calculus I")
    with pytest.raises(DuplicateConceptError):
        kg.add_concept(id="calc1", name="Calculus I Repeat")


def test_add_dependency_and_query_prereqs_dependents():
    kg = KnowledgeGraph()
    kg.add_concept(id="prob", name="Probability")
    kg.add_concept(id="stat", name="Statistics")
    kg.add_concept(id="ml", name="Machine Learning")

    # Probability -> Statistics -> Machine Learning
    edge1 = kg.add_dependency(source_id="prob", target_id="stat")
    edge2 = kg.add_dependency(source_id="stat", target_id="ml")

    assert edge1.source_id == "prob"
    assert edge1.target_id == "stat"
    assert kg.edge_count() == 2

    # Verify Statistics prerequisites: [Probability]
    prereqs_stat = kg.get_prerequisites("stat")
    assert len(prereqs_stat) == 1
    assert prereqs_stat[0].id == "prob"

    # Verify Statistics dependents: [Machine Learning]
    dependents_stat = kg.get_dependents("stat")
    assert len(dependents_stat) == 1
    assert dependents_stat[0].id == "ml"

    # In-degree / Out-degree
    assert kg.get_in_degree("ml") == 1
    assert kg.get_out_degree("prob") == 1
    assert kg.get_in_degree("prob") == 0


def test_self_loop_error():
    kg = KnowledgeGraph()
    kg.add_concept(id="algo", name="Algorithms")
    with pytest.raises(SelfLoopError):
        kg.add_dependency(source_id="algo", target_id="algo")


def test_missing_concept_errors():
    kg = KnowledgeGraph()
    kg.add_concept(id="c1", name="Concept 1")

    with pytest.raises(ConceptNotFoundError):
        kg.add_dependency(source_id="c1", target_id="non_existent")

    with pytest.raises(ConceptNotFoundError):
        kg.get_prerequisites("non_existent")


def test_remove_concept_cleans_edges():
    kg = KnowledgeGraph()
    kg.add_concept(id="a", name="Topic A")
    kg.add_concept(id="b", name="Topic B")
    kg.add_concept(id="c", name="Topic C")

    kg.add_dependency("a", "b")  # A -> B
    kg.add_dependency("b", "c")  # B -> C

    assert kg.edge_count() == 2

    # Remove node B (middle node)
    kg.remove_concept("b")

    assert kg.node_count() == 2
    assert kg.edge_count() == 0
    assert kg.has_concept("b") is False
    assert len(kg.get_dependents("a")) == 0
    assert len(kg.get_prerequisites("c")) == 0


def test_serialization():
    kg = KnowledgeGraph()
    kg.add_concept(id="python", name="Python")
    kg.add_concept(id="ds", name="Data Structures")
    kg.add_dependency("python", "ds", reason="Python fundamentals needed")

    serialized = kg.to_dict()
    assert len(serialized["nodes"]) == 2
    assert len(serialized["edges"]) == 1

    deserialized_kg = KnowledgeGraph.from_dict(serialized)
    assert deserialized_kg.node_count() == 2
    assert deserialized_kg.edge_count() == 1
    assert deserialized_kg.has_dependency("python", "ds") is True


# ============================================================================
# API Endpoint Integration Tests
# ============================================================================

def test_api_graph_crud():
    # 1. Add Concept 1
    r1 = client.post("/api/v1/graph/concepts", json={
        "id": "linear_algebra",
        "name": "Linear Algebra",
        "unit": "Unit 1"
    })
    assert r1.status_code == 201
    assert r1.json()["id"] == "linear_algebra"

    # 2. Add Concept 2
    r2 = client.post("/api/v1/graph/concepts", json={
        "id": "deep_learning",
        "name": "Deep Learning",
        "unit": "Unit 4"
    })
    assert r2.status_code == 201

    # 3. Add Dependency
    r3 = client.post("/api/v1/graph/dependencies", json={
        "source_id": "linear_algebra",
        "target_id": "deep_learning",
        "reason": "Linear Algebra is foundational for matrices in Deep Learning"
    })
    assert r3.status_code == 201

    # 4. Query Prerequisites API
    r4 = client.get("/api/v1/graph/concepts/deep_learning/prerequisites")
    assert r4.status_code == 200
    assert len(r4.json()) == 1
    assert r4.json()[0]["id"] == "linear_algebra"

    # 5. Query Summary API
    r5 = client.get("/api/v1/graph/summary")
    assert r5.status_code == 200
    assert r5.json()["node_count"] == 2
    assert r5.json()["edge_count"] == 1
