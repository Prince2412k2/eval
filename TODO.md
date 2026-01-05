# Policy Chatbot – TODO Checklist

---

## PHASE 0 — Setup (30 min | 5 pts)

- [x] Create repo structure
  - [x] `backend/`
  - [x] `frontend/`

- [x] Add Dockerfiles (backend + frontend)
- [x] Create `docker-compose.yml`
- [x] Add `.env.example`
- [x] Create `README.md` skeleton with headings
- [x] Choose stack (document clearly)

---

## PHASE 1 — Document Ingestion & Chunking (1.5 hrs | 15 pts)

### File Processing

- [x] Upload & parse:
  - [x] PDF
  - [x] DOCX
  - [x] TXT

- [x] Extract:
  - [x] text
  - [x] page numbers
  - [x] headings / sections
  - [x] lists
  - [x] tables

---

### Chunking Strategy A — Sliding Window

- [x] Implement fixed-size chunks
- [x] Add overlap
- [x] Make chunk size configurable

---

### Chunking Strategy B — Semantic Chunking

- [x] Detect section headers
- [x] Keep headers + first paragraph together
- [x] Keep numbered lists intact
- [x] Treat tables as atomic chunks
- [x] Avoid splitting policy rules across pages

---

### Metadata (CRITICAL)

- [x] Store for every chunk:
  - [x] document_id
  - [x] page_numbers
  - [x] section_hierarchy
  - [x] chunk_index

---

## PHASE 2 — RAG + Custom Ranking (1.5 hrs | 20 pts)

### Retrieval

- [x] Embed chunks
- [x] Store in vector DB
- [x] Implement semantic search

---

### Custom Re-Ranking (MANDATORY)

- [x] Implement scoring:

  ```
  final_score =
    similarity * W1 +
    recency * W2 +
    hierarchy * W3 +
    adjacency * W4
  ```

- [x] Recency boost (newer > older)
- [x] Section bonus (Definitions / Overview)
- [x] Adjacent chunk boost (±1 chunk)

---

### Context Window Management

- [x] Enforce token budget
- [x] Select best subset of chunks
- [x] Avoid redundant info
- [x] Include adjacent chunks if needed

---

## PHASE 3 — Citations & Verification (1 hr | 12 pts)

### Citation System

- [x] Each claim has citation:
  - [x] document name
  - [x] page number
  - [x] section
  - [x] 50–200 char text span

- [x] Mark citation type:
  - [x] direct quote
  - [x] paraphrase
  - [x] inference

---

### Verification API

- [x] `POST /api/verify-citation`
- [x] Return:
  - [x] source text
  - [x] context
  - [x] confidence score

---

## PHASE 4 — Conversation Management (30 min | 8 pts)

- [x] Persist chat history
- [x] Keep last N messages verbatim
- [ ] Summarize older messages
- [ ] Track:
  - [ ] documents discussed
  - [ ] topics covered

- [ ] Handle:
  - [ ] “what I asked earlier…”

---

## PHASE 5 — Edge Cases & Safety (45 min | 20 pts)

### Robustness Scenarios

- [ ] Detect contradictory policies (v1 vs v2)
- [x] Handle partial info (say “not specified”)
- [x] Detect out-of-scope questions
- [x] Handle ambiguous queries

---

### Document Logic

- [ ] Version superseding (`supersedes`)
- [ ] Detect cross-references
- [ ] Ask / notify before auto-including docs
- [ ] Detect internal document contradictions

---

## PHASE 6 — Writing & Justification (45 min | 20 pts)

### README / DESIGN.md

- [ ] Chunking strategy explanation (200–300 words)
- [ ] Re-ranking weights justification (150–200 words)
- [ ] Citation handling explanation (100–150 words)
- [ ] Cross-reference UX decision (100–150 words)
- [ ] Embedding model choice
- [ ] Chunk size trade-offs
- [ ] DB schema description
- [ ] Failure mode analysis

---

## ⭐ BONUS (Only If Time Left)

- [x] Streaming responses with citations
- [ ] Semantic caching
- [ ] Query decomposition
- [ ] Feedback loop

---

## 🎯 FINAL SANITY CHECK (10 min)

- [x] System says “I don’t know” when unsure
- [x] Citations actually support answers
- [ ] README explains **why**, not just **what**
- [ ] No default-only logic

---
