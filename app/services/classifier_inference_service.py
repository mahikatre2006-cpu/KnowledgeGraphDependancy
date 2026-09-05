"""
classifier_inference_service.py
===============================
Phase R4 - Trained Classifier Inference Service

Loads the frozen XGBoost model artifact (app/ml/model_artifact.joblib) once
at module import time and exposes predict_edge_probability for online inference.
"""

from pathlib import Path
from typing import Dict, Any
import numpy as np
import joblib

MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "model_artifact.joblib"

FEATURE_KEYS = [
    "embedding_similarity",
    "order_delta",
    "domain_match",
    "keyword_overlap",
]


class ClassifierInferenceService:
    """Singleton inference service wrapping the frozen XGBoost model."""
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            if not MODEL_PATH.exists():
                raise FileNotFoundError(
                    f"Model artifact not found at {MODEL_PATH}. "
                    "Ensure train_classifier.py has been executed."
                )
            cls._model = joblib.load(MODEL_PATH)
        return cls._model

    @classmethod
    def predict_edge_probability(cls, features: Dict[str, Any]) -> float:
        """
        Predicts prerequisite dependency probability (0.0 to 1.0) given standard feature dict.
        """
        model = cls.get_model()
        vec = np.array([[float(features[k]) for k in FEATURE_KEYS]], dtype=np.float32)
        # Probability of class 1 (prerequisite edge exists)
        prob = float(model.predict_proba(vec)[0, 1])
        return round(prob, 4)

