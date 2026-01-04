from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class MessageResponse(BaseModel):
    """Response model for a single message"""
    id: UUID
    role: str
    content: str
    created_at: datetime
    sources: Optional[List[str]] = None
    citations: Optional[List[dict]] = None
    
    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Response model for conversation summary"""
    id: UUID
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    documents_discussed: List[str]
    topics_covered: List[str]
    message_count: int = 0
    
    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    """Response model for conversation with messages"""
    id: UUID
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    documents_discussed: List[str]
    topics_covered: List[str]
    messages: List[MessageResponse]
    
    class Config:
        from_attributes = True
