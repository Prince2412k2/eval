# Citations & Verification System Documentation

## Overview

The citations system provides transparent source attribution for every claim made by the LLM, ensuring accuracy and trustworthiness in policy-based question answering.

## Architecture

### Dual-LLM Approach

We use **two separate LLM calls** running in parallel:

1. **Citation Extraction** (Fast Model)
   - Model: `llama-3.1-8b-instant`
   - Output: Structured JSON with citations
   - Cost: ~$0.0001 per query
   - Latency: ~1-2 seconds

2. **User Response** (Main Model)
   - Model: `openai/gpt-oss-120b`
   - Output: Natural language answer (streaming)
   - Cost: ~$0.001 per query
   - Latency: ~2-3 seconds

**Total Latency**: ~2-3 seconds (parallel execution)

---

## Citation Types

### 1. Direct Quote (`direct_quote`)
- Exact wording from the source document
- Highest confidence
- Example: "The refund policy states: 'All returns must be made within 30 days'"

### 2. Paraphrase (`paraphrase`)
- Restated information maintaining original meaning
- High confidence
- Example: "Customers have 30 days to return items"

### 3. Inference (`inference`)
- Logical conclusion drawn from source
- Medium confidence
- Example: "This suggests receipts are mandatory for returns"

---

## API Endpoints

### Query with Citations

**Endpoint**: `POST /api/query`

**Request**:
```json
{
  "query": "What is the refund policy?"
}
```

**Response** (Server-Sent Events):
```
data: {"type": "stream", "data": "The refund policy "}
data: {"type": "stream", "data": "allows returns "}
data: {"type": "stream", "data": "within 30 days."}
data: {"type": "final", "data": "The refund policy allows returns within 30 days.", "sources": [...], "citations": [...]}
```

**Citation Format**:
```json
{
  "document_name": "Refund Policy v2.pdf",
  "document_id": "abc123",
  "page_number": 3,
  "section": "Returns and Refunds",
  "text_span": "All returns must be made within 30 days of purchase date",
  "claim_text": "allows returns within 30 days",
  "citation_type": "direct_quote",
  "chunk_index": 0,
  "confidence_score": 1.0
}
```

---

### Verify Citation

**Endpoint**: `POST /api/verify-citation`

**Request**:
```json
{
  "document_id": "abc123",
  "chunk_index": 0,
  "claim_text": "allows returns within 30 days",
  "expected_text_span": "All returns must be made within 30 days"
}
```

**Response**:
```json
{
  "source_text": "All returns must be made within 30 days of purchase date. Exceptions may apply for defective products.",
  "context": "Section 3.2: Returns and Refunds\n\nAll returns must be made within 30 days...",
  "confidence_score": 1.0,
  "is_accurate": true,
  "citation": {...},
  "issues": []
}
```

---

## Implementation Flow

### Query Pipeline

```
1. Embed query
2. Vector search (top 20)
3. Rerank (top 10)
4. Token budget enforcement
   ↓
5. Start citation extraction (async) ──┐
6. Stream main response               │
   ↓                                   │
7. Wait for citations ←────────────────┘
8. Return final response with citations
```

### Citation Extraction Process

```
1. Build numbered chunks with metadata
2. Send to llama-3.1-8b-instant with JSON mode
3. Parse structured JSON response
4. Map to Citation objects
5. Return formatted citations
```

---

## Code Examples

### Using Citations in Frontend

```javascript
// Handle streaming response
const eventSource = new EventSource('/api/query');

let fullResponse = '';
let citations = [];

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'stream') {
    fullResponse += data.data;
    updateUI(fullResponse);
  } else if (data.type === 'final') {
    citations = data.citations;
    displayCitations(citations);
  }
};

function displayCitations(citations) {
  citations.forEach((citation, index) => {
    console.log(`[${index + 1}] ${citation.document_name}, p.${citation.page_number}`);
    console.log(`   "${citation.text_span}"`);
    console.log(`   Type: ${citation.citation_type}`);
  });
}
```

### Verifying a Citation

```python
import httpx

async def verify_citation(document_id, chunk_index, claim_text):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/verify-citation",
            json={
                "document_id": document_id,
                "chunk_index": chunk_index,
                "claim_text": claim_text
            }
        )
        result = response.json()
        
        if result['is_accurate']:
            print(f"✓ Citation verified (confidence: {result['confidence_score']})")
        else:
            print(f"✗ Citation issues: {result['issues']}")
        
        return result
```

---

## Configuration

### Adjusting Citation Extraction

Edit `app/service/citation_service.py`:

```python
# Customize text span length
def extract_best_text_span(
    chunk_text: str,
    claim_text: str,
    min_length: int = 50,   # Adjust minimum
    max_length: int = 200,  # Adjust maximum
) -> str:
    ...
```

