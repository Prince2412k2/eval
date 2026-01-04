"""
Documents management API endpoints

Provides endpoints for:
- Listing all documents with metadata
- Getting document statistics
- Deleting documents (full cleanup from all systems)
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from supabase import AsyncClient

from app.core.database import get_db
from app.core.supabase import get_supabase
from app.core.vector import get_qdrant
from app.models import Document
from app.service.upload_service import DocumentCRUD, SupabaseFileCRUD
from app.service.embedding_service import VectorService
from qdrant_client import AsyncQdrantClient
from app.core.config import Defaults

documents_router = APIRouter()


@documents_router.get("/documents")
async def list_documents(
    db: AsyncSession = Depends(get_db), supabase: AsyncClient = Depends(get_supabase)
):
    """
    List all documents with metadata

    Returns:
        List of documents with file size, page count, chunk count, etc.
    """
    try:
        # Get all documents
        result = await db.execute(select(Document).order_by(Document.created_at.desc()))
        documents = result.scalars().all()

        # Format response
        docs_list = []
        for doc in documents:
            # Generate signed URL
            try:
                url_res = await supabase.storage.from_(
                    Defaults.BUCKET_NAME
                ).create_signed_url(doc.hash, 3600)
                signed_url = url_res.get("signedURL")
            except:
                signed_url = None

            docs_list.append(
                {
                    "id": str(doc.hash),
                    "title": doc.title,
                    "hash": doc.hash,
                    "mime_type": doc.mime_type,
                    "created_at": doc.created_at.isoformat(),
                    "file_size": doc.file_size,
                    "page_count": doc.page_count,
                    "chunk_count": doc.chunk_count,
                    "status": doc.status or "indexed",
                    "signed_url": signed_url,
                }
            )

        return {"documents": docs_list, "total": len(docs_list)}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}",
        )


@documents_router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    supabase: AsyncClient = Depends(get_supabase),
    qdrant: AsyncQdrantClient = Depends(get_qdrant),
):
    """
    Delete a document from all systems

    Steps:
    1. Delete from PostgreSQL
    2. Delete vectors from Qdrant
    3. Delete file from Supabase Storage

    Args:
        document_id: Document UUID or hash
    """
    try:
        # Get document
        result = await db.execute(
            select(Document).where(Document.hash == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found",
            )

        doc_hash = document.hash
        doc_title = document.title

        # Step 1: Delete from Qdrant
        try:
            await VectorService.delete_chunks_by_document(qdrant, doc_hash)
            print(f"✅ Deleted vectors for document {doc_hash} from Qdrant")
        except Exception as e:
            print(f"⚠️  Failed to delete from Qdrant: {e}")

        # Step 2: Delete from Supabase Storage
        try:
            await supabase.storage.from_(Defaults.BUCKET_NAME).remove([doc_hash])
            print(f"✅ Deleted file {doc_hash} from Supabase")
        except Exception as e:
            print(f"⚠️  Failed to delete from Supabase: {e}")

        # Step 3: Delete from PostgreSQL
        await db.delete(document)
        await db.commit()
        print(f"✅ Deleted document {doc_hash} from PostgreSQL")

        return {
            "success": True,
            "message": f"Document '{doc_title}' deleted successfully",
            "document_id": doc_hash,
            "hash": doc_hash,
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}",
        )


@documents_router.get("/documents/{document_id}/stats")
async def get_document_stats(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    qdrant: AsyncQdrantClient = Depends(get_qdrant),
):
    """
    Get detailed statistics for a document

    Returns:
        Document metadata, chunk count, query statistics
    """
    try:
        # Get document
        result = await db.execute(
            select(Document).where(Document.hash == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found",
            )

        # Get chunk count from Qdrant
        try:
            scroll_result = await qdrant.scroll(
                collection_name=Defaults.COLLECTION_NAME,
                scroll_filter={
                    "must": [{"key": "document_id", "match": {"value": document.hash}}]
                },
                limit=1,
                with_payload=False,
                with_vectors=False,
            )
            # Get total count
            chunk_count = len(scroll_result[0]) if scroll_result else 0
        except:
            chunk_count = document.chunk_count or 0

        return {
            "document_id": document.hash,
            "title": document.title,
            "hash": document.hash,
            "mime_type": document.mime_type,
            "created_at": document.created_at.isoformat(),
            "file_size": document.file_size,
            "page_count": document.page_count,
            "chunk_count": chunk_count,
            "status": document.status or "indexed",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document stats: {str(e)}",
        )
