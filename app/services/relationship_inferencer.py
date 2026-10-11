"""
relationship_inferencer.py — Prerequisite relationship inference engine (Model V5).

Optimisations & specifications:
- Embed unique topic names (name only) in ONE batch
- Build pair features using canonical app.ml.features_v5.pair_features
- ONE predict_proba call over all candidate pairs
- Candidate pairs: forward only (i<j), within course syllabus
- Window constraint: same module OR (j - i) <= max(12, n)
- Graph rules: in-degree <= 3, out-degree <= 6, reject cycles, transitive reduction
- NO orphan attachment
- 100% offline operation (no external APIs or network calls)
"""

import re
from time import perf_counter
from typing import List, Dict, Tuple, Optional
import numpy as np

from app.graph.engine import KnowledgeGraph
from app.graph.models import DependencyEdge, ConceptNode
from app.services.embedding_service import LocalEmbeddingService
from app.services.sequence_engine import SequenceEngine
from app.ml.features_v5 import pair_features, compute_keyword_overlap
from app.services.classifier_inference_service import ClassifierInferenceService

FOUNDATIONAL_KEYWORDS = {
    "basic", "basics", "foundation", "foundations", "introduction", "intro",
    "fundamental", "fundamentals", "python", "algebra", "calculus", "vector",
    "vectors", "probability", "statistics", "math", "linear",
}

MAX_IN_DEGREE = 3
MAX_OUT_DEGREE = 6


