from typing import List, Dict, Optional, Tuple, Iterable
import uuid
from fastembed.common.types import NumpyArray
import numpy as np
from app.schema.chunk import Chunk
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels
from app.service.upload_service import DocumentCRUD


class EmbeddingService:
    @staticmethod
    def embed_chunks(chunks: List[Chunk]) -> Iterable[NumpyArray]:
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
        chunks: List[Chunk],
        embeddings: Iterable[NumpyArray],
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
    async def delete_chunks_by_document(qdrant: AsyncQdrantClient, document_id: str):
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
        score_threshold: Optional[float] = None,
    ) -> List[Dict]:
        """
        Queries Qdrant for the most similar chunks to the given embedding.

        Returns:
            List of dicts with chunk details including text, score, document_id, page, etc.
        """

        results = await qdrant.query_points(
            collection_name=VectorService.COLLECTION_NAME,
            query=query_embedding.tolist(),
            limit=top_k,
            score_threshold=score_threshold,
        )
        chunks_data = []

        for r in results.points:
            if not r.payload:
                continue

            text = r.payload.get("text", "")
            if not text:
                continue

            chunks_data.append(
                {
                    "text": text,
                    "score": r.score,
                    "document_id": r.payload.get("document_id"),
                    "page": r.payload.get("page"),
                    "chunk_index": r.payload.get("chunk_index"),
                    "metadata": r.payload.get("metadata", {}),
                }
            )

        return chunks_data

    @staticmethod
    def format_context(chunks_data: List[Dict]) -> str:
        """
        Format retrieved chunks into a context string.
        Args:
            chunks_data: List of chunk dicts from query_similar_chunks
        Returns:
            Formatted context string
        """
        context = ""
        for chunk in chunks_data:
            page = chunk.get("page", "N/A")
            score = chunk.get("score", 0.0)
            text = chunk.get("text", "")
            context += f"[Page {page}] (Score: {score:.4f})\n{text}\n---\n\n"
        return context

    @staticmethod
    def get_source_documents(chunks_data: List[Dict]) -> Iterable[str]:
        """
        Extract unique document IDs from chunks data.

        Args:
            chunks_data: List of chunk dicts from query_similar_chunks

        Returns:
            List of unique document IDs
        """

        return set(
            chunk.get("document_id", "")
            for chunk in chunks_data
            if chunk.get("document_id")
        )
