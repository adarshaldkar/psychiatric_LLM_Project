"""
Provider-agnostic embedding service.

Production (Render/cloud): Uses OpenRouter API for embeddings (free quota).
Local dev fallback: Uses local SentenceTransformer if API fails and torch is installed.
"""
import logging
from abc import ABC, abstractmethod
from typing import List

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_EMBED_URL = 'https://openrouter.ai/api/v1/embeddings'


class EmbeddingService(ABC):
    """Abstract embedding interface — swap implementations freely."""

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Embed a single text string. Returns a list of floats."""
        ...

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts. Returns list of embedding vectors."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding vector dimension."""
        ...


class LocalSentenceTransformerEmbedder(EmbeddingService):
    """
    100% FREE local embedding engine using SentenceTransformers (all-MiniLM-L6-v2).
    Only used as local dev fallback — requires torch + sentence-transformers installed.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", target_dim: int = 1536):
        self._model_name = model_name
        self._target_dim = target_dim
        logger.info(f"[EMBEDDER] Loading local SentenceTransformer model '{model_name}'...")
        # Lazy import — torch/sentence-transformers not required in production
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(model_name)
        except ImportError:
            raise RuntimeError(
                "sentence-transformers not installed. "
                "In production, set OPENROUTER_API_KEY so HybridEmbedder is used instead."
            )

    @property
    def dimension(self) -> int:
        return self._target_dim

    def _pad_vector(self, vec: List[float]) -> List[float]:
        if len(vec) < self._target_dim:
            return vec + [0.0] * (self._target_dim - len(vec))
        return vec[:self._target_dim]

    def embed(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        raw_embeddings = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return [self._pad_vector(vec.tolist()) for vec in raw_embeddings]


class HybridEmbedder(EmbeddingService):
    """
    Primary production embedder.
    Calls OpenRouter embedding API (text-embedding-3-small, free quota).
    Falls back to local SentenceTransformer if API fails AND torch is installed.
    Falls back to zero vectors if neither is available (graceful degradation).
    """

    def __init__(self):
        self._model = settings.EMBEDDING_MODEL
        self._dim = settings.EMBEDDING_DIMENSION
        self._headers = {
            'Authorization': f'Bearer {settings.OPENROUTER_API_KEY}',
            'Content-Type': 'application/json',
        }
        self._local_fallback = None

    @property
    def dimension(self) -> int:
        return self._dim

    def _get_local(self):
        """Lazy-load local fallback only if available."""
        if self._local_fallback is None:
            try:
                self._local_fallback = LocalSentenceTransformerEmbedder(target_dim=self._dim)
            except (ImportError, RuntimeError) as e:
                logger.warning(f"[EMBEDDER] Local fallback unavailable: {e}. Using zero vectors.")
                self._local_fallback = False  # Mark as unavailable
        return self._local_fallback if self._local_fallback else None

    def _zero_vectors(self, texts: List[str]) -> List[List[float]]:
        """Last-resort fallback: zero vectors (FTS search still works)."""
        logger.error("[EMBEDDER] All embedding methods failed. Returning zero vectors.")
        return [[0.0] * self._dim for _ in texts]

    def embed(self, text: str) -> List[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        # Truncate long texts
        truncated = [t[:32000] for t in texts]

        payload = {
            'model': self._model,
            'input': truncated,
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    OPENROUTER_EMBED_URL,
                    json=payload,
                    headers=self._headers
                )

            if response.status_code == 200:
                data = response.json()
                embeddings = sorted(data['data'], key=lambda x: x['index'])
                logger.debug(f"[EMBEDDER] OpenRouter API: embedded {len(texts)} texts.")
                return [e['embedding'] for e in embeddings]
            else:
                logger.warning(f"[EMBEDDER] Remote API status {response.status_code}. Trying local fallback.")
                local = self._get_local()
                return local.embed_batch(texts) if local else self._zero_vectors(texts)

        except Exception as e:
            logger.warning(f"[EMBEDDER] Remote API exception: {e}. Trying local fallback.")
            local = self._get_local()
            return local.embed_batch(texts) if local else self._zero_vectors(texts)


# ── Singleton: Use HybridEmbedder (API-first) in all environments ─────────────
# Production (Render/cloud): OpenRouter API handles embeddings — no torch needed
# Local dev: Falls back to local SentenceTransformer if API fails
_embedder: EmbeddingService = HybridEmbedder()


def get_embedder() -> EmbeddingService:
    """Return the configured embedding service (singleton)."""
    return _embedder
