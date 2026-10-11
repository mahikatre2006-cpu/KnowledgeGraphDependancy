"""
test_features_parity.py
=======================
Verifies feature parity between training and serving pipelines:
1. Training and serving produce identical 40-dimensional vectors for a sample pair.
2. Vectors contain no NaNs or Infs and match the 40-feature schema.
3. ClassifierInferenceService loads Model V5 and produces valid probability.
"""

import numpy as np
import pytest

from app.services.embedding_service import LocalEmbeddingService
from app.ml.features_v5 import (
    FEATURE_NAMES,
    pair_features,
    get_pca,
)
from app.services.classifier_inference_service import ClassifierInferenceService


def test_feature_vector_parity():
    # 1. Ensure PCA is loaded/available
    pca = get_pca()
    assert pca is not None, "PCA model must be loaded from pca_artifact_v5.joblib"
    assert len(FEATURE_NAMES) == 40

    # 2. Sample topic pair
    topic_a = "Introduction to JavaScript"
    topic_b = "React Components"
    n_topics = 50
    unit_a = 1
    unit_b = 2
    pos_a = 2
    pos_b = 14

    emb_a = LocalEmbeddingService.encode_text(topic_a)
    emb_b = LocalEmbeddingService.encode_text(topic_b)

    # Compute feature vector via training path
    vec_train = pair_features(
        a=topic_a,
        b=topic_b,
        n_topics=n_topics,
        unit_a=unit_a,
        unit_b=unit_b,
        pos_a=pos_a,
        pos_b=pos_b,
        emb_a=emb_a,
        emb_b=emb_b,
        pca=pca,
    )

    # Compute feature vector via serving path (global PCA singleton)
    vec_serve = pair_features(
        a=topic_a,
        b=topic_b,
        n_topics=n_topics,
        unit_a=unit_a,
        unit_b=unit_b,
        pos_a=pos_a,
        pos_b=pos_b,
        emb_a=emb_a,
        emb_b=emb_b,
    )

    # Assert shape, types, and values
    assert vec_train.shape == (40,)
    assert vec_serve.shape == (40,)
    assert not np.isnan(vec_train).any()
    assert not np.isinf(vec_train).any()
    assert not np.isnan(vec_serve).any()
    assert not np.isinf(vec_serve).any()

    # Assert exact parity between training and serving vectors
    np.testing.assert_allclose(vec_train, vec_serve, rtol=1e-6, atol=1e-6)

    # Assert base features sanity
    # pos_gap = (14 - 2) / 50 = 0.24
    assert np.isclose(vec_serve[1], 0.24, atol=1e-4)
    # unit_gap = 2 - 1 = 1.0
    assert np.isclose(vec_serve[2], 1.0, atol=1e-4)
    # same_unit = 0.0
    assert vec_serve[3] == 0.0
    # a_earlier = 1.0
    assert vec_serve[4] == 1.0
    # foundational_a = 1.0 (contains "introduction")
    assert vec_serve[7] == 1.0


def test_classifier_serving_v5():
    # Verify inference service loads V5
    assert ClassifierInferenceService.get_model_version() == "v5"
    threshold = ClassifierInferenceService.get_threshold()
    assert 0.1 <= threshold <= 0.9

    # Test prediction on 40-dim vector
    topic_a = "Introduction to JavaScript"
    topic_b = "React Components"
    emb_a = LocalEmbeddingService.encode_text(topic_a)
    emb_b = LocalEmbeddingService.encode_text(topic_b)

    vec = pair_features(
        a=topic_a,
        b=topic_b,
        n_topics=50,
        unit_a=1,
        unit_b=2,
        pos_a=2,
        pos_b=14,
        emb_a=emb_a,
        emb_b=emb_b,
    )

    prob = ClassifierInferenceService.predict_edge_probability(vec)
    assert isinstance(prob, float)
    assert 0.0 <= prob <= 1.0

