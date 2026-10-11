"""
tests/test_nep_syllabus.py
==========================
Phase 4 — NEP 2026 Syllabus Parser Tests (fix/nep-parser)

Uses tests/fixtures/nep_sem5_6.pdf
"""
import os
import time
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "nep_sem5_6.pdf"

# ── Ensure fixture exists before any test runs ────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def ensure_fixture():
    if not FIXTURE_PATH.exists():
        import subprocess, sys
        subprocess.run(
            [sys.executable, str(Path(__file__).parent / "create_fixture_pdf.py")],
            check=True
        )
    assert FIXTURE_PATH.exists(), f"Fixture not found: {FIXTURE_PATH}"


# ── Test 1: Calendar text -> 422 not_a_syllabus ───────────────────────────────

def test_is_not_syllabus_gate():
    """Calendar/schedule text must fail the is_syllabus gate."""
    from app.parser.nep_syllabus_parser import is_syllabus

    calendar = (
        "Oct 20, 2026 Tuesday all subjects DIWALI BREAK "
        "Nov 2–7 Mod. 1–3 SEAP carried from original plan UNIT TEST 2"
    )
    assert not is_syllabus(calendar), "Calendar text must not pass the syllabus gate"


def test_is_not_syllabus_via_api():
    """Upload calendar PDF -> HTTP 422 with detail.error == 'not_a_syllabus'."""
    import fitz, io
    from app.main import app

    # Create a small in-memory PDF with calendar text only
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((40, 40), (
        "Oct 20, 2026 Tuesday all subjects DIWALI BREAK "
        "Nov 2-7 Mod. 1-3 SEAP carried from original plan UNIT TEST 2"
    ))
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()

    client = TestClient(app)
    files = {"file": ("calendar.pdf", buf.getvalue(), "application/pdf")}
    resp = client.post("/api/v1/pipeline/upload-and-parse", files=files)
    assert resp.status_code == 422
    detail = resp.json().get("detail", {})
    if isinstance(detail, dict):
        assert detail.get("error") == "not_a_syllabus"
    else:
        assert "not_a_syllabus" in str(detail)


# ── Test 2: Golden topic assertions ──────────────────────────────────────────

@pytest.fixture(scope="module")
def parsed_courses():
    """Parse the fixture PDF once and return courses keyed by code."""
    from app.parser.nep_syllabus_parser import parse_nep_pdf_bytes
    with open(FIXTURE_PATH, "rb") as f:
        data = f.read()
    gate_ok, courses, _ = parse_nep_pdf_bytes(data)
    assert gate_ok, "Fixture PDF must pass syllabus gate"
    return {c.code: c for c in courses}


def test_segmentation_counts(parsed_courses):
    """Must segment at least 3 courses; all golden codes present."""
    assert len(parsed_courses) >= 3
    for code in ("2345113", "2345111", "2345112"):
        assert code in parsed_courses, f"Missing course {code}"


def _topic_names(course):
    return [t["name"].lower() for t in course.topics]


def _assert_zero_self_learning(course):
    names = _topic_names(course)
    for name in names:
        assert "self-learning" not in name, f"SL leakage: {name}"
        assert "self learning" not in name, f"SL leakage: {name}"
        assert "explore online" not in name, f"SL content leakage: {name}"
        assert "nptel" not in name, f"SL content leakage: {name}"


# ── 2345113 Web Technology ────────────────────────────────────────────────────

def test_web_technology_modules(parsed_courses):
    c = parsed_courses["2345113"]
    assert len(c.modules) == 6, f"Expected 6 modules, got {len(c.modules)}"


def test_web_technology_topic_count(parsed_courses):
    c = parsed_courses["2345113"]
    n = len(c.topics)
    assert 35 <= n <= 70, f"Expected 35-70 topics, got {n}"


def test_web_technology_module_min_topics(parsed_courses):
    c = parsed_courses["2345113"]
    for mod in c.modules:
        assert len(mod["topics"]) >= 4, (
            f"Module {mod['idx']} has only {len(mod['topics'])} topics"
        )


def test_web_technology_must_contain(parsed_courses):
    c = parsed_courses["2345113"]
    names = _topic_names(c)
    must_have = [
        "arrow functions", "state and props", "hooks", "crud operations",
        "event loops", "express router", "rest api", "model-view",
    ]
    missing = [t for t in must_have if not any(t in n for n in names)]
    assert not missing, f"Missing required topics: {missing}"


def test_web_technology_must_not_contain(parsed_courses):
    c = parsed_courses["2345113"]
    names = _topic_names(c)
    must_not = [
        "asynchronous javascript", "react vs angular", "next.js framework",
        "fastapi", "react native", "query optimization",
        "environment setup", "first app", "installation",
    ]
    found = [t for t in must_not if any(t in n for n in names)]
    assert not found, f"Banned topics found: {found}"


def test_web_technology_no_self_learning(parsed_courses):
    _assert_zero_self_learning(parsed_courses["2345113"])


# ── 2345111 Software Engineering ─────────────────────────────────────────────

def test_se_modules(parsed_courses):
    c = parsed_courses["2345111"]
    assert len(c.modules) == 6


def test_se_must_contain(parsed_courses):
    c = parsed_courses["2345111"]
    names = _topic_names(c)
    must_have = ["waterfall", "cocomo", "rmmm", "scrum", "kanban", "regression"]
    missing = [t for t in must_have if not any(t in n for n in names)]
    assert not missing, f"Missing: {missing}"