### Changing LLM Model

Edit `app/service/query_service.py`:

```python
# Use different model for citation extraction
resp = await groq.chat.completions.create(
    messages=[{"role": "user", "content": prompt}],
    model="llama-3.1-70b-versatile",  # More powerful model
    response_format={"type": "json_object"},
    temperature=0.1,
)
```

---

## Verification Logic

### Confidence Scoring

Citations are scored based on:

1. **Text Span Match** (0.0 - 1.0)
   - Exact match: 1.0
   - Fuzzy match (>70% similarity): 0.7-0.99
   - No match: <0.7

2. **Claim Relevance** (0.0 - 1.0)
   - Keyword overlap between claim and source
   - Minimum 30% overlap required

**Final Confidence**: `min(text_span_score, claim_relevance_score)`

**Accuracy Threshold**: `confidence >= 0.7 AND no_issues`

### Common Issues

- `text_span_not_found_in_source`: Text span doesn't exist in chunk
- `text_span_fuzzy_match`: Text span partially matches (fuzzy)
- `low_claim_relevance`: Claim has low keyword overlap with source

---

## Testing

### Unit Tests

```python
# Test citation creation
def test_create_citation():
    chunk = {
        'text': 'All returns must be made within 30 days.',
        'document_id': 'doc123',
        'page': 3,
        'chunk_index': 0,
        'metadata': {'section_hierarchy': ['Returns']}
    }
    
    citation = CitationService.create_citation_from_chunk(
        chunk=chunk,
        claim_text='30-day return policy',
        citation_type=CitationType.PARAPHRASE,
        document_name='Policy.pdf'
    )
    
    assert citation.page_number == 3
    assert citation.citation_type == CitationType.PARAPHRASE
```

### Integration Tests

```python
# Test full query flow with citations
async def test_query_with_citations():
    response = await client.post(
        "/api/query",
        json={"query": "What is the refund policy?"}
    )
    
    # Parse SSE stream
    events = parse_sse_stream(response.content)
    final_event = events[-1]
    
    assert 'citations' in final_event
    assert len(final_event['citations']) > 0
    assert final_event['citations'][0]['citation_type'] in ['direct_quote', 'paraphrase', 'inference']
```

---

## Performance

### Latency Breakdown

| Component | Time | Notes |
|-----------|------|-------|
| Vector search | ~100ms | Qdrant HNSW index |
| Reranking | ~50ms | Custom scoring |
| Citation extraction | ~1-2s | llama-3.1-8b-instant |
| Response streaming | ~2-3s | openai/gpt-oss-120b |
| **Total (parallel)** | **~2-3s** | Max of citation + streaming |

### Cost Analysis

| Component | Model | Cost per Query |
|-----------|-------|----------------|
| Citation extraction | llama-3.1-8b-instant | ~$0.0001 |
| Main response | openai/gpt-oss-120b | ~$0.001 |
| **Total** | | **~$0.0011** |

---

## Troubleshooting

### Citations Not Appearing

1. Check LLM response format:
   ```python
   # Add logging in query_service.py
   print(f"Citation extraction response: {content}")
   ```

2. Verify JSON parsing:
   ```python
   try:
       citations_data = json.loads(content)
   except json.JSONDecodeError as e:
       print(f"JSON parse error: {e}")
       print(f"Raw content: {content}")
   ```

### Low Citation Quality

1. Adjust prompt in `CitationService.build_citation_extraction_prompt()`
2. Increase temperature for more diverse citations
3. Use more powerful model (e.g., `llama-3.1-70b-versatile`)

### Verification Failures

1. Check chunk exists in Qdrant:
   ```python
   results = await qdrant.scroll(
       collection_name="documents",
       scroll_filter=...,
       limit=1
   )
   print(f"Found {len(results[0])} chunks")
   ```

2. Verify document_id and chunk_index match

---

## Future Enhancements

1. **Cross-encoder Reranking**: Use dedicated citation model
2. **Citation Caching**: Cache citations for common queries
3. **Multi-document Citations**: Support claims spanning multiple documents
4. **Citation Confidence Tuning**: ML-based confidence scoring
5. **Frontend Integration**: Rich citation UI with hover previews

---

## Summary

The citations system provides:

✅ Transparent source attribution for every claim  
✅ Three citation types (quote, paraphrase, inference)  
✅ Parallel LLM execution for speed  
✅ Verification API for accuracy checking  
✅ Structured JSON output for reliability  
✅ Low cost (~$0.0001 per query for citations)  

This ensures trustworthy, verifiable responses for policy-based question answering.
