
# **Section A**
## Task 1: Project Setup (5 points)
- Docker Compose,
- README
- .env.example.
- Your choice of stack (any backend, frontend, vector DB, LLM).

## Task 2: Intelligent Document Chunking (15 points)

- [x]  PDF, DOCX, and TXT support

1. Implement TWO different chunking strategies (configurable):
    - [x] Strategy A: Sliding window with overlap
    - [x] Strategy B: Semantic boundary detection (paragraphs, sections, or sentences)
    
2. Handle these edge cases (we will test these):
    - [x] A policy rule that spans across what would be a chunk boundary
    - [x] Numbered lists where items reference each other (e.g., "See item 3 above")
    - [x] Tables with multi-row cells
    - [x]  Headers that must stay attached to their content

3. **Metadata preservation** - Each chunk must store: 
- [x]  parent document ID
- [x] page number(s)
- [x] section hierarchy
- [x] chunk's relative position.

4. **Written Requirement** (200-300 words in README): Why did you choose your chunking boundaries? What's the trade-off between chunk size and retrieval accuracy? How do you handle a sentence spanning two pages?


## Task 3: RAG Pipeline with Custom Ranking (20 points)

1. **Basic Retrieval** (6 poi`nts)
	- Implement semantic search with a vector database.

2.  **Custom Re-Ranking Logic** (8 points)
	Your re-ranking must consider:
    1. Recency Boost: Prefer chunks from more recently uploaded documents
    2. Section Hierarchy Bonus: Boost "Definitions" or "Overview" sections for ambiguous queries
    3. Adjacent Chunk Consideration: If chunk #5 is relevant, consider chunks #4 and #6 for context
    4. Implement a scoring function: final_score = (similarity * W1) + (recency * W2) + (hierarchy * W3) + (adjacency * W4)

3. **Context Window Management** (6 points)
- Problem: You retrieve 10 chunks totaling 8,000 tokens. Your LLM budget is 4,000 tokens.
- Implement a function that returns the optimal subset maximizing information while fitting the budget. Consider: ranking score, diversity (don't repeat similar info), completeness (include adjacent chunks that complete thoughts).
- How did you determine weights? What if top chunk (0.95 similarity) is 3 years old, but another (0.80 similarity) is from last week?

## Citation Extraction & Verification (12 points)

- Citations must be verifiable and precise. We will test whether citations actually support claims made.
    1. Citation granularity: Document name, page number, section, actual text span (50-200 chars)
    2. Handle Synthesis: Answer combines info from 3 docs - each claim cites its specific source
    3. Handle Inference: LLM makes logical inference - mark differently from direct quotes
    4. Verification endpoint: /api/verify-citation returns source text, context, confidence score
## Task 5: Conversation Management (8 points)

**Problem:** 20-message conversation exceeds token limits. Implement conversation summarization:

- Keep last N messages in full, summarize older messages
    
- Handle references to "what I asked earlier" when that message is summarized
    
- Track conversation state: documents discussed, topics covered, user preferences






# **Section B**


### 6. edge cases
#### Scenario 1: Redundant Information (3 points)

HR_Policy_2023.pdf says "15 days leave". HR_Policy_2024.pdf says "20 days leave". User asks: "How many days of leave?"

**Your system must:** Detect contradiction and redundancy, respond appropriately, NOT confidently state one answer.

#### Scenario 2: Partial Information (3 points)

Documents have domestic travel limit ($500/day) but international travel only says "reasonable expenses".

**Your system must:** Acknowledge what IS known, state what ISN'T specified, NOT hallucinate a number.

#### Scenario 3: Out of Scope (2 points)

User asks: "What's the capital of France?"

**Your system must:** Recognize not in documents, politely redirect to policy questions.

#### Scenario 4: Ambiguous Query (2 points)

User asks: "What's the policy?"

**Your system must:** Recognize ambiguity, ask for clarification OR list available topics.


### 7.  Document Filtering Logic (10 points)

**1. Hierarchical Documents (3 points):** If v1 and v2 exist, v2 supersedes v1. Implement metadata flag: supersedes: [document IDs]

**2. Cross-Reference Detection (3 points):** Document A says "See IT Security Policy section 4.2". If user only queries A, detect the reference and ask/notify about including the referenced doc.

**3. Conflict Detection (2 points):** Detect when a single document contradicts itself internally.