def test_se_must_not_contain(parsed_courses):
    c = parsed_courses["2345111"]
    names = _topic_names(c)
    must_not = ["kano", "personal and team", "crystal", "scaled agile"]
    found = [t for t in must_not if any(t in n for n in names)]
    assert not found, f"Banned topics: {found}"


def test_se_no_self_learning(parsed_courses):
    _assert_zero_self_learning(parsed_courses["2345111"])


# ── 2345112 AI and ML ─────────────────────────────────────────────────────────

def test_ml_modules(parsed_courses):
    c = parsed_courses["2345112"]
    assert len(c.modules) == 6


def test_ml_must_contain(parsed_courses):
    c = parsed_courses["2345112"]
    names = _topic_names(c)
    must_have = [
        "breadth first search", "a* algorithm", "linear regression",
        "k-means", "confusion matrix", "roc curve",
    ]
    missing = [t for t in must_have if not any(t in n for n in names)]
    assert not missing, f"Missing: {missing}"


def test_ml_must_not_contain(parsed_courses):
    c = parsed_courses["2345112"]
    names = _topic_names(c)
    must_not = ["dbscan", "smote", "automl"]
    found = [t for t in must_not if any(t in n for n in names)]
    assert not found, f"Banned topics: {found}"


def test_ml_no_self_learning(parsed_courses):
    _assert_zero_self_learning(parsed_courses["2345112"])


# ── Test 3: Graph endpoint checks (real endpoint) ────────────────────────────

@pytest.fixture(scope="module")
def client():
    from app.main import app
    return TestClient(app)


def _upload_and_build(client, fixture_path: Path, course_code: str):
    with open(fixture_path, "rb") as f:
        pdf_bytes = f.read()

    files = {"file": ("nep_sem5_6.pdf", pdf_bytes, "application/pdf")}
    t0 = time.perf_counter()
    resp = client.post("/api/v1/pipeline/upload-and-parse", files=files)
    assert resp.status_code == 200, f"upload-and-parse failed: {resp.text}"
    doc_id = resp.json()["document_id"]

    resp2 = client.post(
        "/api/v1/pipeline/build-and-infer",
        json={"document_id": doc_id, "course_code": course_code},
    )
    wall = time.perf_counter() - t0
    return resp2, wall


@pytest.mark.parametrize("course_code", ["2345113", "2345111", "2345112"])
def test_graph_endpoint_properties(client, course_code):
    resp, wall = _upload_and_build(client, FIXTURE_PATH, course_code)
    assert resp.status_code == 200, f"build-and-infer failed for {course_code}: {resp.text}"
    data = resp.json()
    graph = data["graph_summary"]

    print(f"\n[{course_code}] wall={wall:.2f}s  nodes={graph['node_count']}  edges={graph['edge_count']}")

    # Must have edges
    assert graph["edge_count"] > 0, f"No edges produced for {course_code}"

    # All endpoint IDs must exist as nodes
    node_ids = {str(n["id"]) for n in graph["nodes"]}
    for edge in graph["edges"]:
        src = str(edge["source_id"])
        tgt = str(edge["target_id"])
        assert src in node_ids, f"Edge source '{src}' not in nodes"
        assert tgt in node_ids, f"Edge target '{tgt}' not in nodes"

    # DAG check: build adjacency and verify no cycle
    adj = {}
    for n in graph["nodes"]:
        adj[str(n["id"])] = []
    for edge in graph["edges"]:
        adj[str(edge["source_id"])].append(str(edge["target_id"]))

    assert not _has_cycle(adj), f"Graph for {course_code} contains a cycle"

    # Degree constraints
    in_deg = {nid: 0 for nid in node_ids}
    out_deg = {nid: 0 for nid in node_ids}
    for edge in graph["edges"]:
        out_deg[str(edge["source_id"])] += 1
        in_deg[str(edge["target_id"])] += 1

    max_out = max(out_deg.values(), default=0)
    max_in = max(in_deg.values(), default=0)
    print(f"[{course_code}] max_out={max_out}  max_in={max_in}")
    assert max_out <= 6, f"Max out-degree {max_out} exceeds 6 for {course_code}"
    assert max_in <= 3, f"Max in-degree {max_in} exceeds 3 for {course_code}"


def _has_cycle(adj: dict) -> bool:
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in adj}

    def dfs(u):
        color[u] = GRAY
        for v in adj.get(u, []):
            if color[v] == GRAY:
                return True
            if color[v] == WHITE and dfs(v):
                return True
        color[u] = BLACK
        return False

    return any(dfs(u) for u in adj if color[u] == WHITE)


# ── Test 4: Offline test (no API key) ────────────────────────────────────────

def test_offline_no_api_key(monkeypatch, parsed_courses):
    """Prediction must work with GEMINI_API_KEY unset."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    # Re-import and verify classifier still works
    from app.services.classifier_inference_service import ClassifierInferenceService
    features = {
        "embedding_similarity": 0.75,
        "keyword_overlap": 0.3,
        "order_delta": 2,
    }
    prob = ClassifierInferenceService.predict_edge_probability(features)
    assert 0.0 <= prob <= 1.0, f"Invalid probability: {prob}"

