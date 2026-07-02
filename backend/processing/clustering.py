"""Topic clustering for grouping related documents before skill extraction."""

from __future__ import annotations

import re
from collections import Counter, defaultdict

import numpy as np
from sklearn.cluster import DBSCAN

from backend.processing.embeddings import EmbeddingService


class TopicClusterer:
    """Clusters documents by semantic similarity using embeddings + DBSCAN."""

    def __init__(self, eps: float = 0.5, min_samples: int = 2):
        self.eps = eps
        self.min_samples = min_samples
        self.embedding_service = EmbeddingService()

    def cluster_documents(self, documents: list[dict]) -> list[dict]:
        """
        Cluster documents by semantic similarity.

        Args:
            documents: list of dicts with keys: id, content

        Returns:
            list of cluster dicts: {
                cluster_id: int,
                topic: str,  # generated from most common words in cluster
                document_ids: list[str],
                document_count: int
            }
            Noise points (cluster_id=-1) are grouped as "uncategorized"
        """
        if len(documents) < 2:
            return [
                {
                    "cluster_id": 0,
                    "topic": "all_documents",
                    "document_ids": [d["id"] for d in documents],
                    "document_count": len(documents),
                }
            ]

        # Generate embeddings for all documents (use first 200 chars of content)
        texts = [d.get("content", "")[:200] for d in documents]
        embeddings = self.embedding_service.generate_embeddings(texts)

        # Run DBSCAN clustering
        embeddings_array = np.array(embeddings)
        clustering = DBSCAN(
            eps=self.eps, min_samples=self.min_samples, metric="cosine"
        ).fit(embeddings_array)

        labels = clustering.labels_

        # Group documents by cluster
        clusters_map: defaultdict[int, list[dict]] = defaultdict(list)
        for idx, label in enumerate(labels):
            clusters_map[int(label)].append(documents[idx])

        # Build result
        results = []
        for cluster_id, docs in sorted(clusters_map.items()):
            topic = (
                self._extract_topic(docs) if cluster_id != -1 else "uncategorized"
            )
            results.append(
                {
                    "cluster_id": cluster_id,
                    "topic": topic,
                    "document_ids": [d["id"] for d in docs],
                    "document_count": len(docs),
                }
            )

        return results

    def _extract_topic(self, documents: list[dict]) -> str:
        """Extract a topic label from a cluster of documents using word frequency."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "can", "shall", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "as", "into", "through", "during",
            "before", "after", "above", "below", "between", "and", "but", "or",
            "not", "no", "nor", "so", "yet", "both", "either", "neither", "each",
            "every", "all", "any", "few", "more", "most", "other", "some", "such",
            "than", "too", "very", "just", "also", "this", "that", "these", "those",
            "i", "me", "my", "we", "our", "you", "your", "he", "him", "his",
            "she", "her", "it", "its", "they", "them", "their", "what", "which",
            "who", "whom", "how", "when", "where", "why",
        }

        all_text = " ".join(
            d.get("content", "") for d in documents
        )
        words = re.findall(r"\b[a-zA-Z]{3,}\b", all_text.lower())
        filtered = [w for w in words if w not in stop_words]

        if not filtered:
            return "general"

        most_common = Counter(filtered).most_common(3)
        return "_".join(word for word, _ in most_common)
