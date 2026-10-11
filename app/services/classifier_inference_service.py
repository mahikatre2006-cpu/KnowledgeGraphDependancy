"""
classifier_inference_service.py
===============================
Phase R4 & Phase 5 - Trained Classifier Inference Service

Loads Model V5 if its metadata feature list matches app/ml/features_v5.py,
otherwise falls back to Model V4 and logs a warning.
Exposes get_model(), get_model_version(), get_threshold(), and predict_edge_probability().
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
import numpy as np
import joblib

from app.ml.features_v5 import FEATURE_NAMES as FEATURE_NAMES_V5, set_pca, get_pca

logger = logging.getLogger(__name__)

MODEL_PATH_V5 = Path(__file__).resolve().parent.parent / "ml" / "model_artifact_v5.joblib"
META_PATH_V5 = Path(__file__).resolve().parent.parent / "ml" / "model_artifact_v5_meta.json"
PCA_PATH_V5 = Path(__file__).resolve().parent.parent / "ml" / "pca_artifact_v5.joblib"

MODEL_PATH_V4 = Path(__file__).resolve().parent.parent / "ml" / "model_artifact_v4.joblib"
META_PATH_V4 = Path(__file__).resolve().parent.parent / "ml" / "model_artifact_v4_meta.json"
MODEL_PATH_V3 = Path(__file__).resolve().parent.parent / "ml" / "model_artifact_v3.joblib"

FEATURE_KEYS_V4 = [
    "embedding_similarity",
    "keyword_overlap",
    "order_delta",
]


class ClassifierInferenceService:
    """Singleton inference service wrapping the trained prerequisite classifier."""
    _model = None
    _model_version: Optional[str] = None
    _threshold: Optional[float] = None
    _model_v4 = None

    @classmethod
    def load_model(cls):
        # 1. Try loading Model V5
        v5_valid = False
        if MODEL_PATH_V5.exists() and META_PATH_V5.exists():
            try:
                with open(META_PATH_V5, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                meta_features = meta.get("feature_list") or meta.get("feature_names")
                if meta_features == FEATURE_NAMES_V5:
                    model_v5 = joblib.load(MODEL_PATH_V5)
                    # Load PCA
                    if hasattr(model_v5, "pca_") and model_v5.pca_ is not None:
                        set_pca(model_v5.pca_)
                    elif PCA_PATH_V5.exists():
                        set_pca(joblib.load(PCA_PATH_V5))

                    cls._model = model_v5
                    cls._model_version = "v5"
                    cls._threshold = meta.get("threshold", 0.29)
                    logger.info("Loaded Model V5 with optimal threshold %.2f", cls._threshold)
                    v5_valid = True
                else:
                    logger.warning(
                        "Model V5 meta feature list mismatch! Expected %s, got %s. "
                        "Falling back to Model V4.",
                        FEATURE_NAMES_V5, meta_features
                    )
            except Exception as e:
                logger.warning("Failed to load Model V5: %s. Falling back to Model V4.", e)
        else:
            logger.warning("Model V5 artifact or metadata not found. Falling back to Model V4.")

        # 2. Fall back to V4 if V5 is not valid
        if not v5_valid:
            model_path_v4 = MODEL_PATH_V4 if MODEL_PATH_V4.exists() else MODEL_PATH_V3
            if not model_path_v4.exists():
                raise FileNotFoundError(
                    f"Neither Model V5 nor Model V4 found at {MODEL_PATH_V5} / {model_path_v4}."
                )
            cls._model = joblib.load(model_path_v4)
            cls._model_version = "v4"
            v4_th = 0.40
            if META_PATH_V4.exists():
                try:
                    with open(META_PATH_V4, "r", encoding="utf-8") as f:
                        meta_v4 = json.load(f)
                        v4_th = meta_v4.get("optimal_threshold") or meta_v4.get("threshold", 0.40)
                except Exception:
                    pass
            cls._threshold = v4_th
            logger.info("Loaded fallback Model V4 with threshold %.2f", cls._threshold)

    @classmethod
    def get_model(cls):
        if cls._model is None:
            cls.load_model()
        return cls._model

    @classmethod
    def get_model_version(cls) -> str:
        if cls._model is None:
            cls.load_model()
        return cls._model_version or "v4"

    @classmethod
    def get_threshold(cls) -> float:
        if cls._model is None:
            cls.load_model()
        return float(cls._threshold if cls._threshold is not None else 0.40)

    @classmethod
    def get_model_v4(cls):
        if cls._model_v4 is None:
            model_path = MODEL_PATH_V4 if MODEL_PATH_V4.exists() else MODEL_PATH_V3
            if model_path.exists():
                cls._model_v4 = joblib.load(model_path)
        return cls._model_v4

    @classmethod
    def predict_edge_probability(cls, features: Union[Dict[str, Any], np.ndarray, List[float]]) -> float:
        """
        Predicts prerequisite dependency probability (0.0 to 1.0).
        Supports:
        - 40-feature numpy vector or dict (Model V5)
        - Legacy 3-feature dict (falls back to Model V4 if legacy keys provided)
        """
        model = cls.get_model()

        if isinstance(features, np.ndarray):
            vec = features.reshape(1, -1).astype(np.float32)
            prob = float(model.predict_proba(vec)[0, 1])
            return round(prob, 4)

        if isinstance(features, (list, tuple)):
            vec = np.array([features], dtype=np.float32)
            prob = float(model.predict_proba(vec)[0, 1])
            return round(prob, 4)

        if isinstance(features, dict):
            # Check if features is legacy 3/4-key dict
            is_legacy = set(FEATURE_KEYS_V4).issubset(set(features.keys())) and not any(
                k.startswith("pca_") for k in features
            )
            if is_legacy:
                m4 = cls.get_model_v4() or model
                vec = np.array([[float(features[k]) for k in FEATURE_KEYS_V4]], dtype=np.float32)
                prob = float(m4.predict_proba(vec)[0, 1])
                return round(prob, 4)

            # Otherwise V5 feature dict
            vec = np.array([[float(features[k]) for k in FEATURE_NAMES_V5]], dtype=np.float32)
            prob = float(model.predict_proba(vec)[0, 1])
            return round(prob, 4)

        raise ValueError(f"Unsupported features type: {type(features)}")
