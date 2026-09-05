"""
feature_engineering.py
=======================
Phase R2 - Shared Feature Module

Defines the canonical feature extraction function used identically
during offline training and online FastAPI relationship inference.

Guarantees zero train-inference feature drift.
"""

import re
from typing import Dict, Any
from app.services.embedding_service import LocalEmbeddingService


def compute_keyword_overlap(text_a: str, text_b: str) -> float:
    """Computes Jaccard similarity over word tokens between two concept strings."""
    tokens_a = set(re.findall(r"\w+", text_a.lower()))
    tokens_b = set(re.findall(r"\w+", text_b.lower()))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return float(len(intersection) / len(union))


def compute_features(
    concept_a: str,
    concept_b: str,
    order_delta: int,
    domain_a: str,
    domain_b: str
) -> Dict[str, Any]:
    """
    Computes standard prerequisite classifier features for a directed pair (concept_a -> concept_b).

    Parameters:
        concept_a: Source concept name (potential prerequisite)
        concept_b: Target concept name (downstream concept)
        order_delta: Relative position distance (e.g. unit/topic order offset)
        domain_a: Subject, course code, or unit identifier of concept_a
        domain_b: Subject, course code, or unit identifier of concept_b

    Returns:
        Dict containing exactly:
          - 'embedding_similarity': float cosine similarity [-1.0, 1.0] via all-MiniLM-L6-v2
          - 'order_delta': int positional gap
          - 'domain_match': int (1 if domain_a and domain_b match, else 0)
          - 'keyword_overlap': float Jaccard token overlap [0.0, 1.0]
    """
    clean_a = str(concept_a).strip()
    clean_b = str(concept_b).strip()

    # 1. Embedding Similarity via shared LocalEmbeddingService
    vec_a = LocalEmbeddingService.encode_text(clean_a)
    vec_b = LocalEmbeddingService.encode_text(clean_b)
    emb_sim = LocalEmbeddingService.compute_cosine_similarity(vec_a, vec_b)

    # 2. Domain Match
    clean_dom_a = str(domain_a).strip().lower()
    clean_dom_b = str(domain_b).strip().lower()
    domain_match = 1 if (clean_dom_a and clean_dom_b and clean_dom_a == clean_dom_b) else 0

    # 3. Keyword Overlap
    kw_overlap = compute_keyword_overlap(clean_a, clean_b)

    return {
        "embedding_similarity": round(float(emb_sim), 4),
        "order_delta": int(order_delta),
        "domain_match": int(domain_match),
        "keyword_overlap": round(float(kw_overlap), 4),
    }

