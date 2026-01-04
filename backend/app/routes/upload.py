from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from qdrant_client.async_qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import AsyncClient
from app.core.config import Defaults
from app.core.supabase import get_supabase
from app.service.chunk_service import ChunkerFactory
from app.service.embedding_service import EmbeddingService, VectorService
from app.service.parser_service import DocumentService
from app.service.upload_service import DocumentCRUD, DocumentCreate, SupabaseFileCRUD
from app.core.database import get_db, AsyncSessionLocal
from app.core.vector import get_qdrant
from sqlalchemy.exc import IntegrityError
from typing import List
import logging
import json
from app.schema.upload_progress import UploadProgress, FileStage, FileStatus

logger = logging.getLogger(__name__)

upload_router = APIRouter()


@upload_router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    qdrant: AsyncQdrantClient = Depends(get_qdrant),
    supabase: AsyncClient = Depends(get_supabase),
):
    """
    Upload and process a document

    Steps:
    1. Calculate file hash and size
    2. Create document record with status="processing"
    3. Upload to Supabase bucket
    4. Parse document to extract pages
    5. Chunk documents
    6. Generate embeddings and store in Qdrant
    7. Update document metadata with page_count, chunk_count, status="indexed"
    """
    # Calculate file hash and size
    logger.info(f"Starting upload for file: {file.filename}")
    file_hash = await SupabaseFileCRUD._hash_bytes(file)
    await file.seek(0)
    file_content = await file.read()
    file_size = len(file_content)
    await file.seek(0)
    logger.info(f"File hash calculated: {file_hash}, size: {file_size} bytes")

    # Create initial document with status="processing"
    data = DocumentCreate(
        mime_type=file.content_type or "",
        title=file.filename or "Untitled",
        file_size=file_size,
        status="processing",
    )

    try:
        # Create document record
        logger.info(f"Creating document record for {file_hash}")
        doc = await DocumentCRUD.create(db, data, file_hash)
        logger.info(f"Document record created: {doc.hash}")

        # Upload to Supabase
        logger.info(f"Uploading file to Supabase: {file_hash}")
        await SupabaseFileCRUD.create(file, file_hash, supabase)
        logger.info(f"File uploaded to Supabase successfully")

        # Parse document
        logger.info(f"Parsing document: {file_hash}")
        parsed_docs = await DocumentService.parse(file)
        page_count = len(parsed_docs)
        logger.info(f"Document parsed: {page_count} pages extracted")

        # Chunk documents
        logger.info(f"Chunking document with strategy: {Defaults.CHUNK_STRATEGY}")
        chunker = ChunkerFactory.get_chunker(Defaults.CHUNK_STRATEGY)
        chunks = chunker.chunk_documents(parsed_docs)
        chunk_count = len(chunks)
        logger.info(f"Document chunked: {chunk_count} chunks created")

        # Generate embeddings and store
        logger.info(f"Generating embeddings for {chunk_count} chunks")
        embeddings = EmbeddingService.embed_chunks(chunks)
        logger.info(f"Embeddings generated, storing in Qdrant")
        await VectorService.upsert_chunks(qdrant, file_hash, chunks, embeddings)
        logger.info(f"Vectors stored in Qdrant successfully")

        # Update document with metadata and mark as indexed
        logger.info(f"Updating document metadata: {file_hash}")
        updated_doc = await DocumentCRUD.update_metadata(
            db=db,
            doc_hash=file_hash,
            page_count=page_count,
            chunk_count=chunk_count,
            status="indexed",
        )
        logger.info(
            f"✅ Upload complete: {file.filename} ({page_count} pages, {chunk_count} chunks)"
        )

        return {
            "message": "File uploaded successfully",
            "file": {
                "hash": updated_doc.hash,
                "title": updated_doc.title,
                "mime_type": updated_doc.mime_type,
                "file_size": updated_doc.file_size,
                "page_count": updated_doc.page_count,
                "chunk_count": updated_doc.chunk_count,
                "status": updated_doc.status,
                "created_at": updated_doc.created_at.isoformat(),
            },
        }

    except IntegrityError:
        # Document already exists (duplicate hash)
        logger.warning(f"Duplicate file upload attempted: {file_hash}")
        await db.rollback()
        return {"error": "File already exists", "hash": file_hash}

    except Exception as e:
        # Mark as failed if document was created
        logger.error(f"❌ Upload failed for {file.filename}: {str(e)}", exc_info=True)
        await db.rollback()
        try:
            await DocumentCRUD.update_metadata(
                db=db, doc_hash=file_hash, status="failed"
            )
        except:
            pass  # Document may not exist yet

        return {"error": str(e), "status": "failed", "hash": file_hash}


