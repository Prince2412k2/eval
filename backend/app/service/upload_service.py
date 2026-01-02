import hashlib
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import AsyncClient
from app.core.supabase import get_supabase

from app.core.config import Defaults
from app.models import Document



#Schema

class DocumentBase(BaseModel):
    mime_type: str
    title: str = Field(..., min_length=1, max_length=255)

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)

class DocumentRead(DocumentBase):
    id: UUID
    created_at: datetime
    hash: str
    signed_url: str | None = None

    class Config:
        from_attributes = True

#Services 

class SupabaseFileCRUD:
    @staticmethod
    async def _hash_bytes(file:UploadFile) -> str:
        await file.seek(0)
        data=await file.read()
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _build_path(file_hash: str, filename: str) -> str:
        ext = ""
        if "." in filename:
            ext = "." + filename.split(".")[-1]
        return f"{file_hash[:2]}/{file_hash}{ext}"

    @staticmethod
    async def create(
        file:UploadFile,
        file_hash:str
    ) -> dict:
        supabase=await get_supabase()
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
            },)

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
        supabase=await get_supabase()
        try:
            return await supabase.storage.from_(Defaults.BUCKET_NAME).download(path)
        except Exception as e:
            raise FileNotFoundError(f"File not found: {e}")

    @staticmethod
    async def delete(path: str) -> None:
        supabase=await get_supabase()
        try:
            res = await supabase.storage.from_(Defaults.BUCKET_NAME).remove([path])
            if isinstance(res, dict) and res.get("error"):
                raise RuntimeError(res["error"]["message"])
        except Exception as e:
            raise RuntimeError(f"Delete failed: {e}")

    @staticmethod
    async def listall(prefix: str = "") -> List[dict]:

        supabase=await get_supabase()
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
        await db.flush()
        await db.refresh(new_doc)
        return new_doc

    @staticmethod
    async def get_all(db: AsyncSession) -> list[Document]:
        """Fetch all documents."""
        result = await db.execute(select(Document))
        return list(result.scalars().all())


    @staticmethod
    async def get_by_id(db: AsyncSession, document_id: UUID, supabase: AsyncClient) -> Document:
        """Fetch a single document by ID."""
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found.",
            )
        document.signed_url = await DocumentCRUD._generate_signed_url(supabase, str(document.hash))
        return document

    @staticmethod
    async def _generate_signed_url(supabase: AsyncClient, file_hash: str) -> str | None:
        try:
            res = await supabase.storage.from_("docs").create_signed_url(file_hash, 3600)  # 1 hour expiration
            return res["signedURL"]
        except Exception as e:
            # Log the error, but don't fail the request if URL generation fails
            print(f"Error generating signed URL for {file_hash}: {e}")
            return None


    @staticmethod
    async def delete(db: AsyncSession, document_id: UUID) -> None:
        """Delete a document by ID."""
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found.",
            )
        await db.delete(document)
        await db.flush()

