from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer


class LocalEmbeddingService:
    """
    Local Open-Source Embedding Service using HuggingFace sentence-transformers.
    Model: sentence-transformers/all-MiniLM-L6-v2 (384-dim dense vectors).
    Runs 100% locally on CPU/GPU without external API keys.
    """
    _model_instance: SentenceTransformer = None

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        """Lazy-loads the local SentenceTransformer model instance."""
        if cls._model_instance is None:
            # Download/load lightweight local MiniLM model
            cls._model_instance = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        return cls._model_instance

    @classmethod
    def encode_text(cls, text: str) -> np.ndarray:
        """Encodes a single text string into a 384-dim numpy embedding vector."""
        if not text or not text.strip():
            return np.zeros(384, dtype=np.float32)
        model = cls.get_model()
        return model.encode(text.strip(), convert_to_numpy=True)

    @classmethod
    def encode_batch(cls, texts: List[str]) -> np.ndarray:
        """Encodes a list of text strings into an (N, 384) matrix of embedding vectors."""
        if not texts:
            return np.empty((0, 384), dtype=np.float32)
        cleaned = [t.strip() if t and t.strip() else " " for t in texts]
        model = cls.get_model()
        return model.encode(cleaned, convert_to_numpy=True, batch_size=32)

    @staticmethod
    def compute_cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Computes cosine similarity between two embedding vectors (-1.0 to 1.0)."""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
