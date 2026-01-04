from fastapi import APIRouter, Depends
from groq import AsyncGroq
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse
import json

from supabase import AsyncClient
from app.core.database import get_db
from app.core.groq import get_groq
from app.core.supabase import get_supabase
from app.core.vector import get_qdrant
from app.schema.messages import MessageSchema
from app.service.embedding_service import EmbeddingService, VectorService
from app.service.query_service import QueryService
from app.service.upload_service import DocumentCRUD
from app.service.reranker_service import RerankerService

query_router = APIRouter()


@query_router.post("/")
async def ask(
    msg: MessageSchema,
    groq: AsyncGroq = Depends(get_groq),
    qdrant: AsyncQdrantClient = Depends(get_qdrant),
    db: AsyncSession = Depends(get_db),
    supabase: AsyncClient = Depends(get_supabase),
):
    # Step 1: Embed the query
    query_embedd = EmbeddingService.embed_string(msg.query)
    
    # Step 2: Retrieve initial candidates (more than final top_k for reranking)
    initial_chunks = await VectorService.query_similar_chunks(
        query_embedding=query_embedd, qdrant=qdrant, top_k=20
    )
    
    # Step 3: Rerank chunks using custom scoring
    reranked_chunks = RerankerService.rerank_chunks(
        chunks=initial_chunks,
        top_k=10,  # Get top 10 after reranking
        include_adjacent=True,  # Include adjacent chunks for context
    )
    
    # Step 4: Enforce token budget to avoid context overflow
    final_chunks = RerankerService.enforce_token_budget(
        chunks=reranked_chunks,
        max_tokens=4000,  # Adjust based on your LLM's context window
    )
    
    # Step 5: Format context for LLM
    merged_context = VectorService.format_context(final_chunks)
    
    # Step 6: Get source documents for citation
    sources_hash = VectorService.get_source_documents(final_chunks)
    docs = await DocumentCRUD.get_by_ids(db, sources_hash)
    names = [str(i.title) for i in docs]
    sources = await DocumentCRUD.generate_signed_urls(
        supabase, file_hashes=sources_hash, names=names
    )

    gen = QueryService.query(msg.query, merged_context, groq)
    final_reply = ""

    async def stream():
        nonlocal final_reply
        async for content in gen:
            final_reply += content
            yield f"data: {json.dumps({'type': 'stream', 'data': content})}\n\n"
        yield f"data: {json.dumps({'type': 'final', 'data': final_reply, 'sources': sources})}\n\n"

    # async def stream():
    #     nonlocal final_reply
    #     async for content in gen:
    #         final_reply += content
    #         yield content
    #     yield f"data: {json.dumps({'type': 'final', 'data': final_reply, 'sources': sources})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
