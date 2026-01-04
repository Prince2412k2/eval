from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from typing import List

from app.core.database import get_db
from app.service.conversation_service import ConversationService
from app.schema.conversation import (
    ConversationResponse,
    ConversationDetailResponse,
    MessageResponse
)
from app.models import Conversation, Message

conversation_router = APIRouter()


@conversation_router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    List all conversations with pagination.
    
    Args:
        limit: Maximum number of conversations to return
        offset: Number of conversations to skip
        
    Returns:
        List of conversation summaries
    """
    # Get conversations with message count
    query = (
        select(
            Conversation,
            func.count(Message.id).label("message_count")
        )
        .outerjoin(Message, Conversation.id == Message.conversation_id)
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    result = await db.execute(query)
    rows = result.all()
    
    conversations = []
    for conv, msg_count in rows:
        conversations.append(
            ConversationResponse(
                id=conv.id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                documents_discussed=conv.documents_discussed or [],
                topics_covered=conv.topics_covered or [],
                message_count=msg_count or 0
            )
        )
    
    return conversations



@conversation_router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get conversation details with all messages.
    
    Args:
        conversation_id: Conversation UUID
        
    Returns:
        Conversation with messages
    """
    conversation = await ConversationService.get_conversation(
        db, conversation_id, include_messages=True
    )
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        documents_discussed=conversation.documents_discussed or [],
        topics_covered=conversation.topics_covered or [],
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
                sources=msg.sources,
                citations=msg.citations
            )
            for msg in conversation.messages
        ]
    )


@conversation_router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Get conversation messages.
    
    Args:
        conversation_id: Conversation UUID
        limit: Maximum number of messages to return
        
    Returns:
        List of messages
    """
    messages = await ConversationService.get_conversation_history(
        db, conversation_id, last_n=limit
    )
    
    return [
        MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at,
            sources=msg.sources,
            citations=msg.citations
        )
        for msg in messages
    ]


@conversation_router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a conversation and all its messages.
    
    Args:
        conversation_id: Conversation UUID
        
    Returns:
        Success message
    """
    deleted = await ConversationService.delete_conversation(db, conversation_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"message": "Conversation deleted successfully"}