@upload_router.post("/bulk", response_class=StreamingResponse)
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    qdrant: AsyncQdrantClient = Depends(get_qdrant),
    supabase: AsyncClient = Depends(get_supabase),
):
    """
    Upload and process multiple documents with real-time progress streaming via SSE
    
    Streams progress updates for each file through all processing stages:
    - hashing → uploading → parsing → chunking → embedding → storing → finished
    """
    logger.info(f"Starting SSE bulk upload for {len(files)} files")
    
    async def event_stream():
        """Stream progress updates for all files"""
        
        for file in files:
            file_hash = None
            filename = file.filename or "Untitled"
            
            # Create independent session for this file
            async with AsyncSessionLocal() as db:
                try:
                    # Stage 1: Hashing
                    yield f"data: {json.dumps(UploadProgress(filename=filename, stage=FileStage.HASHING, status=FileStatus.PROCESSING, message='Calculating file hash').model_dump())}\n\n"
                    
                    file_hash = await SupabaseFileCRUD._hash_bytes(file)
                    await file.seek(0)
                    file_content = await file.read()
                    file_size = len(file_content)
                    await file.seek(0)
                    
                    logger.info(f"[SSE] {filename}: hash={file_hash}, size={file_size}")
                    
                    # Stage 2: Uploading to DB and Supabase
                    yield f"data: {json.dumps(UploadProgress(filename=filename, stage=FileStage.UPLOADING, status=FileStatus.PROCESSING, message='Uploading file', hash=file_hash, file_size=file_size).model_dump())}\n\n"
                    
                    data = DocumentCreate(
                        mime_type=file.content_type or "",
                        title=filename,
                        file_size=file_size,
                        status="processing",
                    )
                    
                    doc = await DocumentCRUD.create(db, data, file_hash)
                    await SupabaseFileCRUD.create(file, file_hash, supabase)
                    
                    # Stage 3: Parsing
                    yield f"data: {json.dumps(UploadProgress(filename=filename, stage=FileStage.PARSING, status=FileStatus.PROCESSING, message='Parsing document', hash=file_hash).model_dump())}\n\n"
                    
                    parsed_docs = await DocumentService.parse(file)
                    page_count = len(parsed_docs)
                    logger.info(f"[SSE] {filename}: {page_count} pages parsed")
                    
                    # Stage 4: Chunking
                    yield f"data: {json.dumps(UploadProgress(filename=filename, stage=FileStage.CHUNKING, status=FileStatus.PROCESSING, message=f'Chunking {page_count} pages', hash=file_hash, page_count=page_count).model_dump())}\n\n"
                    
                    chunker = ChunkerFactory.get_chunker(Defaults.CHUNK_STRATEGY)
                    chunks = chunker.chunk_documents(parsed_docs)
                    chunk_count = len(chunks)
                    logger.info(f"[SSE] {filename}: {chunk_count} chunks created")
                    
                    # Stage 5: Embedding
                    yield f"data: {json.dumps(UploadProgress(filename=filename, stage=FileStage.EMBEDDING, status=FileStatus.PROCESSING, message=f'Generating embeddings for {chunk_count} chunks', hash=file_hash, chunk_count=chunk_count).model_dump())}\n\n"
                    
                    embeddings = EmbeddingService.embed_chunks(chunks)
                    
                    # Stage 6: Storing
                    yield f"data: {json.dumps(UploadProgress(filename=filename, stage=FileStage.STORING, status=FileStatus.PROCESSING, message='Storing vectors in Qdrant', hash=file_hash).model_dump())}\n\n"
                    
                    await VectorService.upsert_chunks(qdrant, file_hash, chunks, embeddings)
                    
                    # Stage 7: Updating metadata
                    yield f"data: {json.dumps(UploadProgress(filename=filename, stage=FileStage.UPDATING, status=FileStatus.PROCESSING, message='Updating metadata', hash=file_hash).model_dump())}\n\n"
                    
                    updated_doc = await DocumentCRUD.update_metadata(
                        db=db,
                        doc_hash=file_hash,
                        page_count=page_count,
                        chunk_count=chunk_count,
                        status="indexed",
                    )
                    
                    # Stage 8: Finished
                    logger.info(f"[SSE] ✅ {filename}: Complete")
                    yield f"data: {json.dumps(UploadProgress(filename=filename, stage=FileStage.FINISHED, status=FileStatus.SUCCESS, message='Upload complete', hash=file_hash, file_size=file_size, page_count=page_count, chunk_count=chunk_count).model_dump())}\n\n"
                    
                except IntegrityError:
                    logger.warning(f"[SSE] ⚠ {filename}: Duplicate (hash={file_hash})")
                    await db.rollback()
                    yield f"data: {json.dumps(UploadProgress(filename=filename, stage=FileStage.FINISHED, status=FileStatus.DUPLICATE, message='File already exists', hash=file_hash).model_dump())}\n\n"
                    
                except Exception as e:
                    logger.error(f"[SSE] ❌ {filename}: {str(e)}")
                    await db.rollback()
                    
                    # Try to mark as failed
                    if file_hash:
                        try:
                            await DocumentCRUD.update_metadata(db=db, doc_hash=file_hash, status="failed")
                        except:
                            pass
                    
                    yield f"data: {json.dumps(UploadProgress(filename=filename, stage=FileStage.FINISHED, status=FileStatus.FAILED, message='Upload failed', error=str(e), hash=file_hash).model_dump())}\n\n"
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")
