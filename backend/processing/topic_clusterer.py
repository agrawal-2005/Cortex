"""Topic clustering using HDBSCAN on document embeddings with LLM-based labeling."""

import logging
import re
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from hdbscan import HDBSCAN
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEndpoint

from backend.config import settings
from backend.processing.embedder import DocumentEmbedder

logger = logging.getLogger(__name__)

_LABEL_PROMPT = PromptTemplate.from_template(
    "Below are sample messages from a group of related documents in a "
    "company knowledge base.\n\n"
    "Samples:\n{samples}\n\n"
    "Based on these samples, provide a short descriptive topic label "
    "(2-5 words) for this group. "
    "Respond with ONLY the topic label, nothing else."
)

_STOP_WORDS = frozenset(
    {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "to", "of", "in", "for", "on", "with",
        "at", "by", "from", "as", "and", "but", "or", "not", "this",
        "that", "these", "those", "i", "me", "my", "we", "our", "you",
        "your", "he", "she", "it", "they", "them", "their", "what",
        "which", "who", "how", "when", "where", "why",
    }
)


class TopicClusterer:
    """Clusters documents by topic using HDBSCAN on embeddings, then labels
    each cluster via an LLM.
    """

    def __init__(
        self,
        min_cluster_size: int = 3,
        min_samples: int = 2,
    ) -> None:
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.embedder = DocumentEmbedder()
        self._llm: HuggingFaceEndpoint | None = None

    def _get_llm(self) -> HuggingFaceEndpoint:
        """Lazy-initialise the HuggingFace LLM endpoint."""
        if self._llm is None:
            self._llm = HuggingFaceEndpoint(
                repo_id=settings.LLM_MODEL,
                huggingfacehub_api_token=settings.HUGGINGFACE_API_TOKEN,
                temperature=0.1,
                max_new_tokens=100,
            )
        return self._llm

    async def cluster(self) -> dict[str, Any]:
        """Run the full clustering pipeline.

        1. Pull all embeddings from ChromaDB.
        2. Run HDBSCAN to find natural clusters.
        3. Label each cluster using the LLM.
        4. Return cluster assignments.
        """
        data = await self.embedder.get_all_embeddings()
        ids: list[str] = data.get("ids", [])
        embeddings: list[list[float]] = data.get("embeddings", [])
        metadatas: list[dict] = data.get("metadatas", [])
        documents: list[str] = data.get("documents", [])

        if not embeddings or len(embeddings) < self.min_cluster_size:
            logger.info(
                "Not enough documents to cluster (%d)", len(embeddings)
            )
            return {
                "clusters": [],
                "total_documents": len(ids),
                "cluster_count": 0,
                "noise_count": len(ids),
            }

        embeddings_array = np.array(embeddings)
        logger.info(
            "Running HDBSCAN on %d embeddings...", len(embeddings_array)
        )

        clusterer = HDBSCAN(
            min_cluster_size=self.min_cluster_size,
            min_samples=self.min_samples,
            metric="euclidean",
        )
        labels = clusterer.fit_predict(embeddings_array)

        # Group documents by cluster label
        clusters_map: dict[int, list[dict]] = defaultdict(list)
        for idx, label in enumerate(labels):
            doc_info = {
                "id": ids[idx] if idx < len(ids) else None,
                "metadata": metadatas[idx] if idx < len(metadatas) else {},
                "text": documents[idx] if idx < len(documents) else "",
            }
            clusters_map[int(label)].append(doc_info)

        # Label each cluster with the LLM
        results: list[dict[str, Any]] = []
        noise_docs = clusters_map.pop(-1, [])

        for cluster_id, docs in sorted(clusters_map.items()):
            sample_texts = [d["text"][:200] for d in docs[:5]]
            label = await self._label_cluster(sample_texts)

            results.append(
                {
                    "cluster_id": cluster_id,
                    "label": label,
                    "document_ids": [d["id"] for d in docs],
                    "document_count": len(docs),
                    "sample_texts": sample_texts[:3],
                }
            )

        if noise_docs:
            results.append(
                {
                    "cluster_id": -1,
                    "label": "uncategorized",
                    "document_ids": [d["id"] for d in noise_docs],
                    "document_count": len(noise_docs),
                    "sample_texts": [d["text"][:200] for d in noise_docs[:3]],
                }
            )

        return {
            "clusters": results,
            "total_documents": len(ids),
            "cluster_count": len(
                [r for r in results if r["cluster_id"] != -1]
            ),
            "noise_count": len(noise_docs),
        }

    async def _label_cluster(self, sample_texts: list[str]) -> str:
        """Use the LLM to generate a descriptive label for a cluster."""
        samples_text = "\n---\n".join(sample_texts)

        try:
            llm = self._get_llm()
            chain = _LABEL_PROMPT | llm
            response = await chain.ainvoke({"samples": samples_text})
            label = response.strip().strip('"').strip("'").lower()
            return label if label else "unlabeled"
        except Exception as e:
            logger.warning("LLM labeling failed: %s", e)
            return self._fallback_label(sample_texts)

    @staticmethod
    def _fallback_label(texts: list[str]) -> str:
        """Generate a label from word frequency when the LLM is unavailable."""
        all_text = " ".join(texts)
        words = re.findall(r"\b[a-zA-Z]{3,}\b", all_text.lower())
        filtered = [w for w in words if w not in _STOP_WORDS]

        if not filtered:
            return "general"

        most_common = Counter(filtered).most_common(3)
        return " ".join(word for word, _ in most_common)
