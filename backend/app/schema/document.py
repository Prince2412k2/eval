from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime


class DocumentBase(BaseModel):
    owner_id: UUID
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
