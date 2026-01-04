# Policy Chatbot – TODO Checklist

---

## PHASE 0 — Setup (30 min | 5 pts)

- [ ] Create repo structure
  - [ ] `backend/`
  - [ ] `frontend/`

- [ ] Add Dockerfiles (backend + frontend)
- [ ] Create `docker-compose.yml`
- [ ] Add `.env.example`
- [ ] Create `README.md` skeleton with headings
- [ ] Choose stack (document clearly)

---

## PHASE 1 — Document Ingestion & Chunking (1.5 hrs | 15 pts)

### File Processing

- [ ] Upload & parse:
  - [ ] PDF
  - [ ] DOCX
  - [ ] TXT

- [ ] Extract:
  - [ ] text
  - [ ] page numbers
  - [ ] headings / sections
  - [ ] lists
  - [ ] tables

---

### Chunking Strategy A — Sliding Window

- [ ] Implement fixed-size chunks
- [ ] Add overlap
- [ ] Make chunk size configurable

---

### Chunking Strategy B — Semantic Chunking

- [ ] Detect section headers
- [ ] Keep headers + first paragraph together
- [ ] Keep numbered lists intact
- [ ] Treat tables as atomic chunks
- [ ] Avoid splitting policy rules across pages

---

### Metadata (CRITICAL)

- [ ] Store for every chunk:
  - [ ] document_id
  - [ ] page_numbers
  - [ ] section_hierarchy
  - [ ] chunk_index

---

## PHASE 2 — RAG + Custom Ranking (1.5 hrs | 20 pts)

### Retrieval

- [ ] Embed chunks
- [ ] Store in vector DB
- [ ] Implement semantic search

---

### Custom Re-Ranking (MANDATORY)

- [ ] Implement scoring:

  ```
  final_score =
    similarity * W1 +
    recency * W2 +
    hierarchy * W3 +
    adjacency * W4
  ```

- [ ] Recency boost (newer > older)
- [ ] Section bonus (Definitions / Overview)
- [ ] Adjacent chunk boost (±1 chunk)

---

### Context Window Management

- [ ] Enforce token budget
- [ ] Select best subset of chunks
- [ ] Avoid redundant info
- [ ] Include adjacent chunks if needed

---

## PHASE 3 — Citations & Verification (1 hr | 12 pts)

### Citation System

- [ ] Each claim has citation:
  - [ ] document name
  - [ ] page number
  - [ ] section
  - [ ] 50–200 char text span

- [ ] Mark citation type:
  - [ ] direct quote
  - [ ] paraphrase
  - [ ] inference

---

### Verification API

- [ ] `POST /api/verify-citation`
- [ ] Return:
  - [ ] source text
  - [ ] context
  - [ ] confidence score

---

## PHASE 4 — Conversation Management (30 min | 8 pts)

- [ ] Persist chat history
- [ ] Keep last N messages verbatim
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
- [ ] Handle partial info (say “not specified”)
- [ ] Detect out-of-scope questions
- [ ] Handle ambiguous queries

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

- [ ] Streaming responses with citations
- [ ] Semantic caching
- [ ] Query decomposition
- [ ] Feedback loop

---

## 🎯 FINAL SANITY CHECK (10 min)

- [ ] System says “I don’t know” when unsure
- [ ] Citations actually support answers
- [ ] README explains **why**, not just **what**
- [ ] No default-only logic

---

If you want next, I can:

- Convert this into a **GitHub issue board**
- Mark **absolute must-do vs nice-to-have**
- Give you a **minimal 70-point survival plan**

Just tell me how aggressive you want to be.
