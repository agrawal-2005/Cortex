"""Batch document embedder — generates embeddings and stores them in ChromaDB."""

import logging
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.knowledge.models import Document
from backend.processing.embeddings import EmbeddingService

logger = logging.getLogger(__name__)

COLLECTION_NAME = "cortex_documents"


class DocumentEmbedder:
    """Batch embeds documents and stores vectors in a dedicated ChromaDB collection."""

    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()
        self._client: chromadb.PersistentClient | None = None

    def _get_client(self) -> chromadb.PersistentClient:
        """Lazy-load a ChromaDB persistent client from settings."""
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
            )
        return self._client

    def _get_collection(self) -> Collection:
        """Get or create the documents collection."""
        client = self._get_client()
        return client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Cortex document embeddings"},
        )

    async def embed_documents(
        self,
        db: AsyncSession,
        document_ids: list[str] | None = None,
        batch_size: int = 64,
    ) -> dict[str, Any]:
        """Embed documents and store in ChromaDB.

        If *document_ids* is ``None``, embeds all documents that do not yet
        have an ``embedding_id``.

        Returns a stats dict with keys ``embedded``, ``skipped``, ``errors``,
        and ``total``.
        """
        query = select(Document)
        if document_ids:
            query = query.where(Document.id.in_(document_ids))
        else:
            query = query.where(Document.embedding_id.is_(None))

        result = await db.execute(query)
        docs = list(result.scalars().all())

        if not docs:
            logger.info("No documents to embed")
            return {"embedded": 0, "skipped": 0, "errors": 0, "total": 0}

        logger.info("Embedding %d documents...", len(docs))

        collection = self._get_collection()
        embedded = 0
        errors = 0

        for i in range(0, len(docs), batch_size):
            batch = docs[i : i + batch_size]
            texts = [d.content[:500] for d in batch]

            try:
                embeddings = self.embedding_service.generate_embeddings(texts)

                ids: list[str] = []
                metadatas: list[dict[str, str]] = []
                documents_text: list[str] = []

                for doc, embedding in zip(batch, embeddings):
                    emb_id = f"doc-{doc.id}"
                    ids.append(emb_id)
                    metadatas.append(
                        {
                            "document_id": doc.id,
                            "source_type": doc.source_type,
                            "channel": doc.channel_or_project or "",
                            "author": doc.author_name or "",
                        }
                    )
                    documents_text.append(doc.content[:500])
                    doc.embedding_id = emb_id

                collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents_text,
                    metadatas=metadatas,
                )

                await db.flush()
                embedded += len(batch)
                logger.info(
                    "Embedded batch %d-%d (%d/%d)",
                    i,
                    i + len(batch),
                    embedded,
                    len(docs),
                )

            except Exception as e:
                logger.error("Error embedding batch %d: %s", i, e)
                errors += len(batch)

        stats = {
            "embedded": embedded,
            "skipped": 0,
            "errors": errors,
            "total": len(docs),
        }
        logger.info("Embedding complete: %s", stats)
        return stats

    async def get_all_embeddings(self) -> dict[str, Any]:
        """Retrieve all document embeddings from ChromaDB.

        Returns a dict with keys ``ids``, ``embeddings``, ``metadatas``, and
        ``documents``.
        """
        try:
            client = self._get_client()
            collection = client.get_collection(name=COLLECTION_NAME)
        except Exception:
            return {"ids": [], "embeddings": [], "metadatas": [], "documents": []}

        return collection.get(
            include=["embeddings", "metadatas", "documents"],
        )
