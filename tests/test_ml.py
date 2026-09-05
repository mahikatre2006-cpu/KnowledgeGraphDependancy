"""
test_ml.py
==========
Unit tests for the ML pipeline:
- Feature engineering
- Model artifact inference service
- Zero concept leakage split guarantee
"""

import pytest
import pandas as pd
from app.ml.feature_engineering import compute_features, compute_keyword_overlap
from app.services.classifier_inference_service import ClassifierInferenceService
from app.ml.train_classifier import concept_aware_split


def test_compute_keyword_overlap():
    sim = compute_keyword_overlap("Linear Algebra Basics", "Advanced Linear Algebra")
    assert sim > 0.0
    assert sim <= 1.0

    zero_sim = compute_keyword_overlap("Thermodynamics", "Database Management")
    assert zero_sim == 0.0


def test_compute_features_shape_and_types():
    features = compute_features(
        concept_a="Calculus 1",
        concept_b="Multivariable Calculus",
        order_delta=2,
        domain_a="MATH",
        domain_b="MATH"
    )
    assert "embedding_similarity" in features
    assert "order_delta" in features
    assert "domain_match" in features
    assert "keyword_overlap" in features

    assert isinstance(features["embedding_similarity"], float)
    assert isinstance(features["order_delta"], int)
    assert features["domain_match"] == 1
    assert isinstance(features["keyword_overlap"], float)


def test_classifier_inference_service():
    features = {
        "embedding_similarity": 0.65,
        "order_delta": 2,
        "domain_match": 1,
        "keyword_overlap": 0.4
    }
    prob = ClassifierInferenceService.predict_edge_probability(features)
    assert isinstance(prob, float)
    assert 0.0 <= prob <= 1.0


def test_concept_aware_split_no_leakage():
    sample_data = {
        "concept_a": ["TopicA", "TopicB", "TopicC", "TopicD", "TopicE", "TopicF"],
        "concept_b": ["TopicB", "TopicC", "TopicD", "TopicE", "TopicF", "TopicG"],
        "Course_Code": ["CS101", "CS101", "CS102", "CS102", "CS103", "CS103"],
        "source_syllabus": ["a.pdf"] * 6,
        "embedding_similarity": [0.5] * 6,
        "order_delta": [1] * 6,
        "domain_match": [1] * 6,
        "keyword_overlap": [0.2] * 6,
        "label": [1, 0, 1, 0, 1, 0]
    }
    df = pd.DataFrame(sample_data)
    train_df, val_df, test_df = concept_aware_split(df, train_ratio=0.5, val_ratio=0.25)

    train_c = set(train_df["concept_a"]).union(set(train_df["concept_b"]))
    val_c = set(val_df["concept_a"]).union(set(val_df["concept_b"]))
    test_c = set(test_df["concept_a"]).union(set(test_df["concept_b"]))

    assert train_c.isdisjoint(val_c)
    assert train_c.isdisjoint(test_c)

