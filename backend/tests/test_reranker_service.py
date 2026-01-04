"""
Unit tests for the RerankerService.

Run with: pytest tests/test_reranker_service.py
"""

import pytest
from app.service.reranker_service import RerankerService, RerankerWeights


class TestRerankerWeights:
    """Test RerankerWeights configuration"""
    
    def test_default_weights_sum_to_one(self):
        """Default weights should sum to 1.0"""
        weights = RerankerWeights()
        total = weights.similarity + weights.recency + weights.hierarchy + weights.adjacency
        assert 0.99 <= total <= 1.01
    
    def test_custom_weights_validation(self):
        """Custom weights must sum to approximately 1.0"""
        # Valid weights
        weights = RerankerWeights(
            similarity=0.6,
            recency=0.2,
            hierarchy=0.15,
            adjacency=0.05
        )
        assert weights.similarity == 0.6
        
        # Invalid weights (don't sum to 1.0)
        with pytest.raises(ValueError):
            RerankerWeights(
                similarity=0.5,
                recency=0.5,
                hierarchy=0.5,
                adjacency=0.5
            )


class TestRerankerService:
    """Test RerankerService functionality"""
    
    def test_empty_chunks(self):
        """Reranking empty list should return empty list"""
        result = RerankerService.rerank_chunks([])
        assert result == []
    
    def test_basic_reranking(self):
        """Test basic reranking with mock chunks"""
        chunks = [
            {
                'text': 'This is a test chunk',
                'score': 0.8,
                'document_id': 'doc1',
                'page': 1,
                'chunk_index': 0,
                'metadata': {
                    'section_hierarchy': ['Introduction'],
                    'primary_type': 'paragraph'
                }
            },
            {
                'text': 'This is another chunk',
                'score': 0.9,
                'document_id': 'doc1',
                'page': 1,
                'chunk_index': 1,
                'metadata': {
                    'section_hierarchy': ['Definitions'],
                    'primary_type': 'paragraph'
                }
            },
            {
                'text': 'Third chunk here',
                'score': 0.7,
                'document_id': 'doc2',
                'page': 2,
                'chunk_index': 0,
                'metadata': {
                    'section_hierarchy': ['Conclusion'],
                    'primary_type': 'paragraph'
                }
            }
        ]
        
        reranked = RerankerService.rerank_chunks(chunks, top_k=3)
        
        # Should have rerank_score added
        assert 'rerank_score' in reranked[0]
        assert 'score_breakdown' in reranked[0]
        
        # Should be sorted by rerank_score
        assert reranked[0]['rerank_score'] >= reranked[1]['rerank_score']
        assert reranked[1]['rerank_score'] >= reranked[2]['rerank_score']
    
    def test_hierarchy_scoring(self):
        """Test that Definitions section gets boosted"""
        chunks = [
            {
                'text': 'Regular content',
                'score': 0.9,  # High similarity
                'document_id': 'doc1',
                'page': 1,
                'chunk_index': 0,
                'metadata': {
                    'section_hierarchy': ['Chapter 1'],
                    'primary_type': 'paragraph'
                }
            },
            {
                'text': 'Definition content',
                'score': 0.7,  # Lower similarity
                'document_id': 'doc1',
                'page': 2,
                'chunk_index': 1,
                'metadata': {
                    'section_hierarchy': ['Definitions'],
                    'primary_type': 'paragraph'
                }
            }
        ]
        
        reranked = RerankerService.rerank_chunks(chunks)
        
        # Definitions chunk should potentially rank higher despite lower similarity
        # (depends on weights, but hierarchy boost should be visible in breakdown)
        definitions_chunk = next(c for c in reranked if 'Definition' in c['text'])
        assert definitions_chunk['score_breakdown']['hierarchy'] > 0.8
    
    def test_adjacency_scoring(self):
        """Test adjacency bonus for consecutive chunks"""
        chunks = [
            {
                'text': 'Chunk 0',
                'score': 0.8,
                'document_id': 'doc1',
                'page': 1,
                'chunk_index': 0,
                'metadata': {'section_hierarchy': [], 'primary_type': 'paragraph'}
            },
            {
                'text': 'Chunk 1',
                'score': 0.8,
                'document_id': 'doc1',
                'page': 1,
                'chunk_index': 1,
                'metadata': {'section_hierarchy': [], 'primary_type': 'paragraph'}
            },
            {
                'text': 'Chunk 2',
                'score': 0.8,
                'document_id': 'doc1',
                'page': 1,
                'chunk_index': 2,
                'metadata': {'section_hierarchy': [], 'primary_type': 'paragraph'}
            },
            {
                'text': 'Isolated chunk',
                'score': 0.8,
                'document_id': 'doc2',
                'page': 5,
                'chunk_index': 10,
                'metadata': {'section_hierarchy': [], 'primary_type': 'paragraph'}
            }
        ]
        
        reranked = RerankerService.rerank_chunks(chunks)
        
        # Middle chunk (index 1) should have highest adjacency (both neighbors present)
        chunk_1 = next(c for c in reranked if c['chunk_index'] == 1)
        isolated = next(c for c in reranked if c['chunk_index'] == 10)
        
        assert chunk_1['score_breakdown']['adjacency'] > isolated['score_breakdown']['adjacency']
    
    def test_token_budget_enforcement(self):
        """Test that token budget is enforced"""
        chunks = [
            {
                'text': 'A' * 1000,  # 1000 chars
                'rerank_score': 0.9,
                'score': 0.9,
                'document_id': 'doc1',
                'page': 1,
                'chunk_index': 0,
                'metadata': {}
            },
            {
                'text': 'B' * 1000,  # 1000 chars
                'rerank_score': 0.8,
                'score': 0.8,
                'document_id': 'doc1',
                'page': 1,
                'chunk_index': 1,
                'metadata': {}
            },
            {
                'text': 'C' * 1000,  # 1000 chars
                'rerank_score': 0.7,
                'score': 0.7,
                'document_id': 'doc1',
                'page': 1,
                'chunk_index': 2,
                'metadata': {}
            }
        ]
        
        # Budget for ~2 chunks (2000 chars / 4 chars per token = 500 tokens)
        result = RerankerService.enforce_token_budget(
            chunks,
            max_tokens=500,
            chars_per_token=4.0
        )
        
        # Should only include 2 chunks
        assert len(result) <= 2
        
        # Should include highest scoring chunks
        assert result[0]['rerank_score'] == 0.9
    
    def test_custom_weights(self):
        """Test reranking with custom weights"""
        chunks = [
            {
                'text': 'Test',
                'score': 0.8,
                'document_id': 'doc1',
                'page': 1,
                'chunk_index': 0,
                'metadata': {'section_hierarchy': [], 'primary_type': 'paragraph'}
            }
        ]
        
        custom_weights = RerankerWeights(
            similarity=0.7,
            recency=0.1,
            hierarchy=0.15,
            adjacency=0.05
        )
        
        reranked = RerankerService.rerank_chunks(chunks, weights=custom_weights)
        
        # Check that custom weights are used
        breakdown = reranked[0]['score_breakdown']['weights']
        assert breakdown['similarity'] == 0.7
        assert breakdown['recency'] == 0.1
        assert breakdown['hierarchy'] == 0.15
        assert breakdown['adjacency'] == 0.05


