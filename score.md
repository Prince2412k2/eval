# Policy Chatbot Development - Technical Evaluation Checklist

---

## Scoring Summary

| Section                          | Points  | scored |
| -------------------------------- | ------- | ------ |
| A: Core Implementation           | 60      | 54     |
| B: Edge Cases & Error Handling   | 20      | 16     |
| C: System Design & Justification | 20      | 17     |
| D: Bonus Challenges              | +15     | 4      |
| **total**                        | **115** | **91** |

---

## SECTION A: Core Implementation (60 points)

### Task 1: Project Setup (5 points)

- [x] Standard setup with Docker Compose
- [x] README created
- [x] .env.example created
- [x] Backend stack chosen
- [x] Frontend stack chosen
- [x] Vector DB chosen
- [x] LLM chosen

**Total: 5 points**

### Task 2: Intelligent Document Chunking (15 points)

**1. Implement TWO different chunking strategies (configurable):**

- [x] Strategy A: Sliding window with overlap
- [x] Strategy B: Semantic boundary detection (paragraphs, sections, or sentences)

**2. Handle these edge cases:**

- [x] A policy rule that spans across what would be a chunk boundary
- [x] Numbered lists where items reference each other (e.g., "See item 3 above")
- [x] Tables with multi-row cells
- [x] Headers that must stay attached to their content

**3. Metadata preservation:**

- [x] Parent document ID stored
- [x] Page number(s) stored
- [x] Section hierarchy stored
- [x] Chunk's relative position stored

**4. Written Requirement (200-300 words in README):**

- [x] Why did you choose your chunking boundaries?
- [x] What's the trade-off between chunk size and retrieval accuracy?
- [x] How do you handle a sentence spanning two pages?

**Criteria:**

- [x] Two chunking strategies implemented and configurable - **4 points**
- [x] Edge cases handled correctly - **4 points**
- [x] Metadata correctly preserved - **3 points**
- [x] Written explanation demonstrates understanding - **4 points**

**Total: 15 points**

### Task 3: RAG Pipeline with Custom Ranking (20 points)

**Part A: Basic Retrieval (6 points)**

- [x] Semantic search implemented with vector database

**Part B: Custom Re-Ranking Logic (8 points)**

- [x] Do NOT just return top-k by cosine similarity
- [x] Recency Boost: Prefer chunks from more recently uploaded documents
- [x] Section Hierarchy Bonus: Boost "Definitions" or "Overview" sections for ambiguous queries
- [x] Adjacent Chunk Consideration: If chunk #5 is relevant, consider chunks #4 and #6 for context
- [x] Scoring function: final_score = (similarity x W1) + (recency x W2) + (hierarchy x W3) + (adjacency x W4)

**Part C: Context Window Management (6 points)**

