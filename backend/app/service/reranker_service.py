from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class RerankerWeights:
    """Configurable weights for reranking (must sum to 1.0)"""

    similarity: float = 0.6
    recency: float = 0.15
    hierarchy: float = 0.15
    adjacency: float = 0.1

    def __post_init__(self) -> None:
        """Validate weights sum to approximately 1.0"""
        total = self.similarity + self.recency + self.hierarchy + self.adjacency
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Weights must sum to ~1.0, got {total}")


class RerankerService:
    """
    Simple RAG reranker combining vector similarity with document metadata.

    Scoring formula:
        final_score = similarity * W1 + recency * W2 + hierarchy * W3 + adjacency * W4

    Features:
    - Vector similarity scoring
    - Recency boost for newer documents
    - Section hierarchy importance
    - Adjacency context scoring
    - Automatic adjacent chunk inclusion for high-scoring results
    """

    def __init__(self, weights: Optional[RerankerWeights] = None) -> None:
        """
        Initialize reranker with custom or default weights.

        Args:
            weights: Custom RerankerWeights instance. Uses defaults if None.
        """
        self.weights = weights or RerankerWeights()

    def rerank(
        self,
        chunks: List[Dict],
        top_k: Optional[int] = None,
        score_threshold: float = 0.7,
    ) -> List[Dict]:
        """
        Rerank chunks and optionally return top K results.

        High-scoring chunks automatically include adjacent chunks for context.

        Args:
            chunks: List of chunk dicts with keys: text, score, document_id,
                   chunk_index, metadata
            top_k: Number of top chunks to return (None = return all)
            score_threshold: If chunk score >= threshold, include adjacent chunks

        Returns:
            Sorted list of chunks with 'rerank_score' added
        """
        if not chunks:
            return []

        # Step 1: Score all chunks
        scored = [self._score_chunk(chunk, chunks) for chunk in chunks]

        # Step 2: Sort by final score descending
        scored.sort(key=lambda x: x["rerank_score"], reverse=True)

        # Step 3: Add adjacent chunks for high-scoring results
        result = self._add_adjacent_chunks(scored, chunks, score_threshold)

        # Step 4: Apply top_k limit if specified
        return result[:top_k] if top_k else result

    # ========================================================================
    # Scoring Methods
    # ========================================================================

    def _score_chunk(self, chunk: Dict, all_chunks: List[Dict]) -> Dict:
        """
        Calculate composite score for a single chunk.

        Args:
            chunk: Single chunk to score
            all_chunks: All chunks for context (recency normalization)

        Returns:
            Chunk dict with added 'rerank_score' field
        """
        similarity = chunk.get("score", 0.0)
        recency = self._recency_score(chunk, all_chunks)
        hierarchy = self._hierarchy_score(chunk)
        adjacency = self._adjacency_score(chunk, all_chunks)

        final_score = (
            similarity * self.weights.similarity
            + recency * self.weights.recency
            + hierarchy * self.weights.hierarchy
            + adjacency * self.weights.adjacency
        )

        enriched = chunk.copy()
        enriched["rerank_score"] = final_score

        return enriched

    def _recency_score(self, chunk: Dict, all_chunks: List[Dict]) -> float:
        """
        Score based on document recency (0.0-1.0).

        Normalizes timestamps across all chunks. Returns neutral 0.5 if
        timestamps are missing or cannot be normalized.

        Args:
            chunk: Current chunk
            all_chunks: All chunks for timestamp range calculation

        Returns:
            Recency score between 0.0 (oldest) and 1.0 (newest)
        """
        created_at = chunk.get("metadata", {}).get("created_at")

        if not isinstance(created_at, (int, float)):
            return 0.5  # Neutral if missing

        # Get range of timestamps from all chunks
        timestamps = [
            c.get("metadata", {}).get("created_at")
            for c in all_chunks
            if isinstance(c.get("metadata", {}).get("created_at"), (int, float))
        ]

        if len(timestamps) < 2:
            return 0.5  # Can't normalize with < 2 timestamps

        min_ts, max_ts = min(timestamps), max(timestamps)
        if min_ts == max_ts:
            return 0.5

        score = (created_at - min_ts) / (max_ts - min_ts)
        return max(0.0, min(score, 1.0))

    def _hierarchy_score(self, chunk: Dict) -> float:
        """
        Score based on section importance (0.0-1.0).

        Boosts important sections like definitions, overviews, and structured
        content types like tables and lists.

        Args:
            chunk: Current chunk

        Returns:
            Hierarchy score between 0.0 and 1.0
        """
        metadata = chunk.get("metadata", {})
        section = " ".join(metadata.get("section_hierarchy", [])).lower()
        primary_type = metadata.get("primary_type", "")

        score = 0.5  # Baseline

        # Boost important sections
        if any(kw in section for kw in ["definition", "terminology"]):
            score = 1.0
        elif any(kw in section for kw in ["overview", "introduction", "summary"]):
            score = 0.9
        elif any(kw in section for kw in ["conclusion", "key points"]):
            score = 0.8

        # Boost structured content
        if primary_type == "table":
            score = min(score + 0.1, 1.0)
        elif primary_type == "numbered_list":
            score = min(score + 0.05, 1.0)

        return score

    def _adjacency_score(self, chunk: Dict, all_chunks: List[Dict]) -> float:
        """
        Score based on adjacent chunks being present (0.0-1.0).

        Rewards chunks that have neighbors in the result set, indicating
        they're part of a coherent contextual section.

        Args:
            chunk: Current chunk
            all_chunks: All chunks in result set

        Returns:
            Adjacency score: 0.3 (isolated), 0.65 (1 neighbor), 1.0 (2 neighbors)
        """
        chunk_index = chunk.get("chunk_index")
        document_id = chunk.get("document_id")

        if chunk_index is None or document_id is None:
            return 0.3  # No adjacency info

        # Count adjacent chunks (ñ1 index) in result set
        adjacent_count = 0
        for other in all_chunks:
            if (
                other.get("document_id") == document_id
                and abs(other.get("chunk_index", -999) - chunk_index) == 1
            ):
                adjacent_count += 1

        # Return score based on context availability
        if adjacent_count == 0:
            return 0.3  # Isolated
        elif adjacent_count == 1:
            return 0.65  # Some context
        else:
            return 1.0  # Full context

    # ========================================================================
    # Adjacent Chunk Inclusion
    # ========================================================================

    def _add_adjacent_chunks(
        self,
        scored_chunks: List[Dict],
        all_chunks: List[Dict],
        threshold: float,
    ) -> List[Dict]:
        """
        For chunks scoring above threshold, automatically include adjacent chunks.
        This ensures high-quality results include their immediate neighbors for
        better contextual continuity without polluting results with low-scoring
        chunks.

        Args:
            scored_chunks: Already scored and sorted chunks
            all_chunks: Original full chunk list
            threshold: Minimum score to trigger adjacent chunk inclusion

        Returns:
            Extended list with adjacent chunks included and re-sorted
        """
        result = scored_chunks.copy()
        included_keys = {
            (c.get("document_id"), c.get("chunk_index")) for c in result
        }

        # For each high-scoring chunk, find and add its neighbors
        for chunk in scored_chunks:
            if chunk["rerank_score"] < threshold:
                continue

            doc_id = chunk.get("document_id")
            chunk_idx = chunk.get("chunk_index")

            if doc_id is None or chunk_idx is None:
                continue

            # Find previous and next chunks
            for other in all_chunks:
                if other.get("document_id") != doc_id:
                    continue

                other_idx = other.get("chunk_index")
                if other_idx is None:
                    continue

                # Check if it's adjacent (ñ1)
                if abs(other_idx - chunk_idx) == 1:
                    key = (doc_id, other_idx)
                    if key not in included_keys:
                        adjacent = other.copy()
                        adjacent["rerank_score"] = chunk["rerank_score"] * 0.85
                        adjacent["is_adjacent"] = True
                        result.append(adjacent)
                        included_keys.add(key)

        # Re-sort by score
        result.sort(key=lambda x: x["rerank_score"], reverse=True)
        return result
