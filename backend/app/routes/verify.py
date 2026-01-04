from fastapi import APIRouter, Depends, HTTPException
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.vector import get_qdrant
from app.schema.citation import VerificationRequest, VerificationResponse, Citation, CitationType
from app.service.citation_service import CitationService
from app.service.embedding_service import VectorService

verify_router = APIRouter()


@verify_router.post("/verify-citation", response_model=VerificationResponse)
async def verify_citation(
    request: VerificationRequest,
    qdrant: AsyncQdrantClient = Depends(get_qdrant),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a citation's accuracy against the source document.
    
    Args:
        request: Verification request with document_id, chunk_index, and claim_text
        
    Returns:
        VerificationResponse with source text, context, and confidence score
    """
    try:
        # Query Qdrant for all chunks from this document
        # Note: We filter by document_id only (which has an index), then find the specific chunk in memory
        from qdrant_client.http import models as qmodels
        
        results = await qdrant.scroll(
            collection_name="documents",
            scroll_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=request.document_id)
                    )
                ]
            ),
            limit=100,  # Get up to 100 chunks from this document
            with_payload=True
        )
        
        if not results[0] or len(results[0]) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Document not found: document_id={request.document_id}"
            )
        
        # Find the specific chunk by chunk_index
        point = None
        for p in results[0]:
            if p.payload and p.payload.get('chunk_index') == request.chunk_index:
                point = p
                break
        
        if point is None:
            raise HTTPException(
                status_code=404,
                detail=f"Chunk not found: document_id={request.document_id}, chunk_index={request.chunk_index}"
            )
        
        # Extract chunk data
        chunk = {
            'text': point.payload.get('text', ''),
            'document_id': point.payload.get('document_id', ''),
            'page': point.payload.get('page', 0),
            'chunk_index': point.payload.get('chunk_index', 0),
            'metadata': point.payload.get('metadata', {})
        }
        
        # Create a temporary citation for verification
        metadata = chunk.get('metadata', {})
        section_hierarchy = metadata.get('section_hierarchy', [])
        section = ' > '.join(section_hierarchy) if section_hierarchy else None
        
        citation = Citation(
            document_name=request.document_id,  # Will be replaced with actual name
            document_id=request.document_id,
            page_number=chunk.get('page', 0),
            section=section,
            text_span=request.expected_text_span or chunk.get('text', '')[:150],
            claim_text=request.claim_text,
            citation_type=CitationType.PARAPHRASE,  # Default
            chunk_index=request.chunk_index,
            confidence_score=1.0
        )
        
        # Verify the citation
        verification_result = CitationService.verify_citation(citation, chunk)
        
        return verification_result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Verification failed: {str(e)}"
        )
