# Re-Ranking Strategy Documentation

## Scoring Formula

```
final_score = similarity × W1 + recency × W2 + hierarchy × W3 + adjacency × W4
```

### Default Weights

- **W1 (Similarity)**: 0.5 - Cosine similarity from vector search
- **W2 (Recency)**: 0.2 - Document recency boost
- **W3 (Hierarchy)**: 0.2 - Section importance boost
- **W4 (Adjacency)**: 0.1 - Adjacent chunk bonus

**Total**: 1.0 (normalized)

---

## Scoring Components

### 1. Similarity Score (W1 = 0.5)

**Source**: Cosine similarity from Qdrant vector search

**Rationale**: This is the foundation of semantic search and should carry the most weight. It ensures that chunks with high semantic relevance to the query are prioritized.

**Range**: 0.0 to 1.0 (from vector DB)

---

### 2. Recency Score (W2 = 0.2)

**Purpose**: Boost newer documents over older ones

**Rationale**: In policy contexts, newer documents often supersede older versions. Recent policies are more likely to be currently applicable and accurate.

**Implementation**:

- Uses document `created_at` timestamp when available
- Falls back to heuristic scoring if timestamps unavailable
- Newer documents receive scores closer to 1.0

**Range**: 0.0 to 1.0

**Example**:

```
Document from 2024: score = 0.9
Document from 2022: score = 0.6
Document from 2020: score = 0.4
```

---

### 3. Hierarchy Score (W3 = 0.2)

**Purpose**: Boost chunks from important sections (Definitions, Overview, etc.)

**Rationale**: Certain sections contain foundational information that's critical for understanding policies:

- **Definitions**: Essential for interpreting policy language correctly
- **Overview/Introduction**: Provides high-level context
- **Policy Rules**: Core requirements and regulations

**Scoring Rules**:

| Section Type              | Score | Rationale                            |
| ------------------------- | ----- | ------------------------------------ |
| Definitions/Terminology   | 1.0   | Critical for accurate interpretation |
| Overview/Introduction     | 0.9   | Provides essential context           |
| Policy/Rules/Requirements | 0.85  | Core policy content                  |
| Conclusion/Summary        | 0.8   | Synthesized key points               |
| Regular content           | 0.5   | Baseline                             |

**Additional Boosts**:

- **Tables**: +0.15 (structured, high-density information)
- **Numbered lists**: +0.1 (often contain rules or procedures)
- **Cross-references**: +0.1 (indicates important interconnected content)
- **Headers**: +0.05 (section markers)

**Range**: 0.0 to 1.0

---

### 4. Adjacency Score (W4 = 0.1)

**Purpose**: Boost chunks whose neighbors are also in top results

**Rationale**: If multiple consecutive chunks from the same document are retrieved, it indicates a coherent, contextually rich section that's highly relevant to the query. This promotes contextual continuity.

**Scoring Logic**:

| Adjacent Chunks Present | Score | Interpretation                 |
| ----------------------- | ----- | ------------------------------ |
| 0 (isolated chunk)      | 0.3   | Potentially fragmented context |
| 1 (one neighbor)        | 0.65  | Some contextual continuity     |
| 2+ (both neighbors)     | 1.0   | Strong contextual coherence    |

**Range**: 0.0 to 1.0

**Example**:

```
Query: "What is the refund policy?"

Retrieved chunks:
- Chunk 45: "Refund Policy Overview" (has neighbors 44, 46)
- Chunk 46: "Refund eligibility criteria" (has neighbor 45)
- Chunk 78: "Payment methods" (isolated)

→ Chunks 45 and 46 get adjacency boost
→ Chunk 78 gets lower adjacency score
```

---

## Weight Justification

### Why These Specific Weights?

1. **Similarity (50%)**: Dominant factor because semantic relevance is fundamental. Without high similarity, other factors are less meaningful.

2. **Recency (20%)**: Significant but not dominant. Older documents can still be valuable for historical context or if they contain unique information not in newer versions.

3. **Hierarchy (20%)**: Equal to recency because section importance is crucial in policy documents. A definition from an older document might be more valuable than a tangential mention in a newer one.

4. **Adjacency (10%)**: Smallest weight because it's a secondary signal. It helps with context but shouldn't override semantic relevance.

### Trade-offs

- **Higher similarity weight**: Ensures we don't over-correct away from semantic relevance
- **Balanced recency/hierarchy**: Allows flexibility for both temporal and structural importance
- **Lower adjacency weight**: Prevents over-clustering of consecutive chunks at the expense of diverse, relevant information

---

## Advanced Features

### 1. Adjacent Chunk Inclusion

When `include_adjacent=True`, the reranker automatically fetches chunks immediately before and after (±1 index) top-ranked chunks. This ensures:

- Complete context for partial information
- Continuity across chunk boundaries
- Better handling of split sentences or concepts

**Implementation**:

```python
reranked_chunks = RerankerService.rerank_chunks(
    chunks=initial_chunks,
    top_k=10,
    include_adjacent=True  # Adds ±1 chunks
)
```

