from pydantic import BaseModel, Field
from datetime import datetime


class DocumentBase(BaseModel):
    """Base schema for documents"""
    mime_type: str
    title: str = Field(..., min_length=1, max_length=255)


class DocumentCreate(DocumentBase):
    """Schema for creating a new document"""
    file_size: int | None = None
    page_count: int | None = None
    chunk_count: int | None = None
    status: str = "processing"


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata"""
    title: str | None = Field(None, max_length=255)
    file_size: int | None = None
    page_count: int | None = None
    chunk_count: int | None = None
    status: str | None = None


class DocumentRead(DocumentBase):
    """Schema for reading document data"""
    hash: str
    created_at: datetime
    file_size: int | None
    page_count: int | None
    chunk_count: int | None
    status: str
    signed_url: str | None = None

    class Config:
        from_attributes = True
