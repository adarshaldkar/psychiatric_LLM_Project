"""
Provider-agnostic embedding service with local SentenceTransformer fallback.
"""
import logging
from abc import ABC, abstractmethod
from typing import List

import httpx
from sentence_transformers import SentenceTransformer
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
    Zero API cost, zero quota limits, ultra-fast CPU inference.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", target_dim: int = 1536):
        self._model_name = model_name
        self._target_dim = target_dim
        logger.info(f"[EMBEDDER] Loading local SentenceTransformer model '{model_name}'...")
        self._model = SentenceTransformer(model_name)

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
    Tries remote OpenAI/OpenRouter embedding endpoint.
    Automatically falls back to Local SentenceTransformer if API credits/quotas fail (402/429).
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

    def _get_local(self) -> LocalSentenceTransformerEmbedder:
        if self._local_fallback is None:
            self._local_fallback = LocalSentenceTransformerEmbedder(target_dim=self._dim)
        return self._local_fallback

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
                return [e['embedding'] for e in embeddings]
            else:
                logger.warning(f"[EMBEDDER] Remote API status {response.status_code}. Using local SentenceTransformer fallback.")
                return self._get_local().embed_batch(texts)

        except Exception as e:
            logger.warning(f"[EMBEDDER] Remote API exception: {e}. Using local SentenceTransformer fallback.")
            return self._get_local().embed_batch(texts)


# ── Singleton ─────────────────────────────────────────────────────────────────
_embedder: EmbeddingService = LocalSentenceTransformerEmbedder(target_dim=settings.EMBEDDING_DIMENSION)


def get_embedder() -> EmbeddingService:
    """Return the configured local embedding service (singleton)."""
    return _embedder
