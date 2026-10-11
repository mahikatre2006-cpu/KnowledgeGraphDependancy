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

MODEL_PATH_V4 = Path(__file__).resolve().parent.parent / "ml" / "model_artifact_v4.joblib"
MODEL_PATH_V3 = Path(__file__).resolve().parent.parent / "ml" / "model_artifact_v3.joblib"

FEATURE_KEYS = [
    "embedding_similarity",
    "keyword_overlap",
    "order_delta",
]


class ClassifierInferenceService:
    """Singleton inference service wrapping the trained prerequisite classifier."""
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            model_path = MODEL_PATH_V4 if MODEL_PATH_V4.exists() else MODEL_PATH_V3
            if not model_path.exists():
                raise FileNotFoundError(
                    f"Model artifact not found at {MODEL_PATH_V4} or {MODEL_PATH_V3}. "
                    "Ensure train_v4.py has been executed."
                )
            model = joblib.load(model_path)

            # Feature schema guard
            if hasattr(model, "feature_names_in_"):
                loaded_features = list(model.feature_names_in_)
                if loaded_features != FEATURE_KEYS:
                    raise ValueError(
                        f"Feature schema mismatch! Model expected {loaded_features}, "
                        f"but inference service provides {FEATURE_KEYS}."
                    )
            cls._model = model
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