- [x] Function returns optimal subset maximizing information while fitting budget
- [x] Consider: ranking score, diversity (don't repeat similar info), completeness (include adjacent chunks that complete thoughts)

**4. Written Requirement (150-200 words):**

- [x] How did you determine weights?
- [x] What if top chunk (0.95 similarity) is 3 years old, but another (0.80 similarity) is from last week?

**Criteria:**

- [x] Basic retrieval works - **3 points**
- [x] Custom re-ranking with all 4 factors - **5 points**
- [x] Weights justified in README - **3 points**
- [x] Context window optimization implemented - **4 points**
- [x] Token budget function handles edge cases - **3 points**
- [x] Written explanation shows reasoning - **2 points**

**Total: 20 points**

### Task 4: Citation Extraction & Verification (12 points)

**Requirements:**

- [x] Citation granularity: Document name, page number, section, actual text span (50-200 chars)
- [x] Handle Synthesis: Answer combines info from 3 docs - each claim cites its specific source
- [x] Handle Inference: LLM makes logical inference - mark differently from direct quotes
- [x] Verification endpoint: /api/verify-citation returns source text, context, confidence score

**Written Requirement (100-150 words):**

- [x] How do you distinguish direct quote vs paraphrase vs inference?
- [x] How handle synthesized info with no single supporting chunk?

**Criteria:**

- [x] Citations include all required metadata - **3 points**
- [x] Multi-source synthesis handled correctly - **3 points**
- [x] Inferences marked differently from direct citations - **2 points**
- [x] Verification endpoint works - **2 points**
- [x] Written explanation addresses edge cases - **2 points**

**Total: 12 points**

### Task 5: Conversation Management (8 points)

**Problem:** 20-message conversation exceeds token limits. Implement:

- [x] Keep last N messages in full, summarize older messages
- [ ] Handle references to "what I asked earlier" when that message is summarized
- [ ] Track conversation state: documents discussed, topics covered, user preferences

**Criteria:**

- [x] Conversation history persisted - **2 points**
- [ ] Summarization strategy implemented - **3 points**
- [ ] Conversation state tracking works - **2 points**
- [ ] Handles "what I asked earlier" references - **1 point**

**Total: 8 points**

---

## SECTION B: Edge Cases & Error Handling (20 points)

### Task 6: Robustness Scenarios (10 points)

**Scenario 1: Redundant Information (3 points)**

- [x] HR_Policy_2023.pdf says "15 days leave". HR_Policy_2024.pdf says "20 days leave". User asks: "How many days of leave?"
- [x] Detect contradiction and redundancy, respond appropriately, NOT confidently state one answer

**Scenario 2: Partial Information (3 points)**

- [x] Documents have domestic travel limit ($500/day) but international travel only says "reasonable expenses"
- [x] Acknowledge what IS known, state what ISN'T specified, NOT hallucinate a number

**Scenario 3: Out of Scope (2 points)**

- [x] User asks: "What's the capital of France?"
- [x] Recognize not in documents, politely redirect to policy questions

**Scenario 4: Ambiguous Query (2 points)**

- [x] User asks: "What's the policy?"
- [x] Recognize ambiguity, ask for clarification OR list available topics

**Total: 10 points**

### Task 7: Document Filtering Logic (10 points)

**1. Hierarchical Documents (3 points)**

- [ ] If v1 and v2 exist, v2 supersedes v1
- [ ] Implement metadata flag: supersedes: [document IDs]

**2. Cross-Reference Detection (3 points)**

- [x] Document A says "See IT Security Policy section 4.2"
- [x] If user only queries A, detect the reference and ask/notify about including the referenced doc

**3. Conflict Detection (2 points)**

- [x] Detect when a single document contradicts itself internally

**Written Requirement (100-150 words):**

- [x] How do you detect cross-references?
- [ ] UX trade-off between auto-including vs asking?

**Total: 10 points**

---

## SECTION C: System Design & Justification (20 points)

### Task 8: Architecture Decisions (10 points)

**Q1: Embedding Model Choice (3 points)**

- [x] What embedding model did you use and why?
- [x] Trade-off between embedding dimension size and retrieval quality?
- [x] How would your choice change for 10 different languages?

**Q2: Chunk Size Decision (3 points)**

- [x] What chunk size did you choose and why?
- [x] Show example where it works well
- [x] Show example where it might fail

**Q3: Database Schema (4 points)**

- [x] Describe your schema (tables/collections, relationships)
- [x] How handle: document versions, chunk relationships, conversation-message relationships?
- [x] What indexes did you create and why?

**Total: 10 points**

### Task 9: Failure Mode Analysis (10 points)

**Scenario A: Scale (3 points)**

- [ ] 500-page PDF, 500-token chunks with 100-token overlap. How many chunks?
- [x] Retrieval latency impact?
- [x] What would you do differently?

**Scenario B: Adversarial Input (3 points)**

- [x] Document contains: "IGNORE ALL PREVIOUS INSTRUCTIONS..."
- [x] Do you have prompt injection protection?
- [x] How would you mitigate?

**Scenario C: Stale Data (2 points)**

- [ ] New policy uploaded but old chunks still in vector DB
- [ ] How ensure old info doesn't contaminate answers?

**Scenario D: LLM Uncertainty (2 points)**

- [x] How implement confidence score?
- [x] What if confidence is low?

**Total: 10 points**

---

## SECTION D: Bonus Challenges (+15 points)

### Challenge 1: Streaming + Citations (4 points)

- [x] Stream response tokens while providing accurate citations
- [x] How cite incomplete sentences?

### Challenge 2: Semantic Caching (4 points)

- [ ] Recognize "leave policy" and "vacation days" as similar, use cached retrieval results

### Challenge 3: Query Decomposition (4 points)

- [ ] "Compare 2023 and 2024 policies"  decompose into sub-queries, execute, synthesize

### Challenge 4: Feedback Loop (3 points)

- [ ] Use "helpful/not helpful" feedback to improve retrieval over time
- [ ] Describe architecture

**Total: +15 points**

---