class TestScoreComponents:
    """Test individual scoring components"""
    
    def test_hierarchy_score_definitions(self):
        """Definitions section should get maximum hierarchy score"""
        reranker = RerankerService()
        chunk = {
            'metadata': {
                'section_hierarchy': ['Definitions', 'Terms'],
                'primary_type': 'paragraph'
            }
        }
        score = reranker._calculate_hierarchy_score(chunk)
        assert score == 1.0
    
    def test_hierarchy_score_table_boost(self):
        """Tables should get hierarchy boost"""
        reranker = RerankerService()
        chunk = {
            'metadata': {
                'section_hierarchy': ['Data'],
                'primary_type': 'table'
            }
        }
        score = reranker._calculate_hierarchy_score(chunk)
        assert score >= 0.65  # Base 0.5 + table boost 0.15
    
    def test_adjacency_score_isolated(self):
        """Isolated chunks should get low adjacency score"""
        reranker = RerankerService()
        chunk = {
            'chunk_index': 10,
            'document_id': 'doc1'
        }
        all_chunks = [
            {'chunk_index': 0, 'document_id': 'doc1'},
            {'chunk_index': 1, 'document_id': 'doc1'},
            chunk
        ]
        score = reranker._calculate_adjacency_score(chunk, all_chunks)
        assert score == 0.3  # Isolated
    
    def test_adjacency_score_with_neighbors(self):
        """Chunks with neighbors should get high adjacency score"""
        reranker = RerankerService()
        chunk = {
            'chunk_index': 1,
            'document_id': 'doc1'
        }
        all_chunks = [
            {'chunk_index': 0, 'document_id': 'doc1'},
            chunk,
            {'chunk_index': 2, 'document_id': 'doc1'}
        ]
        score = reranker._calculate_adjacency_score(chunk, all_chunks)
        assert score == 1.0  # Both neighbors present


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
