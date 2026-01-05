# Policy Chatbot – Design Documentation

## Table of Contents

1. [Chunking Strategy](#chunking-strategy)
2. [Re-Ranking Weights Justification](#re-ranking-weights-justification)
3. [Citation Handling](#citation-handling)
4. [Cross-Reference UX Decision](#cross-reference-ux-decision)
5. [Embedding Model Choice](#embedding-model-choice)
6. [Chunk Size Trade-offs](#chunk-size-trade-offs)
7. [Database Schema](#database-schema)
8. [Failure Mode Analysis](#failure-mode-analysis)

---

## Chunking Strategy

### Overview (250 words)

The system implements a **hybrid, structure-aware semantic chunking strategy** that intelligently balances semantic coherence with retrieval accuracy. Rather than relying solely on fixed-size splits or arbitrary page boundaries, the chunker first analyzes the document structure to identify logical units such as headings, sections, tables, and numbered lists. These semantic units are then grouped into chunks while respecting their inherent boundaries and meaning.

The implementation provides two chunking strategies via a factory pattern:

1. **NaiveChunker**: A baseline sliding-window approach with fixed chunk sizes (1000 chars) and overlap (100 chars). This serves as a fallback and comparison baseline.

2. **SemanticChunker** (default): An advanced chunker that:
   - Parses markdown into semantic units (headers, paragraphs, tables, lists)
   - Detects "atomic" content that should never be split (tables, numbered lists, cross-referenced items)
   - Groups units into chunks while respecting max/min size constraints (max: 1000, min: 100 chars)
   - Maintains overlap (150 chars) by including previous chunk context, prioritizing section headers
   - Preserves section hierarchy metadata for downstream re-ranking

**Key Edge Cases Handled**:
- **Tables**: Treated as atomic units to preserve structured data integrity
- **Numbered Lists**: Kept intact to maintain procedural or rule-based sequences
- **Cross-References**: Items referencing other sections are kept together with context
- **Page Boundaries**: Treated as soft constraints; text is not forcibly split at page breaks
- **Headers with Content**: Headers are kept with at least 200 characters of following content

This approach ensures chunks remain semantically meaningful, retrieval-friendly, and traceable back to source pages, making it ideal for policy document question-answering where context and accuracy are critical.

---

## Re-Ranking Weights Justification

### Scoring Formula (200 words)

After initial vector similarity search retrieves the top 20 candidates, a custom re-ranking algorithm re-scores chunks using a weighted combination of four factors:

```
final_score = similarity × 0.5 + recency × 0.2 + hierarchy × 0.2 + adjacency × 0.1
```

**Weight Justification**:

1. **Similarity (50%)**: Cosine similarity from vector search remains the dominant factor because semantic relevance is fundamental. Without high similarity to the query, other factors become less meaningful. This ensures we don't over-correct away from what the user actually asked.

2. **Recency (20%)**: In policy contexts, newer documents often supersede older versions. A 20% weight provides significant boost to recent policies without completely overriding semantic relevance. This is crucial for compliance scenarios where outdated policies could lead to incorrect answers.

3. **Hierarchy (20%)**: Section importance is equally weighted with recency because certain sections (Definitions, Overview, Policy Rules) contain foundational information critical for accurate interpretation. A definition from an older document might be more valuable than a tangential mention in a newer one.

4. **Adjacency (10%)**: The smallest weight because it's a secondary signal. When consecutive chunks from the same document appear in results, it indicates a coherent, contextually rich section. However, this shouldn't override semantic relevance or cause over-clustering at the expense of diverse information.

**Trade-offs**: This balanced approach ensures high precision while maintaining contextual continuity and temporal relevance, optimizing for the specific needs of policy-based question answering.

---

## Citation Handling

### Dual-LLM Architecture (130 words)

The citation system uses a **parallel dual-LLM approach** to provide transparent source attribution without sacrificing response latency:

**Architecture**:
- **Citation Extraction** (Fast Model): `llama-3.1-8b-instant` runs in parallel with the main response, extracting structured citations in JSON format. Cost: ~$0.0001 per query.
- **Main Response** (Streaming): `openai/gpt-oss-120b` generates the natural language answer with streaming for better UX.

**Total latency**: ~2-3 seconds (parallel execution means we wait for the slower of the two, not the sum).

**Citation Types**:
1. **Direct Quote**: Exact wording from source (confidence: 1.0)
2. **Paraphrase**: Restated information maintaining meaning (confidence: 0.7-0.99)
3. **Inference**: Logical conclusion drawn from source (confidence: 0.5-0.8)

Each citation includes document name, page number, section hierarchy, a 50-200 character text span from the source, and a confidence score. The verification API (`POST /api/verify-citation`) allows clients to validate citation accuracy by comparing claims against source chunks.

---

## Cross-Reference UX Decision

### Approach (140 words)

The system takes a **transparent, non-intrusive approach** to cross-references within policy documents:

**Detection**: During semantic chunking, the system detects cross-references using pattern matching (e.g., "See item 3", "as mentioned in section 2.1", "refer to above"). These chunks are marked with `has_cross_reference: true` in metadata.

**Handling Strategy**:
1. **Automatic Context Inclusion**: Cross-referenced chunks are kept together with surrounding context during chunking to maintain coherence
2. **Metadata Tracking**: Cross-references are tracked in chunk metadata but not automatically expanded
3. **User Control**: The system does NOT automatically fetch and include referenced documents without user awareness, preventing context pollution and unexpected token usage

**Rationale**: Auto-including cross-referenced documents could lead to:
- Exponential context growth (document A references B, which references C...)
- Irrelevant information diluting the response
- Unexpected costs and latency

Instead, if a cross-reference appears critical, the LLM can mention it in the response, allowing users to explicitly request additional documents.

---

## Embedding Model Choice

### Model: BAAI/bge-small-en-v1.5

**Rationale**:

1. **Performance**: BGE (BAAI General Embedding) models are state-of-the-art for semantic search, consistently ranking at the top of the MTEB (Massive Text Embedding Benchmark) leaderboard for retrieval tasks.

2. **Size vs. Quality**: The "small" variant produces 384-dimensional embeddings, offering an excellent balance:
   - **Quality**: Competitive with larger models on most tasks
   - **Speed**: Fast inference (~10-20ms per query on CPU)
   - **Storage**: Smaller vector size means lower storage costs in Qdrant
   - **Latency**: Faster similarity search due to smaller dimensionality

3. **Domain Suitability**: BGE models are trained on diverse corpora including technical and formal documents, making them well-suited for policy text.

4. **Open Source**: No API costs, runs locally via FastEmbed, ensuring data privacy and eliminating external dependencies.

**Alternatives Considered**:
- **OpenAI text-embedding-3-small**: Higher quality but requires API calls (cost + latency + privacy concerns)
- **all-MiniLM-L6-v2**: Faster but lower quality for complex policy language
- **bge-large-en-v1.5**: Higher quality (768-dim) but 2-3x slower and larger storage footprint

---

## Chunk Size Trade-offs

### Configuration: Max 1000, Min 100, Overlap 150 chars

**The Fundamental Trade-off**:

Chunk size represents a critical balance between **retrieval precision** and **contextual completeness**:

**Larger Chunks (1500+ chars)**:
- ✅ More context for LLM to generate coherent answers
- ✅ Less risk of splitting related information
- ❌ Lower retrieval precision (embeddings become less focused)
- ❌ May include irrelevant information, diluting similarity scores
- ❌ Fewer chunks fit in context window

**Smaller Chunks (500- chars)**:
- ✅ Higher retrieval precision (embeddings are more focused)
- ✅ Better ranking quality (less noise per chunk)
- ❌ Risk of losing context across chunk boundaries
- ❌ May split semantically related content
- ❌ Requires more chunks to answer complex queries

**Our Choice (1000 chars max)**:

This represents the **sweet spot** for policy documents:
- **~200-250 words**: Enough for a complete paragraph or policy rule
- **Fits most tables and lists**: Reduces forced splits of structured content
- **Optimal for 384-dim embeddings**: BGE-small performs best with this granularity
- **Context window efficiency**: With 4000-token budget, we can include 10-15 chunks

**Overlap (150 chars)**:
- Prevents information loss at boundaries
- Ensures sentences split across chunks appear in both
- Prioritizes including section headers for context

**Min Size (100 chars)**:
- Prevents tiny, low-information chunks
- Ensures each chunk has meaningful content for embedding

---

## Database Schema

### Architecture Overview

The system uses a **hybrid storage architecture** combining PostgreSQL (relational data) and Qdrant (vector search):

#### PostgreSQL Schema (via SQLAlchemy)

**1. Documents Table**
```sql
- hash (PK, String): SHA-256 hash for deduplication
- title (String): Document filename
- mime_type (String): File type (application/pdf, etc.)
- created_at (DateTime): Upload timestamp
- file_size (Integer): Bytes
- page_count (Integer): Total pages
- chunk_count (Integer): Total chunks generated
- status (String): "indexed" | "processing" | "failed"
```

**2. Conversations Table**
```sql
- id (UUID, PK): Unique conversation ID
- user_id (UUID): Optional user identifier
- title (String): Auto-generated or user-set title
- created_at, updated_at (DateTime): Timestamps
- documents_discussed (Array<String>): Document hashes referenced
- topics_covered (Array<String>): Extracted topics
```

**3. Messages Table**
```sql
- id (UUID, PK): Unique message ID
- conversation_id (UUID, FK): Links to conversation
- role (Enum): "user" | "assistant" | "system"
- content (Text): Message text
- created_at (DateTime): Timestamp
- sources (Array<String>): Document IDs used for answer
- citations (JSONB): Structured citation data
- extra_metadata (JSONB): Additional context
```

**4. TokenUsage Table**
```sql
- id (UUID, PK)
- conversation_id (UUID, FK)
- model (String): LLM model name
- prompt_tokens, completion_tokens, total_tokens (Integer)
- cost_usd (Float): Estimated cost
- created_at (DateTime)
```

#### Qdrant Vector Database

**Collection: "documents"**
- **Vector Config**: 384 dimensions, COSINE distance
- **Payload Schema**:
  ```json
  {
    "text": "chunk content",
    "document_id": "hash",
    "page": 3,
    "chunk_index": 12,
    "metadata": {
      "section_hierarchy": ["Policy Rules", "Refunds"],
      "primary_type": "table",
      "has_cross_reference": false,
      "is_atomic": true
    },
    "owner_id": "uuid"
  }
  ```
- **Indexes**: `owner_id` (UUID), `document_id` (keyword)

**Design Rationale**:
- PostgreSQL handles relational data (conversations, documents, citations)
- Qdrant optimized for high-speed vector similarity search
- JSONB fields provide flexibility for evolving metadata
- UUID primary keys enable distributed systems and avoid collisions

---

## Failure Mode Analysis

### Critical Failure Scenarios and Mitigations

#### 1. **Contradictory Policies (v1 vs v2)**

**Failure**: User uploads "Refund Policy v1.pdf" (30-day returns) and "Refund Policy v2.pdf" (14-day returns). System retrieves chunks from both, LLM generates conflicting answer.

**Current Mitigation**:
- Recency scoring (20% weight) boosts newer documents
- Document `created_at` timestamp used for ordering

**Gaps**:
- No explicit version detection or `supersedes` relationship
- Users must manually delete old versions

**Future Enhancement**:
- Implement `supersedes` field in Document model
- Detect version patterns in filenames (v1, v2, 2024-01-01)
- Warn users when uploading potentially superseding documents

---

#### 2. **Partial Information / "Not Specified"**

**Failure**: User asks "What is the late fee for returns?" but policy doesn't mention late fees.

**Mitigation** ✅:
- System prompt instructs LLM to explicitly state "not specified in the provided documents"
- Citation system ensures LLM can't hallucinate facts (requires source attribution)
- Low similarity scores trigger "I don't have enough information" responses

**Testing**: Verified with out-of-scope queries during development.

---

#### 3. **Out-of-Scope Questions**

**Failure**: User asks "What's the weather today?" or "How do I cook pasta?"

**Mitigation** ✅:
- System prompt includes explicit scope definition: "You are a policy assistant. Only answer questions about the uploaded policy documents."
- Query embedding similarity threshold filters irrelevant queries
- LLM trained to politely decline off-topic questions

---

#### 4. **Ambiguous Queries**

**Failure**: User asks "What's the policy?" without specifying which policy or aspect.

**Mitigation** ✅:
- System prompt instructs LLM to ask clarifying questions
- Conversation history provides context for follow-up queries
- Re-ranking boosts "Overview" and "Definitions" sections for broad queries

---

#### 5. **Token Budget Overflow**

**Failure**: Query retrieves 20 large chunks (20,000 chars), exceeding LLM context window.

**Mitigation** ✅:
- Token budget enforcement in `RerankerService.enforce_token_budget()`
- Iterates through reranked chunks (highest score first)
- Adds chunks until budget reached, discards rest
- Configurable budget (default: 4000 tokens for context)

---

#### 6. **Embedding Service Failure**

**Failure**: FastEmbed model fails to load or crashes during embedding.

**Mitigation**:
- Singleton pattern with initialization check
- Raises `ValueError` if accessed before initialization
- Startup event in FastAPI ensures embedding model loads before accepting requests

**Gap**: No retry logic or fallback model.

---

#### 7. **Vector Database Unavailable**

**Failure**: Qdrant service is down or unreachable.

**Mitigation**:
- Connection pooling and async client in `QdrantClientSingleton`
- Initialization check at startup
- HTTP errors propagate to client with 500 status

**Gap**: No circuit breaker or graceful degradation (e.g., falling back to keyword search).

---

#### 8. **Citation Extraction Fails**

**Failure**: LLM returns malformed JSON or fails to extract citations.

**Mitigation**:
- JSON mode enforced in Groq API call (`response_format={"type": "json_object"}`)
- Try-catch around JSON parsing with fallback to empty citations
- Logging of extraction failures for debugging

**Impact**: User still gets answer, just without citations (degraded but functional).

---

#### 9. **Chunking Edge Cases**

**Failure**: Extremely long table (5000 chars) marked as atomic, can't be split.

**Mitigation**:
- Semantic chunker has fallback: if atomic unit exceeds max size, splits by sentences
- Logs warning for manual review

**Gap**: Very large tables may still cause issues if they can't be split meaningfully.

---

#### 10. **Conversation History Growth**

**Failure**: Long conversation (50+ messages) causes context overflow.

**Current State**:
- ✅ Last N messages kept verbatim
- ❌ Older message summarization NOT implemented (Phase 4 incomplete)
- ❌ Topic/document tracking partially implemented but not used

**Risk**: Long conversations may degrade performance or hit token limits.

**Future Enhancement**:
- Implement message summarization for messages beyond last 10
- Use `documents_discussed` and `topics_covered` for context compression

---

### Summary

The system handles most critical failure modes gracefully, with strong mitigations for out-of-scope queries, partial information, and token overflow. Key gaps include:
1. No explicit version/superseding logic for contradictory policies
2. Incomplete conversation summarization for long chats
3. No fallback for vector database failures

These represent acceptable trade-offs for an MVP but should be prioritized for production deployment.

