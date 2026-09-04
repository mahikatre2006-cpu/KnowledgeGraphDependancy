import pytest
from app.graph.engine import KnowledgeGraph
from app.services.sequence_engine import SequenceEngine
from app.graph.exceptions import CycleDetectedError, ConceptNotFoundError
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
# SequenceEngine Unit Tests
# ============================================================================

def test_topological_sort_linear_chain():
    kg = KnowledgeGraph()
    kg.add_concept("c1", "Calculus I")
    kg.add_concept("c2", "Calculus II")
    kg.add_concept("diff_eq", "Differential Equations")

    kg.add_dependency("c1", "c2")       # C1 -> C2
    kg.add_dependency("c2", "diff_eq")  # C2 -> DiffEq

    sequence = SequenceEngine.get_topological_sequence(kg)
    ids = [node.id for node in sequence]
    assert ids == ["c1", "c2", "diff_eq"]


def test_topological_sort_complex_dag():
    kg = KnowledgeGraph()
    # Nodes: py, math, numpy, stats, ml, dl
    for cid, name in [
        ("py", "Python"),
        ("math", "Linear Algebra"),
        ("numpy", "NumPy"),
        ("stats", "Statistics"),
        ("ml", "Machine Learning"),
        ("dl", "Deep Learning")
    ]:
        kg.add_concept(cid, name)

    # Edges:
    # py -> numpy
    # math -> numpy
    # numpy -> ml
    # stats -> ml
    # ml -> dl
    kg.add_dependency("py", "numpy")
    kg.add_dependency("math", "numpy")
    kg.add_dependency("numpy", "ml")
    kg.add_dependency("stats", "ml")
    kg.add_dependency("ml", "dl")

    sequence = SequenceEngine.get_topological_sequence(kg)
    ids = [node.id for node in sequence]

    # Verify order constraint: For every edge A -> B, index(A) < index(B)
    for edge in kg.get_all_edges():
        src_idx = ids.index(edge.source_id)
        tgt_idx = ids.index(edge.target_id)
        assert src_idx < tgt_idx, f"Prerequisite {edge.source_id} must appear before {edge.target_id}"


def test_cycle_detection():
    kg = KnowledgeGraph()
    kg.add_concept("a", "Topic A")
    kg.add_concept("b", "Topic B")
    kg.add_concept("c", "Topic C")

    # A -> B -> C -> A (Cycle!)
    kg.add_dependency("a", "b")
    kg.add_dependency("b", "c")
    kg.add_dependency("c", "a")

    cycle = SequenceEngine.find_cycle(kg)
    assert cycle is not None
    assert cycle[0] == cycle[-1]  # Start and end at same node to complete loop

    with pytest.raises(CycleDetectedError) as exc_info:
        SequenceEngine.get_topological_sequence(kg)
    assert "Circular dependency cycle detected" in str(exc_info.value)


def test_prerequisite_chain_resolution():
    kg = KnowledgeGraph()
    kg.add_concept("py", "Python")
    kg.add_concept("math", "Linear Algebra")
    kg.add_concept("ml", "Machine Learning")
    kg.add_concept("web", "Web Design")  # Unrelated topic!

    kg.add_dependency("py", "ml")
    kg.add_dependency("math", "ml")

    chain = SequenceEngine.get_prerequisite_chain(kg, "ml")
    chain_ids = [node.id for node in chain]

    assert "ml" in chain_ids
    assert "py" in chain_ids
    assert "math" in chain_ids
    assert "web" not in chain_ids  # Unrelated topic should NOT be in chain!
    assert chain_ids[-1] == "ml"   # Target node is last


# ============================================================================
# API Endpoint Integration Tests
# ============================================================================

def test_api_sequence_endpoints():
    # Setup graph via API
    client.post("/api/v1/graph/concepts", json={"id": "py", "name": "Python"})
    client.post("/api/v1/graph/concepts", json={"id": "ds", "name": "Data Structures"})
    client.post("/api/v1/graph/dependencies", json={"source_id": "py", "target_id": "ds"})

    # 1. Cycle Check API (Should be False)
    r1 = client.get("/api/v1/sequence/cycle-check")
    assert r1.status_code == 200
    assert r1.json()["has_cycle"] is False

    # 2. Topological Sort API
    r2 = client.get("/api/v1/sequence/topological")
    assert r2.status_code == 200
    seq_ids = [node["id"] for node in r2.json()["sequence"]]
    assert seq_ids == ["py", "ds"]

    # 3. Prerequisite Chain API
    r3 = client.get("/api/v1/sequence/prerequisite-chain/ds")
    assert r3.status_code == 200
    chain_ids = [node["id"] for node in r3.json()["chain"]]
    assert chain_ids == ["py", "ds"]


def test_api_cycle_detection_error_response():
    client.post("/api/v1/graph/concepts", json={"id": "t1", "name": "Topic 1"})
    client.post("/api/v1/graph/concepts", json={"id": "t2", "name": "Topic 2"})
    client.post("/api/v1/graph/dependencies", json={"source_id": "t1", "target_id": "t2"})
    client.post("/api/v1/graph/dependencies", json={"source_id": "t2", "target_id": "t1"})  # Cycle!

    r = client.get("/api/v1/sequence/topological")
    assert r.status_code == 400
    assert "CycleDetected" in r.json()["detail"]["error"]
