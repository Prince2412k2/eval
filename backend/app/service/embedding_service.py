
from typing import List, Dict, Optional, Tuple, Iterable
from dataclasses import dataclass, asdict
import uuid
import numpy as np
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels



class EmbeddingService:
    @staticmethod
    def embed_chunks(chunks: List[Chunk]) -> List[np.ndarray]:
        """
        Embed chunk texts and return embeddings.
        Returns vectors of 384 dimensions.
        """
        from app.core.embedding import get_embbed
        texts = [chunk.text for chunk in chunks]
        return get_embbed().embed(texts)
    
    @staticmethod
    def embed_string(query: str) -> np.ndarray:
        """Embed a single query string"""
        from app.core.embedding import get_embbed
        embeddings = iter(get_embbed().embed([query]))
        return next(embeddings)


class VectorService:
    COLLECTION_NAME = "documents"
    
    @staticmethod
    async def upsert_chunks(
        qdrant: AsyncQdrantClient,
        document_id: str,
        owner_id: Optional[uuid.UUID],
        chunks: List[Chunk],
        embeddings: Iterable[np.ndarray],
    ):
        """
        Inserts or updates vector chunks for a document into Qdrant.
        Each chunk includes its text, metadata, page number, and chunk index.
        """
        points = []
        for chunk, embedding in zip(chunks, embeddings):
            chunk_uuid = uuid.uuid4()
            
            # Build comprehensive payload
            payload = {
                "document_id": document_id,
                "owner_id": str(owner_id) if owner_id else None,
                "text": chunk.text,
                "page": chunk.page,
                "chunk_index": chunk.chunk_index,
                "metadata": chunk.metadata,
            }
            
            points.append(
                qmodels.PointStruct(
                    id=str(chunk_uuid),
                    vector=embedding.tolist(),
                    payload=payload,
                )
            )
        
        # Batch upsert for efficiency
        await qdrant.upsert(
            collection_name=VectorService.COLLECTION_NAME,
            points=points,
            wait=True,
        )
    
    @staticmethod
    async def delete_chunks_by_document(
        qdrant: AsyncQdrantClient, 
        document_id: str
    ):
        """Deletes all chunks for a given document_id from Qdrant."""
        await qdrant.delete(
            collection_name=VectorService.COLLECTION_NAME,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )
    
    @staticmethod
    async def query_similar_chunks(
        qdrant: AsyncQdrantClient,
        query_embedding: np.ndarray,
        top_k: int = 15,
        owner_id: Optional[uuid.UUID] = None,
        document_ids: Optional[List[str]] = None,
        score_threshold: Optional[float] = None,
    ) -> Tuple[str, List[Dict], List[str]]:
        """
        Queries Qdrant for the most similar chunks to the given embedding.
        
        Returns:
            - context: Formatted string with all chunk texts
            - chunks_metadata: List of dicts with chunk details
            - source_doc_ids: List of unique document IDs
        """
        filters = []
        
        if owner_id is not None:
            filters.append(
                qmodels.FieldCondition(
                    key="owner_id", 
                    match=qmodels.MatchValue(value=str(owner_id))
                )
            )
        
        if document_ids:
            filters.append(
                qmodels.FieldCondition(
                    key="document_id",
                    match=qmodels.MatchAny(any=document_ids),
                )
            )
        
        query_filter = qmodels.Filter(must=filters) if filters else None
        
        results = await qdrant.search(
            collection_name=VectorService.COLLECTION_NAME,
            query_vector=query_embedding.tolist(),
            query_filter=query_filter,
            limit=top_k,
            score_threshold=score_threshold,
        )
        
        context = ""
        chunks_metadata = []
        source_doc_ids = set()
        
        for r in results:
            if not r.payload:
                continue
            
            text = r.payload.get("text", "")
            if not text:
                continue
            
            doc_id = r.payload.get("document_id")
            source_doc_ids.add(doc_id)
            
            # Build context string
            context += f"[Page {r.payload.get('page', 'N/A')}] (Score: {r.score:.4f})\n{text}\n---\n\n"
            
            # Collect metadata for each chunk
            chunks_metadata.append({
                "text": text,
                "score": r.score,
                "document_id": doc_id,
                "page": r.payload.get("page"),
                "chunk_index": r.payload.get("chunk_index"),
                "metadata": r.payload.get("metadata", {}),
            })
        
        return context, chunks_metadata, list(source_doc_ids)
