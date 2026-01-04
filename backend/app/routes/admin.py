"""
Admin API endpoints for metrics and system statistics
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models import Document, Conversation, Message, TokenUsage

admin_router = APIRouter()


@admin_router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    """
    Get system-wide metrics for admin dashboard.
    
    Returns:
        - Total documents count
        - Total conversations count
        - Total messages count
        - Token usage statistics
    """
    try:
        # Count documents
        doc_result = await db.execute(select(func.count(Document.hash)))
        total_documents = doc_result.scalar() or 0
        
        # Count conversations
        conv_result = await db.execute(select(func.count(Conversation.id)))
        total_conversations = conv_result.scalar() or 0
        
        # Count messages
        msg_result = await db.execute(select(func.count(Message.id)))
        total_messages = msg_result.scalar() or 0
        
        # Token usage statistics
        token_stats = await db.execute(
            select(
                func.sum(TokenUsage.total_tokens).label("total_tokens"),
                func.sum(TokenUsage.prompt_tokens).label("prompt_tokens"),
                func.sum(TokenUsage.completion_tokens).label("completion_tokens"),
                func.sum(TokenUsage.cost_usd).label("total_cost")
            )
        )
        token_data = token_stats.first()
        
        return {
            "documents": {
                "total": total_documents
            },
            "conversations": {
                "total": total_conversations
            },
            "messages": {
                "total": total_messages
            },
            "tokens": {
                "total_tokens": int(token_data.total_tokens or 0),
                "prompt_tokens": int(token_data.prompt_tokens or 0),
                "completion_tokens": int(token_data.completion_tokens or 0),
                "total_cost_usd": float(token_data.total_cost or 0.0)
            }
        }
    
    except Exception as e:
        return {
            "error": str(e),
            "documents": {"total": 0},
            "conversations": {"total": 0},
            "messages": {"total": 0},
            "tokens": {
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_cost_usd": 0.0
            }
        }
