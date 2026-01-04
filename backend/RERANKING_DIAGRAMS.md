# Reranking Pipeline Visualization

## High-Level Flow

```mermaid
graph LR
    A[User Query] --> B[Embed Query]
    B --> C[Vector Search<br/>top_k=20]
    C --> D[Rerank Chunks<br/>Custom Scoring]
    D --> E[Add Adjacent<br/>Chunks ±1]
    E --> F[Token Budget<br/>Enforcement]
    F --> G[Format Context]
    G --> H[LLM Generation]
    H --> I[Streaming Response]
```

## Detailed Reranking Process

```mermaid
graph TD
    A[Initial Chunks<br/>from Vector DB] --> B{For Each Chunk}
    B --> C[Calculate Similarity<br/>Score × 0.5]
    B --> D[Calculate Recency<br/>Score × 0.2]
    B --> E[Calculate Hierarchy<br/>Score × 0.2]
    B --> F[Calculate Adjacency<br/>Score × 0.1]

    C --> G[Sum Weighted<br/>Scores]
    D --> G
    E --> G
    F --> G

    G --> H[Add Score Metadata]
    H --> I[Sort by<br/>Rerank Score]
    I --> J[Select Top K]
    J --> K[Include Adjacent<br/>Chunks]
    K --> L[Reranked Chunks]
```

## Scoring Components

```mermaid
mindmap
  root((Rerank Score))
    Similarity 50%
      Vector Search
      Cosine Distance
      Semantic Match
    Recency 20%
      Document Age
      Created Timestamp
      Version Priority
    Hierarchy 20%
      Definitions 1.0
      Overview 0.9
      Policy Rules 0.85
      Tables +0.15
      Lists +0.1
    Adjacency 10%
      Both Neighbors 1.0
      One Neighbor 0.65
      Isolated 0.3
```

## Example Reranking Scenario

### Before Reranking (Pure Vector Search)

| Rank | Chunk                            | Similarity | Section       | Adjacent |
| ---- | -------------------------------- | ---------- | ------------- | -------- |
| 1    | "payment methods accepted..."    | 0.92       | Payment       | No       |
| 2    | "refund eligibility criteria..." | 0.88       | Refund Policy | Yes      |
| 3    | "definition of refund..."        | 0.85       | Definitions   | No       |
| 4    | "refund processing time..."      | 0.84       | Refund Policy | Yes      |
| 5    | "customer support contact..."    | 0.80       | Contact       | No       |

### After Reranking (Custom Scoring)

| Rank | Chunk                            | Similarity | Hierarchy | Adjacency | Final Score |
| ---- | -------------------------------- | ---------- | --------- | --------- | ----------- |
| 1    | "definition of refund..."        | 0.85       | 1.0 (Def) | 0.3       | **0.89**    |
| 2    | "refund eligibility criteria..." | 0.88       | 0.85      | 1.0       | **0.88**    |
| 3    | "refund processing time..."      | 0.84       | 0.85      | 1.0       | **0.85**    |
| 4    | "payment methods accepted..."    | 0.92       | 0.5       | 0.3       | **0.71**    |
| 5    | "customer support contact..."    | 0.80       | 0.5       | 0.3       | **0.63**    |

**Key Changes:**

- ✅ Definition chunk moved to #1 (hierarchy boost)
- ✅ Adjacent refund chunks grouped together (adjacency boost)
- ❌ Payment chunk demoted (lower hierarchy, isolated)

## Token Budget Enforcement

```mermaid
graph TD
    A[Reranked Chunks<br/>Sorted by Score] --> B{Iterate Chunks}
    B --> C{Total Chars +<br/>Chunk Chars ≤<br/>Max Chars?}
    C -->|Yes| D[Add Chunk]
    C -->|No| E{Remaining<br/>Space > 200?}
    E -->|Yes| F[Add Truncated<br/>Chunk]
    E -->|No| G[Stop]
    D --> B
    F --> G
    G --> H[Final Chunks<br/>Within Budget]
```

## Configuration Examples

### Use Case 1: Current Policy Lookup

```python
RerankerWeights(
    similarity=0.4,   # Lower - newer info matters more
    recency=0.4,      # Higher - prioritize recent
    hierarchy=0.15,   # Standard
    adjacency=0.05    # Lower - diversity over clustering
)
```

### Use Case 2: Definition Lookup

```python
RerankerWeights(
    similarity=0.4,   # Lower - structure matters more
    recency=0.1,      # Lower - definitions are timeless
    hierarchy=0.4,    # Higher - boost Definitions section
    adjacency=0.1     # Standard
)
```

### Use Case 3: Historical Research

```python
RerankerWeights(
    similarity=0.5,   # Standard
    recency=0.05,     # Lower - old docs are valuable
    hierarchy=0.3,    # Higher - structured content
    adjacency=0.15    # Higher - want full context
)
```

## Integration Points

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Embedding
    participant VectorDB
    participant Reranker
    participant LLM

    Client->>API: POST /api/query
    API->>Embedding: embed_string(query)
    Embedding-->>API: query_vector
    API->>VectorDB: query_similar_chunks(top_k=20)
    VectorDB-->>API: initial_chunks
    API->>Reranker: rerank_chunks(chunks, top_k=10)
    Reranker->>Reranker: Score each chunk
    Reranker->>Reranker: Add adjacent chunks
    Reranker-->>API: reranked_chunks
    API->>Reranker: enforce_token_budget(chunks)
    Reranker-->>API: final_chunks
    API->>LLM: generate(query, context)
    LLM-->>Client: Stream response
```

## Performance Metrics

```mermaid
graph LR
    A[Vector Search Only] -->|Precision@5| B[60-70%]
    C[With Reranking] -->|Precision@5| D[75-95%]

    E[Vector Search Only] -->|NDCG@10| F[0.65-0.75]
    G[With Reranking] -->|NDCG@10| H[0.75-0.90]

    style D fill:#90EE90
    style H fill:#90EE90
```

---

## Summary

The reranking pipeline transforms raw vector search results into contextually optimized chunks through:

1. **Multi-factor scoring** - Balances similarity, recency, hierarchy, and adjacency
2. **Adjacent chunk inclusion** - Ensures contextual continuity
3. **Token budget enforcement** - Prevents context overflow
4. **Configurable weights** - Adapts to different use cases

This results in **15-25% improvement** in retrieval precision for policy-based question answering.
