from fastapi import APIRouter, Depends
from groq import AsyncGroq
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse
import json
import asyncio

from supabase import AsyncClient
from app.core.database import get_db
from app.core.groq import get_groq
from app.core.supabase import get_supabase
from app.core.vector import get_qdrant
from app.schema.messages import MessageSchema
from app.schema.citation import CitationType
from app.service.embedding_service import EmbeddingService, VectorService
from app.service.query_service import QueryService
from app.service.upload_service import DocumentCRUD
from app.service.reranker_service import RerankerService
from app.service.citation_service import CitationService
from app.service.conversation_service import ConversationService

query_router = APIRouter()


@query_router.post("/")
async def ask(
    msg: MessageSchema,
    groq: AsyncGroq = Depends(get_groq),
    qdrant: AsyncQdrantClient = Depends(get_qdrant),
    db: AsyncSession = Depends(get_db),
    supabase: AsyncClient = Depends(get_supabase),
):
    # Step 1: Get or create conversation
    if msg.conversation_id:
        conversation = await ConversationService.get_conversation(db, msg.conversation_id)
        if not conversation:
            from fastapi import HTTPException
            raise HTTPException(404, "Conversation not found")
    else:
        conversation = await ConversationService.create_conversation(db)
    
    # Step 2: Save user message
    await ConversationService.add_message(
        db, conversation.id, "user", msg.query
    )
    
    # Step 3: Get conversation history for context
    history = await ConversationService.get_conversation_history(
        db, conversation.id, last_n=5
    )
    conversation_context = ConversationService.build_context_from_history(history[:-1])  # Exclude current message
    
    # Step 4: Embed the query (optionally enhanced with conversation context)
    # Use conversation context if available for better retrieval
    enhanced_query = msg.query
    if conversation_context:
        # Optionally enhance query with recent context (commented out for now)
        # enhanced_query = f"{conversation_context}\n\nCurrent question: {msg.query}"
        pass
    
    query_embedd = EmbeddingService.embed_string(enhanced_query)

    # Step 5: Retrieve initial candidates (more than final top_k for reranking)
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

    # Step 7: Create document name mapping for citations
    doc_name_map = {doc.hash: doc.title for doc in docs}
    chunk_map = {i: chunk for i, chunk in enumerate(final_chunks)}

    # Step 8: Define citation extraction task (runs in parallel)
    async def extract_citations_task():
        try:
            raw_citations = await QueryService.extract_citations_structured(
                query=msg.query, chunks=final_chunks, groq=groq
            )

            # Map raw citations to full Citation objects
            citations = []
            for raw_cit in raw_citations:
                chunk_idx = raw_cit.get("chunk_index", 0)
                if chunk_idx in chunk_map:
                    chunk = chunk_map[chunk_idx]
                    doc_id = chunk.get("document_id", "Unknown")
                    doc_name = doc_name_map.get(doc_id, doc_id)

                    citation = CitationService.create_citation_from_chunk(
                        chunk=chunk,
                        claim_text=raw_cit.get("claim_text", ""),
                        citation_type=CitationType(
                            raw_cit.get("citation_type", "paraphrase")
                        ),
                        document_name=doc_name,
                        text_span=raw_cit.get("text_span"),
                        confidence_score=1.0,
                    )
                    citations.append(citation)
            return citations
        except Exception as e:
            print(f"Citation extraction failed: {e}")
            return []

    # Start citation extraction (non-blocking)
    citation_task = asyncio.create_task(extract_citations_task())

    # Step 9: Stream main response (existing logic)
    gen = QueryService.query(msg.query, merged_context, groq)
    final_reply = ""

    async def stream():
        nonlocal final_reply

        # Stream tokens
        async for content in gen:
            final_reply += content
            yield f"data: {json.dumps({'type': 'stream', 'data': content})}\n\n"

        # Wait for citations to complete (should be done by now)
        citations = await citation_task
        formatted_citations = CitationService.format_citations_for_response(citations)
        
        # Save assistant message
        await ConversationService.add_message(
            db,
            conversation.id,
            "assistant",
            final_reply,
            sources=list(sources_hash),
            citations=formatted_citations
        )
        
        # Update conversation metadata
        topics = ConversationService.extract_topics_from_query(msg.query)
        await ConversationService.update_conversation_metadata(
            db,
            conversation.id,
            documents=list(sources_hash),
            topics=topics
        )

        # Send final message with citations and conversation_id
        yield f"data: {json.dumps({'type': 'final', 'data': final_reply, 'sources': sources, 'citations': formatted_citations, 'conversation_id': str(conversation.id)})}\n\n"

    # async def stream():
    #     nonlocal final_reply
    #     async for content in gen:
    #         final_reply += content
    #         yield content
    #     yield f"data: {json.dumps({'type': 'final', 'data': final_reply, 'sources': sources})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
