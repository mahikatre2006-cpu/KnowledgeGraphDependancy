"""
gemini_pipeline.py
==================
Turns Gemini's clean topic list into the final teacher-facing result:
graph (nodes + prerequisite edges), study flow, bottlenecks, missing prerequisites.

Edges come from the trained XGBoost classifier, scored in ONE batch
(embeddings are computed once, not once per pair).
Self-contained and stateless: it never touches the app's global graph.
Delete together with gemini_service.py / gemini_router.py / gemini_app.py to remove.
"""

import re
from typing import Any, Dict, List, Tuple

import numpy as np

from app.graph.engine import KnowledgeGraph
from app.ml.features_v5 import compute_keyword_overlap, pair_features
from app.services.analytics_engine import AnalyticsEngine
from app.services.classifier_inference_service import ClassifierInferenceService
from app.services.embedding_service import LocalEmbeddingService
from app.services.sequence_engine import SequenceEngine

MAX_PREREQS_PER_TOPIC = 3   # keep the diagram readable
MIN_FALLBACK_PROB = 0.05    # connect otherwise-isolated topics to their best predecessor


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _threshold() -> float:
    """Decision threshold stored with the loaded model (so it always matches the model)."""
    return ClassifierInferenceService.get_threshold()


def _clean_topics(raw_topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Dedupes topics and orders them by (unit, original position)."""
    seen, topics = set(), []
    for pos, t in enumerate(raw_topics):
        name = str(t.get("name", "")).strip()
        slug = _slug(name)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        topics.append({
            "id": slug,
            "name": name,
            "unit_number": int(t.get("unit_number") or 1),
            "unit_title": str(t.get("unit_title", "")).strip(),
            "pos": pos,
        })
    topics.sort(key=lambda t: (t["unit_number"], t["pos"]))
    return topics


def _predict_edges(topics: List[Dict[str, Any]]) -> List[Tuple[int, int, float]]:
    """
    Scores every forward pair (i < j in syllabus order) with one batched model call.

    Uses the same feature recipe as training and as the app's own inferencer
    (app.ml.features_v5.pair_features), with name-only embeddings computed once.
    """
    n = len(topics)
    if n < 2:
        return []

    names = [t["name"] for t in topics]
    units = [t["unit_number"] for t in topics]
    emb = LocalEmbeddingService.encode_batch(names)
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]

    model = ClassifierInferenceService.get_model()
    if ClassifierInferenceService.get_model_version() == "v5":
        rows = [
            pair_features(a=names[i], b=names[j], n_topics=n, unit_a=units[i], unit_b=units[j],
                          pos_a=i, pos_b=j, emb_a=emb[i], emb_b=emb[j])
            for i, j in pairs
        ]
    else:
        # Older 3-feature model: [embedding_similarity, keyword_overlap, order_delta]
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        unit_emb = emb / norms
        rows = [
            [float(unit_emb[i] @ unit_emb[j]), compute_keyword_overlap(names[i], names[j]), float(j - i)]
            for i, j in pairs
        ]

    probs = model.predict_proba(np.array(rows, dtype=np.float32))[:, 1]
    return [(i, j, float(p)) for (i, j), p in zip(pairs, probs)]


def _select_edges(topics: List[Dict[str, Any]], scored: List[Tuple[int, int, float]]) -> List[Tuple[int, int, float]]:
    """Threshold, cap incoming edges per topic, then drop redundant (transitive) edges."""
    threshold = _threshold()
    incoming: Dict[int, List[Tuple[int, float]]] = {}
    for i, j, p in scored:
        incoming.setdefault(j, []).append((i, p))

    kept: Dict[Tuple[int, int], float] = {}
    for j in range(1, len(topics)):
        candidates = sorted(incoming.get(j, []), key=lambda x: -x[1])
        chosen = [(i, p) for i, p in candidates if p >= threshold][:MAX_PREREQS_PER_TOPIC]
        if not chosen and candidates and candidates[0][1] >= MIN_FALLBACK_PROB:
            chosen = [candidates[0]]
        for i, p in chosen:
            kept[(i, j)] = p

    # Transitive reduction: drop u->v if v is still reachable from u through other kept edges.
    out: Dict[int, List[int]] = {}
    for (i, j) in kept:
        out.setdefault(i, []).append(j)

    def reachable(start: int, goal: int, skip: Tuple[int, int]) -> bool:
        stack, seen = [start], {start}
        while stack:
            cur = stack.pop()
            for nxt in out.get(cur, []):
                if (cur, nxt) == skip or nxt in seen:
                    continue
                if nxt == goal:
                    return True
                seen.add(nxt)
                stack.append(nxt)
        return False

    final = [(i, j, p) for (i, j), p in kept.items() if not reachable(i, j, (i, j))]
    return sorted(final)


def _match_topic_ids(names: List[str], topics: List[Dict[str, Any]]) -> List[str]:
    by_slug = {t["id"]: t["id"] for t in topics}
    ids = []
    for name in names:
        slug = _slug(name)
        if slug in by_slug:
            ids.append(slug)
            continue
        hit = next((t["id"] for t in topics if slug and (slug in t["id"] or t["id"] in slug)), None)
        if hit:
            ids.append(hit)
    return list(dict.fromkeys(ids))


def build_result(extracted: Dict[str, Any]) -> Dict[str, Any]:
    """Builds the final response payload from Gemini's extraction."""
    topics = _clean_topics(extracted.get("topics", []))
    if len(topics) < 2:
        raise ValueError("Could not find enough topics in this syllabus.")

    edges = _select_edges(topics, _predict_edges(topics))

    graph = KnowledgeGraph()
    for t in topics:
        graph.add_concept(id=t["id"], name=t["name"], unit=f"Unit {t['unit_number']}",
                          description=t["unit_title"])
    for i, j, p in edges:
        graph.add_dependency(topics[i]["id"], topics[j]["id"], "predicted_prerequisite", round(p, 3),
                             "Predicted by the trained XGBoost prerequisite classifier")

    sequence = SequenceEngine.get_topological_sequence(graph)
    bottlenecks = AnalyticsEngine.analyze_bottlenecks(graph, top_n=5).bottlenecks

    # Depth (longest path from a root) so the front end can lay the flow out left to right.
    depth: Dict[str, int] = {}
    for node in sequence:
        preds = graph.get_prerequisites(node.id)
        depth[node.id] = 1 + max((depth[p.id] for p in preds), default=-1)

    by_id = {t["id"]: t for t in topics}
    missing = []
    for m in extracted.get("missing_prerequisites", []):
        needed = _match_topic_ids(m.get("needed_for", []), topics)
        if m.get("name"):
            missing.append({
                "name": m["name"].strip(),
                "reason": m.get("reason", "").strip(),
                "needed_for": [{"id": i, "name": by_id[i]["name"]} for i in needed],
            })

    return {
        "needs_subject": False,
        "course_title": extracted.get("course_title") or "Course Syllabus",
        "course_code": extracted.get("course_code", ""),
        "nodes": [
            {"id": t["id"], "name": t["name"], "unit": t["unit_number"],
             "unit_title": t["unit_title"], "depth": depth[t["id"]]}
            for t in topics
        ],
        "edges": [
            {"source": topics[i]["id"], "target": topics[j]["id"], "confidence": round(p, 3)}
            for i, j, p in edges
        ],
        "study_flow": [
            {"step": k + 1, "id": n.id, "name": n.name, "unit": by_id[n.id]["unit_number"],
             "prerequisites": [p.name for p in graph.get_prerequisites(n.id)]}
            for k, n in enumerate(sequence)
        ],
        "bottlenecks": [
            {"id": b.concept.id, "name": b.concept.name, "unlocks": b.downstream_count,
             "direct": b.direct_dependents_count}
            for b in bottlenecks if b.downstream_count > 0
        ],
        "missing_prerequisites": missing,
    }
