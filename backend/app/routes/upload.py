from fastapi import APIRouter, Depends, UploadFile, File
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import AsyncClient
from app.core.config import Defaults
from app.core.supabase import get_supabase
from app.service.chunk_service import ChunkerFactory
from app.service.embedding_service import EmbeddingService, VectorService
from app.service.parser_service import DocumentService
from app.service.upload_service import DocumentCRUD, DocumentCreate, SupabaseFileCRUD
from app.core.database import get_db
from app.core.vector import get_qdrant
from sqlalchemy.exc import IntegrityError

upload_router = APIRouter()


@upload_router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    qdrant: AsyncQdrantClient = Depends(get_qdrant),
    supabase: AsyncClient = Depends(get_supabase),
):
    file_hash = await SupabaseFileCRUD._hash_bytes(file)
    data = DocumentCreate(
        mime_type=file.content_type or "", title=file.filename or "Untitled"
    )

    try:
        doc = await DocumentCRUD.create(db, data, file_hash)
        await SupabaseFileCRUD.create(file, file_hash, supabase)
        parsed_docs = await DocumentService.parse(file)
        chunker = ChunkerFactory.get_chunker(Defaults.CHUNK_STRATEGY)
        chunks = chunker.chunk_documents(parsed_docs)
        embeddings = EmbeddingService.embed_chunks(chunks)
        await VectorService.upsert_chunks(qdrant, file_hash, chunks, embeddings)
        return {"message": "File uploaded successfully", "file": doc}
    except IntegrityError:
        return {"error": "File already exists"}
    except Exception as e:
        return {"error": str(e)}