class RelationshipInferencer:
    """
    Batch-optimised prerequisite inference engine.
    Embedder + XGBoost loaded at app startup (lifespan) via warm_up().
    """

    # Name->vector cache shared across requests
    _embedding_cache: Dict[str, np.ndarray] = {}

    @classmethod
    def warm_up(cls) -> None:
        """Pre-load embedder and classifier. Call once at app startup."""
        t0 = perf_counter()
        LocalEmbeddingService.get_model()
        ClassifierInferenceService.get_model()
        print(f"[TIMING] model_warmup={perf_counter()-t0:.3f}s")

    @classmethod
    def infer_prerequisites(
        cls,
        graph: KnowledgeGraph,
        similarity_threshold: float = 0.0,
        min_confidence: Optional[float] = None,
        auto_add_to_graph: bool = True,
    ) -> List[DependencyEdge]:
        """
        Batch-vectorised prerequisite inference.
        Returns list of inferred DependencyEdge objects.
        """
        t_total = perf_counter()

        if min_confidence is None:
            min_confidence = ClassifierInferenceService.get_threshold()

        nodes = graph.get_all_nodes()
        n = len(nodes)
        if n < 2:
            return []

        # ── 1. Embed unique topic names (name only) in ONE batch ─────────────
        t0 = perf_counter()
        unique_texts = list({nd.name for nd in nodes})
        to_embed = [txt for txt in unique_texts if txt not in cls._embedding_cache]
        if to_embed:
            vecs = LocalEmbeddingService.encode_batch(to_embed)
            for txt, vec in zip(to_embed, vecs):
                cls._embedding_cache[txt] = vec
        # Build per-node embedding matrix
        emb_matrix = np.array([
            cls._embedding_cache[nd.name]
            for nd in nodes
        ], dtype=np.float32)
        print(f"[TIMING] embed={perf_counter()-t0:.3f}s  unique={len(unique_texts)}")

        # Normalise for cosine similarity
        norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        norm_emb = emb_matrix / norms
        sim_matrix = norm_emb @ norm_emb.T  # (N, N)

        # ── 2. Build candidate pairs with window constraint ───────────────────
        t0 = perf_counter()
        unit_nums = np.array([cls._extract_unit_number(nd.unit) for nd in nodes])

        # Forward pairs i<j where same unit OR j-i <= max(12, n)
        is_small_graph = (n <= 12)
        cand_window = max(12, n)
        pair_i: List[int] = []
        pair_j: List[int] = []
        for i in range(n):
            for j in range(i + 1, n):
                if not is_small_graph and sim_matrix[i, j] < similarity_threshold:
                    continue
                if graph.has_dependency(nodes[i].id, nodes[j].id) or \
                   graph.has_dependency(nodes[j].id, nodes[i].id):
                    continue
                same_unit = (unit_nums[i] == unit_nums[j])
                if same_unit or (j - i) <= cand_window:
                    pair_i.append(i)
                    pair_j.append(j)
        print(f"[TIMING] pair_build={perf_counter()-t0:.3f}s  candidates={len(pair_i)}")

        if not pair_i:
            return []

        # ── 3. Feature computation ────────────────────────────────────────────
        t0 = perf_counter()
        model_version = ClassifierInferenceService.get_model_version()
        model = ClassifierInferenceService.get_model()

        if model_version == "v5":
            X = np.array([
                pair_features(
                    a=nodes[i].name,
                    b=nodes[j].name,
                    n_topics=n,
                    unit_a=unit_nums[i],
                    unit_b=unit_nums[j],
                    pos_a=i,
                    pos_b=j,
                    emb_a=emb_matrix[i],
                    emb_b=emb_matrix[j],
                )
                for i, j in zip(pair_i, pair_j)
            ], dtype=np.float32)
        else:
            # Fallback Model V4 3-feature representation
            sims = sim_matrix[pair_i, pair_j]
            deltas = np.array([j - i for i, j in zip(pair_i, pair_j)], dtype=np.float32)
            kw_overlaps = np.array([
                compute_keyword_overlap(nodes[i].name, nodes[j].name)
                for i, j in zip(pair_i, pair_j)
            ], dtype=np.float32)
            X = np.column_stack([sims, kw_overlaps, deltas]).astype(np.float32)

        print(f"[TIMING] feature_build={perf_counter()-t0:.3f}s  pairs={len(pair_i)} (model={model_version})")

        # ── 4. ONE predict_proba call ─────────────────────────────────────────
        t0 = perf_counter()
        probs = model.predict_proba(X)[:, 1]  # P(prerequisite=1)
        print(f"[TIMING] predict={perf_counter()-t0:.3f}s")

        # ── 5. Graph rules ────────────────────────────────────────────────────
        t0 = perf_counter()
        inferred_edges: List[DependencyEdge] = []
        sims_diag = sim_matrix[pair_i, pair_j]

        # Sort by probability descending so high-confidence edges win caps first
        order = np.argsort(-probs)
        for k in order:
            if probs[k] < min_confidence:
                continue

            i, j = pair_i[k], pair_j[k]
            node_a, node_b = nodes[i], nodes[j]

            # Determine direction
            direction = cls._determine_direction(node_a, node_b, unit_nums[i], unit_nums[j])
            src_node = node_a if direction == "A_to_B" else node_b
            tgt_node = node_b if direction == "A_to_B" else node_a

            if src_node.id == tgt_node.id:
                continue
            if not graph.has_concept(src_node.id) or not graph.has_concept(tgt_node.id):
                continue
            if graph.has_dependency(src_node.id, tgt_node.id):
                continue

            # in-degree cap
            if graph.get_in_degree(tgt_node.id) >= MAX_IN_DEGREE:
                continue
            # out-degree cap
            if graph.get_out_degree(src_node.id) >= MAX_OUT_DEGREE:
                continue

            reason_str = (
                f"Inferred via local SentenceTransformer embeddings "
                f"(similarity: {sims_diag[k]:.2f}, p={probs[k]:.2f})"
            )

            if auto_add_to_graph:
                try:
                    graph.add_dependency(
                        source_id=src_node.id,
                        target_id=tgt_node.id,
                        relationship_type="inferred_prerequisite",
                        confidence=round(float(probs[k]), 3),
                        reason=reason_str,
                        tier="strong",
                    )
                    # Reject if cycle introduced
                    if SequenceEngine.find_cycle(graph):
                        graph.remove_dependency(src_node.id, tgt_node.id)
                    else:
                        inferred_edges.append(
                            DependencyEdge(
                                source_id=src_node.id,
                                target_id=tgt_node.id,
                                relationship_type="inferred_prerequisite",
                                tier="strong",
                                confidence=round(float(probs[k]), 3),
                                reason=reason_str,
                            )
                        )
                except Exception:
                    pass
            else:
                inferred_edges.append(
                    DependencyEdge(
                        source_id=src_node.id,
                        target_id=tgt_node.id,
                        relationship_type="inferred_prerequisite",
                        tier="strong",
                        confidence=round(float(probs[k]), 3),
                        reason=reason_str,
                    )
                )

        # Transitive reduction (remove redundant edges)
        if auto_add_to_graph:
            cls._transitive_reduction(graph)
            inferred_edges = [
                e for e in inferred_edges
                if graph.has_dependency(e.source_id, e.target_id)
            ]

        print(f"[TIMING] graph_rules={perf_counter()-t0:.3f}s  edges={len(inferred_edges)}")
        print(f"[TIMING] infer_total={perf_counter()-t_total:.3f}s")
        return inferred_edges

    @staticmethod
    def _determine_direction(
        node_a: ConceptNode,
        node_b: ConceptNode,
        unit_a: int,
        unit_b: int,
    ) -> str:
        """Fast direction heuristic: unit order, then lexical containment."""
        if unit_a < unit_b:
            return "A_to_B"
        if unit_b < unit_a:
            return "B_to_A"
        # Same unit: lexical containment
        name_a = node_a.name.lower()
        name_b = node_b.name.lower()
        if name_a in name_b:
            return "A_to_B"
        if name_b in name_a:
            return "B_to_A"
        # Default: A (earlier) -> B (later)
        return "A_to_B"

    @staticmethod
    def _extract_unit_number(unit_str: str) -> int:
        match = re.search(r'\d+', unit_str or "")
        return int(match.group(0)) if match else 999

    @staticmethod
    def _transitive_reduction(graph: KnowledgeGraph) -> None:
        """
        Remove edges that are implied by longer paths (transitive reduction).
        Only removes edges if removing them keeps reachability intact.
        Uses simple DFS — safe for DAG of <= 120 nodes.
        """
        edges = list(graph.get_all_edges())
        for edge in edges:
            src, tgt = edge.source_id, edge.target_id
            if not graph.has_dependency(src, tgt):
                continue
            # Temporarily remove edge, check if tgt still reachable from src
            graph.remove_dependency(src, tgt)
            if _dfs_reachable(graph, src, tgt):
                # Redundant — keep removed
                pass
            else:
                # Not reachable — restore edge
                graph.add_dependency(
                    source_id=src,
                    target_id=tgt,
                    relationship_type=edge.relationship_type,
                    confidence=edge.confidence,
                    reason=edge.reason,
                    tier=edge.tier,
                )


def _dfs_reachable(graph: KnowledgeGraph, start: str, goal: str) -> bool:
    """DFS reachability check from start to goal (excluding direct edge)."""
    visited = set()
    stack = [start]
    while stack:
        cur = stack.pop()
        if cur in visited:
            continue
        visited.add(cur)
        for dep in graph.get_dependents(cur):
            if dep.id == goal:
                return True
            stack.append(dep.id)
    return False
