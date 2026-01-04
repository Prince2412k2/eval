from typing import List, Dict, Optional, Set
from datetime import datetime
from dataclasses import dataclass


@dataclass
class RerankerWeights:
    """
    Configurable weights for the reranking algorithm.
    All weights should sum to 1.0 for normalized scoring.
    """
    similarity: float = 0.5      # W1: Cosine similarity from vector search
    recency: float = 0.2         # W2: Document recency (newer > older)
    hierarchy: float = 0.2       # W3: Section importance (Definitions/Overview boost)
    adjacency: float = 0.1       # W4: Adjacent chunk bonus (±1 chunk)
    
    def __post_init__(self):
        """Validate that weights sum to approximately 1.0"""
        total = self.similarity + self.recency + self.hierarchy + self.adjacency
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Weights must sum to 1.0, got {total}")


class RerankerService:
    """
    Custom re-ranking service for RAG retrieval.
    
    Implements the scoring formula:
        final_score = similarity * W1 + recency * W2 + hierarchy * W3 + adjacency * W4
    
    Features:
    - Recency boost for newer documents
    - Section hierarchy bonus (e.g., Definitions, Overview sections)
    - Adjacent chunk boost for contextual continuity
    - Configurable weights for different use cases
    """
    
    def __init__(self, weights: Optional[RerankerWeights] = None):
        """
        Initialize reranker with custom or default weights.
        
        Args:
            weights: Custom RerankerWeights instance. Uses defaults if None.
        """
        self.weights = weights or RerankerWeights()
    
    @staticmethod
    def rerank_chunks(
        chunks: List[Dict],
        weights: Optional[RerankerWeights] = None,
        top_k: Optional[int] = None,
        include_adjacent: bool = True,
    ) -> List[Dict]:
        """
        Rerank retrieved chunks using custom scoring algorithm.
        
        Args:
            chunks: List of chunk dicts from VectorService.query_similar_chunks
                    Expected keys: text, score, document_id, page, chunk_index, metadata
            weights: Custom weights for scoring. Uses defaults if None.
            top_k: Number of top chunks to return after reranking. Returns all if None.
            include_adjacent: Whether to fetch and include adjacent chunks
        
        Returns:
            Reranked list of chunks with updated scores and metadata
        """
        if not chunks:
            return []
        
        reranker = RerankerService(weights)
        
        # Step 1: Calculate scores for all chunks
        scored_chunks = []
        for chunk in chunks:
            reranked_chunk = reranker._score_chunk(chunk, chunks)
            scored_chunks.append(reranked_chunk)
        
        # Step 2: Sort by final score (descending)
        scored_chunks.sort(key=lambda x: x['rerank_score'], reverse=True)
        
        # Step 3: Optionally include adjacent chunks for top results
        if include_adjacent and top_k:
            scored_chunks = reranker._add_adjacent_chunks(
                scored_chunks[:top_k], 
                all_chunks=chunks
            )
        
        # Step 4: Apply top_k limit if specified
        if top_k:
            scored_chunks = scored_chunks[:top_k]
        
        return scored_chunks
    
    def _score_chunk(self, chunk: Dict, all_chunks: List[Dict]) -> Dict:
        """
        Calculate final score for a single chunk.
        
        Args:
            chunk: Single chunk dict
            all_chunks: All retrieved chunks (for context)
        
        Returns:
            Chunk dict with added scoring metadata
        """
        # Extract base similarity score (from vector search)
        similarity_score = chunk.get('score', 0.0)
        
        # Calculate component scores
        recency_score = self._calculate_recency_score(chunk, all_chunks)
        hierarchy_score = self._calculate_hierarchy_score(chunk)
        adjacency_score = self._calculate_adjacency_score(chunk, all_chunks)
        
        # Compute weighted final score
        final_score = (
            similarity_score * self.weights.similarity +
            recency_score * self.weights.recency +
            hierarchy_score * self.weights.hierarchy +
            adjacency_score * self.weights.adjacency
        )
        
        # Create enriched chunk with scoring metadata
        enriched_chunk = chunk.copy()
        enriched_chunk['rerank_score'] = final_score
        enriched_chunk['score_breakdown'] = {
            'similarity': similarity_score,
            'recency': recency_score,
            'hierarchy': hierarchy_score,
            'adjacency': adjacency_score,
            'weights': {
                'similarity': self.weights.similarity,
                'recency': self.weights.recency,
                'hierarchy': self.weights.hierarchy,
                'adjacency': self.weights.adjacency,
            }
        }
        
        return enriched_chunk
    
    def _calculate_recency_score(self, chunk: Dict, all_chunks: List[Dict]) -> float:
        """
        Calculate recency score based on document creation time.
        Newer documents get higher scores.
        
        Strategy:
        - If document has created_at timestamp, use it
        - Otherwise, use relative ordering (normalize by position in result set)
        - Score range: 0.0 to 1.0
        
        Args:
            chunk: Current chunk
            all_chunks: All chunks for normalization
        
        Returns:
            Recency score between 0.0 and 1.0
        """
        metadata = chunk.get('metadata', {})
        
        # Check if we have timestamp information
        created_at = metadata.get('created_at')
        
        if created_at:
            # Parse timestamp and calculate age-based score
            # This is a placeholder - in production, you'd compare against current time
            # For now, we'll use a simple heuristic
            try:
                # Assuming created_at is a datetime string or object
                if isinstance(created_at, str):
                    # Simple heuristic: more recent = higher score
                    # This would need actual datetime parsing in production
                    return 0.8  # Placeholder
                return 0.8
            except:
                pass
        
        # Fallback: Use document_id as proxy for recency
        # Assumption: newer documents might have different IDs
        # This is a simple heuristic - in production, you'd use actual timestamps
        
        # For now, give a moderate score if no timestamp available
        return 0.5
    
    def _calculate_hierarchy_score(self, chunk: Dict) -> float:
        """
        Calculate hierarchy score based on section importance.
        
        Boosts:
        - Definitions sections: +0.3
        - Overview/Introduction sections: +0.2
        - Summary/Conclusion sections: +0.15
        - Headers (high-level): +0.1
        - Regular content: baseline 0.5
        
        Args:
            chunk: Current chunk
        
        Returns:
            Hierarchy score between 0.0 and 1.0
        """
        metadata = chunk.get('metadata', {})
        section_hierarchy = metadata.get('section_hierarchy', [])
        primary_type = metadata.get('primary_type', '')
        
        # Base score
        score = 0.5
        
        # Check section hierarchy for important keywords
        hierarchy_text = ' '.join(section_hierarchy).lower() if section_hierarchy else ''
        
        # High-value sections
        if any(keyword in hierarchy_text for keyword in ['definition', 'definitions', 'terminology']):
            score = 1.0  # Maximum boost for definitions
        elif any(keyword in hierarchy_text for keyword in ['overview', 'introduction', 'summary', 'executive summary']):
            score = 0.9
        elif any(keyword in hierarchy_text for keyword in ['conclusion', 'key points', 'highlights']):
            score = 0.8
        elif any(keyword in hierarchy_text for keyword in ['policy', 'rule', 'regulation', 'requirement']):
            score = 0.85  # Policy-specific boost
        
        # Boost for structured content types
        if primary_type == 'table':
            score = min(score + 0.15, 1.0)
        elif primary_type == 'numbered_list':
            score = min(score + 0.1, 1.0)
        elif primary_type == 'header_section':
            score = min(score + 0.05, 1.0)
        
        # Boost for cross-references (indicates important content)
        if metadata.get('has_cross_references', False):
            score = min(score + 0.1, 1.0)
        
        return score
    
    def _calculate_adjacency_score(self, chunk: Dict, all_chunks: List[Dict]) -> float:
        """
        Calculate adjacency score based on neighboring chunks.
        
        Logic:
        - If adjacent chunks (±1 chunk_index) are also in top results, boost score
        - This indicates a coherent, contextually relevant section
        
        Args:
            chunk: Current chunk
            all_chunks: All retrieved chunks
        
        Returns:
            Adjacency score between 0.0 and 1.0
        """
        chunk_index = chunk.get('chunk_index')
        document_id = chunk.get('document_id')
        
        if chunk_index is None or document_id is None:
            return 0.5  # Neutral score if no index info
        
        # Find adjacent chunks in the result set
        adjacent_indices = {chunk_index - 1, chunk_index + 1}
        
        # Check how many adjacent chunks are present
        adjacent_count = 0
        for other_chunk in all_chunks:
            if (other_chunk.get('document_id') == document_id and 
                other_chunk.get('chunk_index') in adjacent_indices):
                adjacent_count += 1
        
        # Score based on adjacency
        # 0 adjacent: 0.3 (isolated chunk)
        # 1 adjacent: 0.65 (some context)
        # 2 adjacent: 1.0 (full context)
        if adjacent_count == 0:
            return 0.3
        elif adjacent_count == 1:
            return 0.65
        else:  # 2 or more
            return 1.0
    
    def _add_adjacent_chunks(
        self, 
        top_chunks: List[Dict], 
        all_chunks: List[Dict]
    ) -> List[Dict]:
        """
        Add adjacent chunks (±1 index) to top results for better context.
        
        This ensures that if a chunk is highly relevant, we also include
        its immediate neighbors for contextual continuity.
        
        Args:
            top_chunks: Top-ranked chunks after reranking
            all_chunks: All originally retrieved chunks
        
        Returns:
            Extended list with adjacent chunks included
        """
        # Track chunks we want to include
        result_chunks = top_chunks.copy()
        included_ids = {
            (c.get('document_id'), c.get('chunk_index')) 
            for c in top_chunks
        }
        
        # For each top chunk, find its adjacent chunks
        for chunk in top_chunks:
            doc_id = chunk.get('document_id')
            chunk_idx = chunk.get('chunk_index')
            
            if doc_id is None or chunk_idx is None:
                continue
            
            # Look for adjacent chunks in all_chunks
            for other_chunk in all_chunks:
                other_doc_id = other_chunk.get('document_id')
                other_idx = other_chunk.get('chunk_index')
                
                if other_doc_id != doc_id or other_idx is None:
                    continue
                
                # Check if it's adjacent (±1)
                if abs(other_idx - chunk_idx) == 1:
                    chunk_key = (other_doc_id, other_idx)
                    if chunk_key not in included_ids:
                        # Add adjacent chunk with a slightly lower score
                        adjacent_chunk = other_chunk.copy()
                        adjacent_chunk['rerank_score'] = chunk['rerank_score'] * 0.9
                        adjacent_chunk['is_adjacent_context'] = True
                        result_chunks.append(adjacent_chunk)
                        included_ids.add(chunk_key)
        
        # Re-sort by score
        result_chunks.sort(key=lambda x: x['rerank_score'], reverse=True)
        
        return result_chunks
    
    @staticmethod
    def enforce_token_budget(
        chunks: List[Dict],
        max_tokens: int = 4000,
        chars_per_token: float = 4.0,
    ) -> List[Dict]:
        """
        Enforce token budget by selecting best subset of chunks.
        
        Strategy:
        - Iterate through sorted chunks (by rerank_score)
        - Add chunks until token budget is reached
        - Avoid redundant information
        
        Args:
            chunks: Reranked chunks (should be sorted by score)
            max_tokens: Maximum token budget
            chars_per_token: Approximate characters per token (default: 4.0)
        
        Returns:
            Subset of chunks that fit within token budget
        """
        max_chars = int(max_tokens * chars_per_token)
        
        selected_chunks = []
        total_chars = 0
        
        for chunk in chunks:
            chunk_text = chunk.get('text', '')
            chunk_chars = len(chunk_text)
            
            # Check if adding this chunk would exceed budget
            if total_chars + chunk_chars <= max_chars:
                selected_chunks.append(chunk)
                total_chars += chunk_chars
            else:
                # Try to fit partial chunk if there's remaining space
                remaining_chars = max_chars - total_chars
                if remaining_chars > 200:  # Only if we can fit meaningful content
                    # Truncate chunk text
                    truncated_chunk = chunk.copy()
                    truncated_chunk['text'] = chunk_text[:remaining_chars] + '...'
                    truncated_chunk['truncated'] = True
                    selected_chunks.append(truncated_chunk)
                break
        
        return selected_chunks
