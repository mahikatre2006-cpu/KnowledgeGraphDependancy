import re
from typing import List, Dict, Tuple, Optional
import numpy as np
from app.graph.engine import KnowledgeGraph
from app.graph.models import DependencyEdge, ConceptNode
from app.services.embedding_service import LocalEmbeddingService
from app.services.sequence_engine import SequenceEngine
from app.ml.feature_engineering import compute_features
from app.services.classifier_inference_service import ClassifierInferenceService


FOUNDATIONAL_KEYWORDS = {
    "basic", "basics", "foundation", "foundations", "introduction", "intro",
    "fundamental", "fundamentals", "python", "algebra", "calculus", "vector",
    "vectors", "probability", "statistics", "math", "linear"
}


class RelationshipInferencer:
    """
    Open-Source Local AI Relationship Inference Engine.
    Uses HuggingFace sentence-transformers (all-MiniLM-L6-v2) semantic embeddings
    combined with multi-factor directional heuristics to discover prerequisite dependencies.
    """

    @classmethod
    def infer_prerequisites(
        cls,
        graph: KnowledgeGraph,
        similarity_threshold: float = 0.0,
        min_confidence: Optional[float] = None,
        auto_add_to_graph: bool = True
    ) -> List[DependencyEdge]:
        """
        Analyzes concept nodes in the graph using local open-source embeddings & ML heuristics,
        infers directed prerequisite relationships, and returns the inferred edges.
        """
        if min_confidence is None:
            try:
                import json
                from pathlib import Path
                thresh_path = Path(__file__).resolve().parent.parent / "ml" / "decision_threshold.json"
                with open(thresh_path, "r") as f:
                    min_confidence = json.load(f).get("optimal_threshold", 0.50)
            except Exception:
                min_confidence = 0.50

        nodes = graph.get_all_nodes()
        if len(nodes) < 2:
            return []

        # 1. Compute local embeddings for all concept nodes
        node_texts = [f"{node.name}. {node.unit}. {node.description}" for node in nodes]
        embeddings = LocalEmbeddingService.encode_batch(node_texts)

        # Normalize embedding vectors for cosine similarity computation
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        norm_embeddings = embeddings / norms

        # Compute pairwise cosine similarity matrix: (N, N)
        sim_matrix = np.dot(norm_embeddings, norm_embeddings.T)

        inferred_edges: List[DependencyEdge] = []

        n = len(nodes)
        for i in range(n):
            for j in range(i + 1, n):
                node_a = nodes[i]
                node_b = nodes[j]

                # Skip if dependency already exists in either direction
                if graph.has_dependency(node_a.id, node_b.id) or graph.has_dependency(node_b.id, node_a.id):
                    continue

                sim_score = float(sim_matrix[i, j])

                if sim_score < similarity_threshold:
                    continue

                # Determine direction: A -> B or B -> A
                direction, confidence, reason = cls._determine_direction_and_confidence(
                    node_a, node_b, sim_score
                )

                if direction and confidence >= min_confidence:
                    src_node = node_a if direction == "A_to_B" else node_b
                    tgt_node = node_b if direction == "A_to_B" else node_a

                    edge = DependencyEdge(
                        source_id=src_node.id,
                        target_id=tgt_node.id,
                        relationship_type="inferred_prerequisite",
                        confidence=round(confidence, 3),
                        reason=reason
                    )

                    if auto_add_to_graph:
                        # Add edge to graph temporarily and verify it creates no cycle
                        try:
                            graph.add_dependency(
                                source_id=edge.source_id,
                                target_id=edge.target_id,
                                relationship_type=edge.relationship_type,
                                confidence=edge.confidence,
                                reason=edge.reason
                            )
                            # Check if adding edge introduced a cycle
                            if SequenceEngine.find_cycle(graph):
                                # Revert edge if cycle created
                                graph.remove_dependency(edge.source_id, edge.target_id)
                            else:
                                inferred_edges.append(edge)
                        except Exception:
                            pass
                    else:
                        inferred_edges.append(edge)

        return inferred_edges

    @classmethod
    def _determine_direction_and_confidence(
        cls,
        node_a: ConceptNode,
        node_b: ConceptNode,
        sim_score: float
    ) -> Tuple[Optional[str], float, str]:
        """
        Evaluates multi-factor directionality heuristics between node_a and node_b.
        Returns: (direction: 'A_to_B' | 'B_to_A' | None, confidence: float, reason: str)
        """
        # Factor 1: Unit Precedence
        unit_a = cls._extract_unit_number(node_a.unit)
        unit_b = cls._extract_unit_number(node_b.unit)

        unit_score = 0.0
        direction = None

        if unit_a < unit_b:
            direction = "A_to_B"
            unit_score = 0.8
        elif unit_b < unit_a:
            direction = "B_to_A"
            unit_score = 0.8
        else:
            # Same unit: check lexical containment or foundational keywords
            direction = cls._check_lexical_direction(node_a, node_b)
            unit_score = 0.5

        if not direction:
            direction = "A_to_B"

        src_node = node_a if direction == "A_to_B" else node_b
        tgt_node = node_b if direction == "A_to_B" else node_a

        # Factor 2: Lexical Containment (e.g. "Linear Algebra" in "Advanced Linear Algebra")
        lexical_score = 0.5
        if src_node.name.lower() in tgt_node.name.lower():
            lexical_score = 0.9

        # Factor 3: Foundational Keywords
        src_words = set(re.findall(r'\w+', src_node.name.lower()))
        foundational_score = 0.7 if (src_words & FOUNDATIONAL_KEYWORDS) else 0.5

        # Trained Prerequisite Classifier Inference
        order_delta = abs(unit_a - unit_b) if (unit_a != 999 and unit_b != 999) else 1
        features = compute_features(
            concept_a=src_node.name,
            concept_b=tgt_node.name,
            order_delta=order_delta,
            domain_a=src_node.unit or "",
            domain_b=tgt_node.unit or ""
        )
        features["embedding_similarity"] = round(float(sim_score), 4)
        confidence = ClassifierInferenceService.predict_edge_probability(features)

        reason = (
            f"Inferred via local SentenceTransformer embeddings (similarity: {sim_score:.2f}) "
            f"and unit precedence ({src_node.unit or 'Unit 1'} -> {tgt_node.unit or 'Unit 2'})."
            f"Predicted via trained XGBoost prerequisite classifier with SentenceTransformer embeddings (p={confidence:.2f}, "
            f"sim: {sim_score:.2f}, delta: {order_delta})."
        )

        return direction, confidence, reason

    @staticmethod
    def _extract_unit_number(unit_str: str) -> int:
        match = re.search(r'\d+', unit_str)
        return int(match.group(0)) if match else 999

    @staticmethod
    def _check_lexical_direction(node_a: ConceptNode, node_b: ConceptNode) -> Optional[str]:
        name_a = node_a.name.lower()
        name_b = node_b.name.lower()
        if name_a in name_b:
            return "A_to_B"
        if name_b in name_a:
            return "B_to_A"
        return None
