

# Chunking strategy

- I chose a hybrid, structure-aware chunking strategy that balances semantic coherence with retrieval accuracy. Instead of relying on raw page boundaries or fixed-size splits alone, the system first groups content by logical units (such as headings or sections) extracted from the document parser, and then applies size-based chunking within those groups when necessary. This approach preserves meaning while keeping chunk sizes suitable for embedding models.

- The main trade-off in chunking is between chunk size and retrieval precision. Larger chunks provide more context, which helps the language model generate coherent answers, but they reduce retrieval accuracy because embeddings become less focused and may match unrelated queries. Smaller chunks improve retrieval precision and ranking quality but risk losing context or breaking semantic continuity. To balance this, chunks are constrained to a target size range and optionally overlapped, ensuring that important contextual information is not lost at boundaries.

- For documents parsed page-by-page, page boundaries are treated as soft constraints rather than strict limits. If a sentence or paragraph spans multiple pages, the system does not forcibly split it at the page break. Instead, text is merged based on paragraph structure and heading continuity. This prevents semantic fragmentation, which would otherwise degrade embedding quality and downstream question-answering performance.

- Overall, this strategy ensures that chunks remain semantically meaningful, retrieval-friendly, and traceable back to their source pages. It supports accurate grounding in responses while maintaining flexibility across different document formats and layouts, making it well-suited for a robust RAG pipeline.

# Re-Ranking Strategy

The system implements a custom re-ranking algorithm that improves upon pure vector similarity search. After retrieving initial candidates from the vector database, chunks are re-scored using a weighted combination of four factors:

- **Similarity (50%)**: Cosine similarity from vector search
- **Recency (20%)**: Newer documents are boosted over older versions
- **Hierarchy (20%)**: Important sections (Definitions, Overview, Policy Rules) receive higher scores
- **Adjacency (10%)**: Chunks with neighbors in the result set are boosted for contextual continuity

This multi-factor approach ensures that the most contextually relevant and useful chunks are surfaced for policy question-answering, not just those with the highest semantic similarity.

For detailed information about the reranking implementation, scoring components, and configuration options, see [RERANKING.md](./RERANKING.md).

