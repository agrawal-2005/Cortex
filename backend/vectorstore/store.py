"""ChromaDB vector store for skill embeddings."""

import logging
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection

from backend.config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Wraps ChromaDB for storing and querying embeddings.

    Defaults to the skill collection; pass ``collection_name`` to wrap a
    different collection (e.g. ``cortex_documents`` for document search).
    """

    COLLECTION_NAME = "cortex_skills"

    def __init__(self, collection_name: str | None = None) -> None:
        self.collection_name = collection_name or self.COLLECTION_NAME
        self._client: chromadb.PersistentClient | None = None
        self._collection: Collection | None = None

    def _get_client(self) -> chromadb.PersistentClient:
        """Lazy-load the ChromaDB persistent client."""
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR
            )
        return self._client

    def _get_collection(self) -> Collection:
        """Get or create the wrapped collection."""
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Cortex embeddings"},
            )
        return self._collection

    def add_skill(
        self,
        skill_id: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any],
    ) -> None:
        """Upsert a skill embedding into the collection.

        Args:
            skill_id: Unique identifier for the skill.
            text: The text that was embedded (title + description).
            embedding: The embedding vector.
            metadata: Additional metadata (title, status, confidence_score, etc.).
        """
        collection = self._get_collection()
        collection.upsert(
            ids=[skill_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
        )
        logger.info("Upserted skill '%s' into vector store", skill_id)

    def search(
        self,
        query_embedding: list[float],
        n_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Query the collection for similar skills.

        Args:
            query_embedding: The query embedding vector.
            n_results: Number of results to return.

        Returns:
            List of dicts with keys: id, distance, metadata.
        """
        collection = self._get_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["metadatas", "distances", "documents"],
        )

        items: list[dict[str, Any]] = []
        if results and results["ids"] and results["ids"][0]:
            ids = results["ids"][0]
            distances = results["distances"][0] if results["distances"] else [None] * len(ids)
            metadatas = results["metadatas"][0] if results["metadatas"] else [{}] * len(ids)
            documents = results["documents"][0] if results["documents"] else [None] * len(ids)

            for i, skill_id in enumerate(ids):
                items.append(
                    {
                        "id": skill_id,
                        "distance": distances[i],
                        "metadata": metadatas[i],
                        "document": documents[i],
                    }
                )

        return items

    def delete_skill(self, skill_id: str) -> None:
        """Delete a skill from the collection.

        Args:
            skill_id: The skill ID to remove.
        """
        collection = self._get_collection()
        collection.delete(ids=[skill_id])
        logger.info("Deleted skill '%s' from vector store", skill_id)

    def clear(self) -> int:
        """Hard-delete every vector in the collection.

        Deletes by id in batches (ChromaDB has no "delete all" call) and
        keeps the collection itself alive so cached handles held by other
        VectorStore instances stay valid. Returns the number deleted.
        """
        collection = self._get_collection()
        deleted = 0
        while True:
            ids = collection.get(limit=500, include=[])["ids"]
            if not ids:
                break
            collection.delete(ids=ids)
            deleted += len(ids)
        logger.warning(
            "Cleared %d vectors from collection '%s'", deleted, self.collection_name
        )
        return deleted

    def get_collection_stats(self) -> dict[str, Any]:
        """Return collection statistics.

        Returns:
            Dict with count and collection name.
        """
        collection = self._get_collection()
        return {
            "collection_name": self.collection_name,
            "count": collection.count(),
        }
