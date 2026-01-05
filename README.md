# Policy Chatbot – RAG-Based Document Q&A System

A production-ready chatbot system for querying policy documents using Retrieval-Augmented Generation (RAG), custom re-ranking, and transparent citation tracking.

---

## 🎯 Overview

This system enables users to upload policy documents (PDF, DOCX, TXT) and ask natural language questions. The chatbot retrieves relevant information using semantic search, re-ranks results using custom scoring, and provides answers with **verifiable citations** including document name, page number, and exact text spans.

**Key Features**:
- ✅ Multi-format document ingestion (PDF, DOCX, TXT)
- ✅ Structure-aware semantic chunking
- ✅ Custom re-ranking with recency, hierarchy, and adjacency scoring
- ✅ Transparent citations with verification API
- ✅ **Security guard** for prompt injection protection
- ✅ Streaming responses for better UX
- ✅ Conversation history with context management
- ✅ Edge case handling (contradictions, out-of-scope queries, ambiguity)

---

## 🏗️ Architecture

### Tech Stack

**Backend**:
- **Framework**: FastAPI (Python 3.12+)
- **Database**: PostgreSQL (relational data) + Qdrant (vector search)
- **LLMs**: 
  - Main: `openai/gpt-oss-120b` (via Groq)
  - Citations: `llama-3.1-8b-instant` (via Groq)
  - Security Guard: `openai/gpt-oss-120b` (via Groq)
- **Embeddings**: `BAAI/bge-small-en-v1.5` (384-dim, via FastEmbed)
- **Document Parsing**: LlamaParse (LlamaIndex)
- **ORM**: SQLAlchemy

**Frontend**:
- **Framework**: React 19 + TypeScript
- **Styling**: TailwindCSS 4
- **Routing**: React Router v7
- **UI Components**: Custom components with Lucide icons
- **Build Tool**: Vite

**Infrastructure**:
- **Containerization**: Docker + Docker Compose
- **Storage**: Supabase (file storage)

---

## 📁 Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── core/          # Config, database, embedding, vector DB
│   │   ├── models.py      # SQLAlchemy models
│   │   ├── routes/        # API endpoints
│   │   ├── schema/        # Pydantic schemas
│   │   └── service/       # Business logic (chunking, RAG, citations)
│   ├── migrations/        # Database migrations
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Route pages
│   │   └── lib/           # Utilities
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── DESIGN.md              # Detailed design decisions
└── TODO.md                # Implementation checklist
```

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.12+ (for local backend development)

### Environment Setup

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd eval
   ```

2. **Set up external services**:
   
   This project uses **external/hosted services** for:
   - **PostgreSQL**: Database for conversations, documents, and metadata
   - **Qdrant**: Vector database for semantic search
   - **Supabase**: File storage for uploaded documents
   
   You'll need to set up these services separately (e.g., via cloud providers).

3. **Create environment file**:

   Copy the example and fill in your credentials:
   ```bash
   cp .env.example backend/.env
   ```

   **Backend** (`backend/.env`):
   ```env
   LLAMAINDEX=<llama-cloud-api-key>
   DB_URL=postgresql://user:password@your-db-host:5432/policy_db
   GROQ_API=<groq-api-key>
   QDRANT_URL=https://your-qdrant-instance.cloud:6333
   QDRANT_API_KEY=<qdrant-api-key>
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=<supabase-anon-key>
   SECRET_KEY=<generate-with-openssl-rand-hex-32>
   ```

4. **Start services**:
   ```bash
   docker-compose up -d
   ```

5. **Access the application**:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

---

## 📚 Documentation

- **[DESIGN.md](./DESIGN.md)**: Comprehensive design decisions including:
  - Chunking strategy explanation
  - Re-ranking weights justification
  - Citation handling architecture
  - Cross-reference UX decisions
  - Embedding model choice
  - Chunk size trade-offs
  - Database schema
  - Failure mode analysis

- **[Backend README](./backend/README.md)**: Backend-specific documentation
- **[CITATIONS.md](./backend/CITATIONS.md)**: Detailed citation system documentation
- **[RERANKING.md](./backend/RERANKING.md)**: Re-ranking algorithm details

---

## 🔑 Key Design Decisions

### 1. Chunking Strategy

**Hybrid semantic chunking** that:
- Preserves document structure (headers, tables, lists)
- Treats tables and numbered lists as atomic units
- Maintains section hierarchy for better re-ranking
- Uses configurable chunk sizes (max: 1000, min: 100, overlap: 150 chars)

**Why?** Fixed-size chunking breaks semantic meaning; pure semantic chunking can create oversized chunks. Our hybrid approach balances both.

### 2. Re-Ranking Weights

```
final_score = similarity × 0.5 + recency × 0.2 + hierarchy × 0.2 + adjacency × 0.1
```

**Why these weights?**
- **Similarity (50%)**: Semantic relevance is fundamental
- **Recency (20%)**: Newer policies often supersede older ones
- **Hierarchy (20%)**: Definitions and policy rules are more valuable than tangential mentions
- **Adjacency (10%)**: Consecutive chunks indicate coherent sections

### 3. Triple-LLM Architecture with Security

**Parallel execution**:
- **Security guard** (`gpt-oss-120b`) validates user input for prompt injections
- Fast model (`llama-3.1-8b-instant`) extracts citations in JSON
- Main model (`gpt-oss-120b`) streams the answer

**Why?** Parallel execution keeps latency at ~2-3s while providing security, citations, and quality answers. Total cost: ~$0.0015-0.002 per query.

### 4. Embedding Model: BAAI/bge-small-en-v1.5

**Why?**
- State-of-the-art retrieval performance
- 384-dim vectors (fast + storage-efficient)
- Runs locally (no API costs, privacy-preserving)
- Excellent for technical/policy documents

---

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| Query Latency (p50) | ~2.5s |
| Query Latency (p95) | ~4s |
| Vector Search | ~100ms |
| Re-ranking | ~50ms |
| Security Guard | ~500ms |
| Cost per Query | ~$0.0015-0.002 |
| Embedding Speed | ~10-20ms |

---

## 🛠️ Development

### Running Locally (without Docker)

**Backend**:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend**:
```bash
cd frontend
npm install
npm run dev
```

---

## 🔒 Security Considerations

- API keys stored in environment variables (never committed)
- User authentication ready (user_id field in conversations)
- SQL injection prevented via SQLAlchemy ORM
- File upload validation (mime type, size limits)
- CORS configured for production

---

## 🚧 Known Limitations

1. **No explicit version/superseding logic**: Users must manually delete old policy versions
2. **Conversation summarization incomplete**: Long conversations (50+ messages) may hit token limits
3. **No fallback for vector DB failures**: System returns 500 if Qdrant is unavailable
4. **Cross-references not auto-expanded**: Prevents context pollution but requires manual follow-up

See [DESIGN.md](./DESIGN.md#failure-mode-analysis) for detailed failure mode analysis.

---

## 🗺️ Roadmap

- [ ] Implement document versioning and superseding logic
- [ ] Complete conversation summarization for older messages
- [ ] Add semantic caching for common queries
- [ ] Implement query decomposition for complex questions
- [ ] Add feedback loop for continuous improvement
- [ ] Cross-encoder re-ranking for higher precision
- [ ] Multi-document citation support

---

## 📝 License

MIT License - see LICENSE file for details

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

---

## 📧 Contact

For questions or issues, please open a GitHub issue or contact the maintainers.

---

**Built with ❤️ for accurate, verifiable policy question-answering**
