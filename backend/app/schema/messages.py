from typing import Optional
from uuid import UUID
from pydantic import BaseModel


### Message Schema


class MessageSchema(BaseModel):
    query: str
    conversation_id: Optional[UUID] = None  # Optional conversation ID for continuity
