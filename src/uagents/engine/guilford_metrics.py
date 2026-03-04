"""Creativity metrics based on Guilford's divergent thinking dimensions.
Spec reference: Section 11.3 (metrics.guilford_dimensions).

Measures:
- Fluency: number of distinct ideas
- Flexibility: number of distinct categories/approaches
- Originality: semantic distance from common solutions (TF-IDF cosine)
- Elaboration: detail level of ideas (word count heuristic)
"""
from __future__ import annotations

import logging

from ..models.creativity import DivergentIdea, GuilfordScores
from .diversity_engine import (
    compute_idf,
    cosine_distance,
    tf_idf_vector,
    tokenize,
)

logger = logging.getLogger("uagents.guilford_metrics")


class GuilfordMetrics:
    """Computes Guilford divergent thinking scores for creative sessions.

    Uses TF-IDF cosine distance (reused from diversity_engine) for
    originality measurement. Category assignment for flexibility is
    done via content clustering heuristic.
    """

    # Minimum word count for an idea to be considered "elaborated"
    ELABORATION_THRESHOLD = 50

    def compute(
        self,
        ideas: list[DivergentIdea],
        corpus: list[str] | None = None,
    ) -> GuilfordScores:
        """Compute all 4 Guilford dimensions for a set of ideas.

        Args:
            ideas: List of divergent ideas from a creative session.
            corpus: Optional list of prior solutions for originality baseline.
                If None, originality is computed as mean pairwise distance.

        Returns:
            GuilfordScores with all 4 dimensions.

        Raises:
            ValueError: If ideas list is empty.
        """
        if not ideas:
            raise ValueError("Cannot compute Guilford metrics on empty ideas list")

        fluency = self._compute_fluency(ideas)
        flexibility = self._compute_flexibility(ideas)
        originality = self._compute_originality(ideas, corpus)
        elaboration = self._compute_elaboration(ideas)

        return GuilfordScores(
            fluency=fluency,
            flexibility=flexibility,
            originality=originality,
            elaboration=elaboration,
        )

    def _compute_fluency(self, ideas: list[DivergentIdea]) -> int:
        """Fluency = number of distinct non-empty ideas."""
        seen: set[str] = set()
        count = 0
        for idea in ideas:
            # Deduplicate by normalized content
            normalized = idea.content.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                count += 1
        return count

    def _compute_flexibility(self, ideas: list[DivergentIdea]) -> int:
        """Flexibility = number of distinct categories/approaches.

        Uses TF-IDF clustering heuristic: ideas with cosine distance < 0.3
        are considered same category. Counts resulting clusters.
        """
        if len(ideas) < 2:
            return len(ideas)

        # FM-P6-IMP-014-FIX: Track original indices to handle empty-content gaps
        filtered = [
            (i, idea.content) for i, idea in enumerate(ideas)
            if idea.content.strip()
        ]
        if len(filtered) < 2:
            return len(filtered)

        original_indices = [i for i, _ in filtered]
        texts = [content for _, content in filtered]

        tokenized = [tokenize(t) for t in texts]
        idf = compute_idf(tokenized)
        vectors = [tf_idf_vector(tok, idf) for tok in tokenized]

        # Greedy clustering: assign each idea to first cluster within threshold
        clusters: list[list[int]] = []
        cluster_threshold = 0.3  # cosine distance below this = same category

        for i, vec in enumerate(vectors):
            assigned = False
            for cluster in clusters:
                representative = vectors[cluster[0]]
                dist = cosine_distance(vec, representative)
                if dist < cluster_threshold:
                    cluster.append(i)
                    assigned = True
                    break
            if not assigned:
                clusters.append([i])

        # Update idea categories for transparency
        # Use original_indices to map filtered positions back to ideas list
        for cluster_idx, cluster in enumerate(clusters):
            category_label = f"approach_{cluster_idx + 1}"
            for text_idx in cluster:
                ideas[original_indices[text_idx]].category = category_label

        return len(clusters)

    def _compute_originality(
        self,
        ideas: list[DivergentIdea],
        corpus: list[str] | None,
    ) -> float:
        """Originality = mean semantic distance from baseline.

        If corpus provided: distance from corpus centroid.
        If no corpus: mean pairwise distance between ideas.
        """
        texts = [idea.content for idea in ideas if idea.content.strip()]
        if len(texts) < 1:
            return 0.0

        if corpus and len(corpus) > 0:
            return self._distance_from_corpus(texts, corpus)
        return self._mean_pairwise_distance(texts)

    def _distance_from_corpus(
        self, texts: list[str], corpus: list[str]
    ) -> float:
        """Mean distance of ideas from corpus (common solutions)."""
        all_docs = [tokenize(t) for t in texts + corpus]
        idf = compute_idf(all_docs)

        idea_vectors = [tf_idf_vector(tokenize(t), idf) for t in texts]
        corpus_vectors = [tf_idf_vector(tokenize(t), idf) for t in corpus]

        total_dist = 0.0
        count = 0
        for iv in idea_vectors:
            for cv in corpus_vectors:
                total_dist += cosine_distance(iv, cv)
                count += 1

        return total_dist / count if count > 0 else 0.0

    def _mean_pairwise_distance(self, texts: list[str]) -> float:
        """Mean pairwise cosine distance between ideas."""
        if len(texts) < 2:
            return 0.0

        tokenized = [tokenize(t) for t in texts]
        idf = compute_idf(tokenized)
        vectors = [tf_idf_vector(tok, idf) for tok in tokenized]

        total_dist = 0.0
        pair_count = 0
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                total_dist += cosine_distance(vectors[i], vectors[j])
                pair_count += 1

        return total_dist / pair_count if pair_count > 0 else 0.0

    def _compute_elaboration(self, ideas: list[DivergentIdea]) -> float:
        """Elaboration = proportion of ideas that are well-developed.

        Heuristic: ideas with >= ELABORATION_THRESHOLD words are "elaborated".
        Returns ratio of elaborated ideas to total.
        """
        if not ideas:
            return 0.0

        elaborated = sum(
            1 for idea in ideas
            if len(idea.content.split()) >= self.ELABORATION_THRESHOLD
        )
        return elaborated / len(ideas)
