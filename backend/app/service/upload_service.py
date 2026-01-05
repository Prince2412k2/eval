import hashlib
from datetime import datetime
from typing import Iterable, List
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import AsyncClient
from app.core.supabase import get_supabase

from app.core.config import Defaults
from app.models import Document
from app.schema.document import DocumentCreate, DocumentUpdate, DocumentRead


# Services
class SupabaseFileCRUD:
    @staticmethod
    async def _hash_bytes(file: UploadFile) -> str:
        await file.seek(0)
        data = await file.read()
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _build_path(file_hash: str, filename: str) -> str:
        ext = ""
        if "." in filename:
            ext = "." + filename.split(".")[-1]
        return f"{file_hash[:2]}/{file_hash}{ext}"

    @staticmethod
    async def create(file: UploadFile, file_hash: str, supabase: AsyncClient) -> dict:
        try:
            await file.seek(0)
            content = await file.read()
            content_type: str = file.content_type if file.content_type else ""

            res = await supabase.storage.from_(Defaults.BUCKET_NAME).upload(
                path=file_hash,
                file=content,
                file_options={
                    "content-type": content_type,
                    "cache-control": "3600",
                    "upsert": "true",
                },
            )

            if isinstance(res, dict) and res.get("error"):
                raise RuntimeError(res["error"]["message"])

        except Exception as e:
            raise RuntimeError(f"Supabase upload failed: {e}")

        return {
            "name": file_hash,
            "Defaults.BUCKET_NAME": Defaults.BUCKET_NAME,
            "created_at": datetime.utcnow().isoformat(),
        }

    @staticmethod
    async def read(path: str) -> bytes:
        supabase = await get_supabase()
        try:
            return await supabase.storage.from_(Defaults.BUCKET_NAME).download(path)
        except Exception as e:
            raise FileNotFoundError(f"File not found: {e}")

    @staticmethod
    async def delete(path: str) -> None:
        supabase = await get_supabase()
        try:
            res = await supabase.storage.from_(Defaults.BUCKET_NAME).remove([path])
            if isinstance(res, dict) and res.get("error"):
                raise RuntimeError(res["error"]["message"])
        except Exception as e:
            raise RuntimeError(f"Delete failed: {e}")

    @staticmethod
    async def listall(prefix: str = "") -> List[dict]:
        supabase = await get_supabase()
        try:
            return await supabase.storage.from_(Defaults.BUCKET_NAME).list(prefix)
        except Exception as e:
            raise RuntimeError(f"List failed: {e}")

    @staticmethod
    async def exists(path: str) -> bool:
        try:
            files = await SupabaseFileCRUD.listall(prefix=path.rsplit("/", 1)[0])
            return any(f["name"] == path.split("/")[-1] for f in files)
        except Exception:
            return False


class DocumentCRUD:
    @staticmethod
    async def create(
        db: AsyncSession, document_data: DocumentCreate, doc_hash: str
    ) -> Document:
        """Create a new document if not already stored (deduplicated by hash)."""

        new_doc = Document(**document_data.model_dump(), hash=doc_hash)
        db.add(new_doc)
        await db.commit()
        await db.refresh(new_doc)
        return new_doc

    @staticmethod
    async def update_metadata(
        db: AsyncSession,
        doc_hash: str,
        file_size: int | None = None,
        page_count: int | None = None,
        chunk_count: int | None = None,
        status: str | None = None,
    ) -> Document:
        """Update document metadata after processing"""
        result = await db.execute(select(Document).where(Document.hash == doc_hash))
        document = result.scalar_one_or_none()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with hash {doc_hash} not found",
            )

        if file_size is not None:
            document.file_size = file_size
        if page_count is not None:
            document.page_count = page_count
        if chunk_count is not None:
            document.chunk_count = chunk_count
        if status is not None:
            document.status = status

        await db.commit()
        await db.refresh(document)
        return document

    @staticmethod
    async def get_all(db: AsyncSession) -> list[Document]:
        """Fetch all documents."""
        result = await db.execute(select(Document))
        return list(result.scalars().all())

    @staticmethod
    async def get_by_ids(
        db: AsyncSession,
        ids: Iterable[str],
    ) -> list[Document]:
        if not ids:
            return []

        result = await db.execute(select(Document).where(Document.hash.in_(ids)))
        return list(result.scalars().all())

    @staticmethod
    async def generate_signed_urls(
        supabase: AsyncClient,
        file_hashes: Iterable[str],
        names: Iterable[str],
        expires_in: int = 3600,  # 1 hour
    ) -> dict[str, str | None]:
        results: dict[str, str | None] = {}

        for file_hash, name in zip(file_hashes, names):
            try:
                res = await supabase.storage.from_(
                    Defaults.BUCKET_NAME
                ).create_signed_url(
                    file_hash,
                    expires_in,
                )
                results[name] = res.get("signedURL")
            except Exception as e:
                # log but do not fail batch
                print(f"Error generating signed URL for {file_hash}: {str(e)}")

        return results
