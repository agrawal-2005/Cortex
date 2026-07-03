"""Topic clustering for grouping related documents before skill extraction."""

from __future__ import annotations

import re
from collections import Counter, defaultdict

import numpy as np
from hdbscan import HDBSCAN

from backend.processing.embeddings import EmbeddingService

# Boilerplate patterns stripped before embedding (see TopicClusterer docstring).
_HTML_TAG = re.compile(r"<[^>]+>")
_URL = re.compile(r"https?://\S+")
_ID_PREFIX = re.compile(r"^(PR|Issue|Discussion) #\d+:\s*", re.IGNORECASE)
_MD_SYMBOLS = re.compile(r"[#*_`>\[\]()|]+")
_WHITESPACE = re.compile(r"\s+")


class TopicClusterer:
    """Clusters documents by semantic similarity using embeddings + HDBSCAN.

    DBSCAN with a fixed eps was abandoned: on real GitHub data it either
    chained ~72% of documents into one mega-cluster (eps=0.5) or left
    >44% as noise (eps<=0.35). HDBSCAN handles the variable-density
    embedding space, and noise points are then re-assigned to the nearest
    cluster centroid when cosine similarity clears ``reassign_similarity``.

    Documents are boilerplate-stripped before embedding (GitHub PR bodies
    are dominated by markdown symbols, HTML like dependabot's
    ``<details>`` blocks, URLs, and bot comment threads — 338/454 real
    docs had cosine < 0.95 between raw and cleaned embeddings).

    Tuning sweep on 454 real docs (2026-07-04):
    - raw text, mcs=3/ms=1 (old):        19.4% noise, max cluster 8.8%
    - mcs=5/ms=3:                        collapses to 3 clusters (48% mega)
    - UMAP-10 -> HDBSCAN:                flat sizes but worst silhouette
    - cleaned[:500], mcs=3/ms=1, t=0.45: 45 clusters, 18.9% noise,
      max cluster 5.7% (chosen)
    """

    #: How much (cleaned) content is embedded for clustering.
    EMBED_CHARS = 500

    def __init__(
        self,
        min_cluster_size: int = 3,
        min_samples: int = 1,
        reassign_similarity: float = 0.45,
    ):
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples
        self.reassign_similarity = reassign_similarity
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

        # Embed boilerplate-stripped content so clusters form around
        # topics, not markdown/HTML/bot noise.
        texts = [
            self._clean_text(d.get("content", ""))[: self.EMBED_CHARS]
            for d in documents
        ]
        embeddings = self.embedding_service.generate_embeddings(texts)

        embeddings_array = np.array(embeddings)
        labels = HDBSCAN(
            min_cluster_size=min(self.min_cluster_size, len(documents)),
            min_samples=self.min_samples,
            metric="euclidean",
            core_dist_n_jobs=-1,
        ).fit_predict(embeddings_array)

        labels = self._reassign_noise(embeddings_array, labels)

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

    @staticmethod
    def _clean_text(text: str) -> str:
        """Strip GitHub/markdown boilerplate that drowns out topical signal.

        Removes bot comment threads, literal ``\\r`` artifacts, HTML tags
        (dependabot ``<details>`` blocks), URLs, ``PR #123:`` prefixes,
        and markdown symbols.
        """
        text = text.split("--- Comments ---")[0]
        text = text.replace("\\r", " ").replace("\r", " ")
        text = _HTML_TAG.sub(" ", text)
        text = _URL.sub(" ", text)
        text = _ID_PREFIX.sub("", text)
        text = _MD_SYMBOLS.sub(" ", text)
        return _WHITESPACE.sub(" ", text).strip()

    def _reassign_noise(
        self, embeddings: np.ndarray, labels: np.ndarray
    ) -> np.ndarray:
        """Assign noise points to the nearest cluster centroid.

        A noise point joins a cluster only if its cosine similarity to that
        cluster's centroid is at least ``reassign_similarity``; genuine
        outliers stay labelled -1.
        """
        cluster_ids = np.unique(labels[labels >= 0])
        noise_idx = np.where(labels == -1)[0]
        if len(cluster_ids) == 0 or len(noise_idx) == 0:
            return labels

        centroids = np.array(
            [embeddings[labels == cid].mean(axis=0) for cid in cluster_ids]
        )
        centroids /= np.linalg.norm(centroids, axis=1, keepdims=True)
        normed = embeddings[noise_idx] / np.linalg.norm(
            embeddings[noise_idx], axis=1, keepdims=True
        )

        similarities = normed @ centroids.T
        best = similarities.argmax(axis=1)
        best_sim = similarities.max(axis=1)

        labels = labels.copy()
        take = best_sim >= self.reassign_similarity
        labels[noise_idx[take]] = cluster_ids[best[take]]
        return labels

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
            self._clean_text(d.get("content", "")) for d in documents
        )
        words = re.findall(r"\b[a-zA-Z]{3,}\b", all_text.lower())
        filtered = [w for w in words if w not in stop_words]

        if not filtered:
            return "general"

        most_common = Counter(filtered).most_common(3)
        return "_".join(word for word, _ in most_common)
