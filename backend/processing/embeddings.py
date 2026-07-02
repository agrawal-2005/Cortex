"""Embedding generation using sentence-transformers."""

import logging
from typing import ClassVar

from sentence_transformers import SentenceTransformer

from backend.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generates text embeddings using a sentence-transformers model.

    The model is lazy-loaded on first use and shared across calls.
    """

    _model: ClassVar[SentenceTransformer | None] = None

    @classmethod
    def _get_model(cls) -> SentenceTransformer:
        """Lazy-load the SentenceTransformer model."""
        if cls._model is None:
            logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
            cls._model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info("Embedding model loaded successfully")
        return cls._model

    def generate_embedding(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text.

        Args:
            text: The input text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        model = self._get_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of input texts to embed.

        Returns:
            A list of embedding vectors (each a list of floats).
        """
        if not texts:
            return []

        model = self._get_model()
        embeddings = model.encode(texts, convert_to_numpy=True, batch_size=32)
        return [emb.tolist() for emb in embeddings]
