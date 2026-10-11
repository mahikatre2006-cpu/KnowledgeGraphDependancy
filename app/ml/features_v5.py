"""
features_v5.py
==============
Canonical prerequisite edge feature engineering for Model V5.
Defines ONE pair_features function used identically by both training and serving.
Zero train-serve drift.

Features (40 total):
- 8 base features:
    1. cosine_similarity
    2. signed_norm_position_gap: (pos_b - pos_a) / n
    3. signed_unit_gap: unit_b - unit_a
    4. same_unit: 1 if unit_a == unit_b else 0
    5. a_earlier_unit: 1 if unit_a < unit_b else 0
    6. keyword_overlap: Jaccard token overlap between name a and name b
    7. name_a_in_name_b: 1 if name a is in name b else 0
    8. foundational_a: 1 if name a contains foundational keywords else 0
- 32 PCA components of [emb_b - emb_a, emb_a * emb_b] (fitted on training pairs only)
"""

import re
from pathlib import Path
from typing import Optional, List, Any
import numpy as np
import joblib

PCA_PATH = Path(__file__).resolve().parent / "pca_artifact_v5.joblib"

FOUNDATIONAL_KEYWORDS = {
    "basic", "basics", "foundation", "foundations", "introduction", "intro",
    "fundamental", "fundamentals", "python", "algebra", "calculus", "vector",
    "vectors", "probability", "statistics", "math", "linear",
}

BASE_FEATURE_NAMES: List[str] = [
    "cosine_similarity",
    "signed_norm_position_gap",
    "signed_unit_gap",
    "same_unit",
    "a_earlier_unit",
    "keyword_overlap",
    "name_a_in_name_b",
    "foundational_a",
]

PCA_FEATURE_NAMES: List[str] = [f"pca_{i}" for i in range(32)]

FEATURE_NAMES: List[str] = BASE_FEATURE_NAMES + PCA_FEATURE_NAMES

_GLOBAL_PCA: Optional[Any] = None


def set_pca(pca_model: Any) -> None:
    """Sets the global PCA model instance for transforming embedding difference and product."""
    global _GLOBAL_PCA
    _GLOBAL_PCA = pca_model


def get_pca() -> Optional[Any]:
    """Retrieves or lazy-loads the global PCA model."""
    global _GLOBAL_PCA
    if _GLOBAL_PCA is None and PCA_PATH.exists():
        _GLOBAL_PCA = joblib.load(PCA_PATH)
    return _GLOBAL_PCA


def compute_keyword_overlap(text_a: str, text_b: str) -> float:
    """Computes Jaccard similarity over word tokens."""
    tokens_a = set(re.findall(r"\w+", str(text_a).lower()))
    tokens_b = set(re.findall(r"\w+", str(text_b).lower()))
    if not tokens_a or not tokens_b:
        return 0.0
    return float(len(tokens_a & tokens_b) / len(tokens_a | tokens_b))


def compute_diff_prod(emb_a: np.ndarray, emb_b: np.ndarray) -> np.ndarray:
    """Computes the 768-dim vector [emb_b - emb_a, emb_a * emb_b]."""
    ea = np.asarray(emb_a, dtype=np.float32).ravel()
    eb = np.asarray(emb_b, dtype=np.float32).ravel()
    diff = eb - ea
    prod = ea * eb
    return np.concatenate([diff, prod]).astype(np.float32)


def pair_features(
    a: str,
    b: str,
    n_topics: float,
    unit_a: float,
    unit_b: float,
    pos_a: float,
    pos_b: float,
    emb_a: np.ndarray,
    emb_b: np.ndarray,
    pca: Optional[Any] = None,
) -> np.ndarray:
    """
    Computes the canonical 40-dimensional feature vector for a directed topic pair (a -> b).
    Used identically during offline training and online serving.

    Parameters:
        a: Name of candidate prerequisite topic A
        b: Name of candidate downstream topic B
        n_topics: Total number of topics in the course
        unit_a: Module / unit index of topic A
        unit_b: Module / unit index of topic B
        pos_a: Global position of topic A in the syllabus
        pos_b: Global position of topic B in the syllabus
        emb_a: 384-dimensional embedding vector of topic A (name only)
        emb_b: 384-dimensional embedding vector of topic B (name only)
        pca: Optional scikit-learn PCA instance. If None, uses loaded global PCA.

    Returns:
        np.ndarray of shape (40,), dtype float32
    """
    ea = np.asarray(emb_a, dtype=np.float32).ravel()
    eb = np.asarray(emb_b, dtype=np.float32).ravel()

    # 1. Cosine similarity
    norm_a = float(np.linalg.norm(ea))
    norm_b = float(np.linalg.norm(eb))
    if norm_a > 1e-9 and norm_b > 1e-9:
        cos_sim = float(np.dot(ea, eb) / (norm_a * norm_b))
    else:
        cos_sim = 0.0

    # 2. Signed normalized position gap: (pos_b - pos_a) / n
    n = max(1.0, float(n_topics))
    pos_gap = float(float(pos_b) - float(pos_a)) / n

    # 3. Signed unit gap: unit_b - unit_a
    u_a = float(unit_a)
    u_b = float(unit_b)
    unit_gap = float(u_b - u_a)

    # 4. Same unit flag
    same_unit = 1.0 if int(u_a) == int(u_b) else 0.0

    # 5. A earlier unit flag
    a_earlier = 1.0 if u_a < u_b else 0.0

    # 6. Keyword overlap
    kw_overlap = compute_keyword_overlap(a, b)

    # 7. Name A in Name B
    clean_a = str(a).strip().lower()
    clean_b = str(b).strip().lower()
    name_a_in_b = 1.0 if (clean_a and clean_a in clean_b) else 0.0

    # 8. Foundational flag for A
    tokens_a = set(re.findall(r"\w+", clean_a))
    foundational_a = 1.0 if any(tok in FOUNDATIONAL_KEYWORDS for tok in tokens_a) else 0.0

    base_features = np.array([
        cos_sim,
        pos_gap,
        unit_gap,
        same_unit,
        a_earlier,
        kw_overlap,
        name_a_in_b,
        foundational_a,
    ], dtype=np.float32)

    # PCA features on [diff, prod]
    diff_prod = compute_diff_prod(ea, eb)

    pca_model = pca if pca is not None else get_pca()
    if pca_model is None:
        raise RuntimeError(
            "PCA model is not fitted or loaded yet. Call set_pca(pca) or train_v5 first."
        )

    pca_features = pca_model.transform(diff_prod.reshape(1, -1))[0].astype(np.float32)

    return np.concatenate([base_features, pca_features]).astype(np.float32)