### 2. Token Budget Enforcement

Prevents context overflow by selecting the best subset of chunks that fit within the LLM's context window.

**Strategy**:

- Iterate through reranked chunks (highest score first)
- Add chunks until token budget is reached
- Optionally truncate last chunk if partial content is meaningful

**Implementation**:

```python
final_chunks = RerankerService.enforce_token_budget(
    chunks=reranked_chunks,
    max_tokens=4000,
    chars_per_token=4.0  # Approximate ratio
)
```

### 3. Score Transparency

Each reranked chunk includes detailed scoring metadata:

```json
{
  "text": "...",
  "rerank_score": 0.87,
  "score_breakdown": {
    "similarity": 0.92,
    "recency": 0.8,
    "hierarchy": 1.0,
    "adjacency": 0.65,
    "weights": {
      "similarity": 0.5,
      "recency": 0.2,
      "hierarchy": 0.2,
      "adjacency": 0.1
    }
  }
}
```

This enables:

- Debugging and analysis
- A/B testing different weight configurations
- User transparency (showing why certain chunks were selected)

---

## Integration Pipeline

```
Query → Embed → Vector Search (top 20) → Rerank (top 10) → Token Budget → LLM
```

1. **Embed query**: Convert to 384-dim vector
2. **Vector search**: Retrieve 20 candidates (over-fetch for reranking)
3. **Rerank**: Apply custom scoring, select top 10
4. **Add adjacent**: Include ±1 chunks for context
5. **Enforce budget**: Trim to fit token limit
6. **Format context**: Convert to LLM prompt
7. **Generate response**: Stream answer with citations

---

## Configuration

### Custom Weights

```python
from app.service.reranker_service import RerankerWeights, RerankerService

# Custom weights for specific use cases
custom_weights = RerankerWeights(
    similarity=0.6,   # Emphasize semantic match
    recency=0.1,      # De-emphasize recency
    hierarchy=0.25,   # Boost important sections
    adjacency=0.05    # Minimal adjacency
)

reranked = RerankerService.rerank_chunks(
    chunks=chunks,
    weights=custom_weights
)
```

### Use Case Examples

**Historical Research** (older documents are valuable):

```python
weights = RerankerWeights(
    similarity=0.5,
    recency=0.05,  # Low recency
    hierarchy=0.3,
    adjacency=0.15
)
```

**Current Policy Lookup** (newest info critical):

```python
weights = RerankerWeights(
    similarity=0.4,
    recency=0.4,   # High recency
    hierarchy=0.15,
    adjacency=0.05
)
```

**Definition Lookup** (hierarchy matters most):

```python
weights = RerankerWeights(
    similarity=0.4,
    recency=0.1,
    hierarchy=0.4,  # High hierarchy
    adjacency=0.1
)
```

---

## Performance Considerations

### Computational Cost

- **Vector search**: O(log n) with HNSW index (Qdrant)
- **Reranking**: O(k) where k = number of retrieved chunks (typically 20)
- **Total overhead**: Minimal (~10-50ms for 20 chunks)

### Accuracy Improvements

Based on typical RAG benchmarks, custom reranking can improve:

- **Precision@5**: +15-25% over pure vector search
- **NDCG@10**: +10-20% improvement
- **User satisfaction**: Significant improvement in policy Q&A tasks

---

## Future Enhancements

1. **Cross-encoder reranking**: Use a dedicated reranking model (e.g., `cross-encoder/ms-marco-MiniLM-L-6-v2`)
2. **Query-dependent weights**: Adjust weights based on query type
3. **Document versioning**: Explicit handling of `supersedes` relationships
4. **User feedback loop**: Learn optimal weights from user interactions
5. **Semantic caching**: Cache reranked results for common queries

---

## Testing & Validation

### Unit Tests

Test individual scoring components:

```python
def test_hierarchy_score():
    chunk = {
        'metadata': {
            'section_hierarchy': ['Definitions', 'Terms'],
            'primary_type': 'table'
        }
    }
    score = reranker._calculate_hierarchy_score(chunk)
    assert score >= 0.9  # Should get high score
```

### Integration Tests

Test full reranking pipeline:

```python
def test_rerank_pipeline():
    chunks = [...]  # Mock chunks
    reranked = RerankerService.rerank_chunks(chunks, top_k=5)
    assert len(reranked) <= 5
    assert reranked[0]['rerank_score'] >= reranked[-1]['rerank_score']
```

### A/B Testing

Compare different weight configurations on real queries:

- Measure answer quality
- Track citation accuracy
- Monitor user feedback

---

## Conclusion

This custom reranking system balances multiple factors to surface the most relevant, contextually appropriate chunks for policy question-answering. The configurable weights allow adaptation to different use cases while maintaining transparency and debuggability.

**Key Benefits**:
✅ Improved retrieval precision
✅ Better handling of policy-specific content
✅ Contextual continuity through adjacency
✅ Transparent, explainable scoring
✅ Configurable for different use cases
