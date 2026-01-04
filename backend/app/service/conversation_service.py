from typing import List, Optional, Dict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from app.models import Conversation, Message
import re


class ConversationService:
    """Service for managing conversations and messages"""
    
    @staticmethod
    async def create_conversation(
        db: AsyncSession,
        user_id: Optional[UUID] = None,
        title: Optional[str] = None
    ) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            db: Database session
            user_id: Optional user ID
            title: Optional conversation title
            
        Returns:
            Created Conversation object
        """
        conversation = Conversation(
            user_id=user_id,
            title=title,
            documents_discussed=[],
            topics_covered=[]
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return conversation
    
    @staticmethod
    async def get_conversation(
        db: AsyncSession,
        conversation_id: UUID,
        include_messages: bool = False
    ) -> Optional[Conversation]:
        """
        Get conversation by ID.
        
        Args:
            db: Database session
            conversation_id: Conversation UUID
            include_messages: Whether to load messages
            
        Returns:
            Conversation object or None
        """
        query = select(Conversation).where(Conversation.id == conversation_id)
        
        if include_messages:
            query = query.options(selectinload(Conversation.messages))
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def add_message(
        db: AsyncSession,
        conversation_id: UUID,
        role: str,
        content: str,
        sources: Optional[List[str]] = None,
        citations: Optional[List[Dict]] = None,
        extra_metadata: Optional[Dict] = None
    ) -> Message:
        """
        Add a message to a conversation.
        
        Args:
            db: Database session
            conversation_id: Conversation UUID
            role: Message role (user/assistant/system)
            content: Message content
            sources: Optional list of source document IDs
            citations: Optional list of citations
            extra_metadata: Optional additional metadata
            
        Returns:
            Created Message object
        """
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=sources or [],
            citations=citations,
            extra_metadata=extra_metadata
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        
        # Update conversation updated_at
        await db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=message.created_at)
        )
        await db.commit()
        
        return message
    
    @staticmethod
    async def get_conversation_history(
        db: AsyncSession,
        conversation_id: UUID,
        last_n: int = 10
    ) -> List[Message]:
        """
        Get last N messages from a conversation.
        
        Args:
            db: Database session
            conversation_id: Conversation UUID
            last_n: Number of recent messages to retrieve
            
        Returns:
            List of Message objects (oldest to newest)
        """
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(last_n)
        )
        
        result = await db.execute(query)
        messages = result.scalars().all()
        
        # Reverse to get chronological order (oldest to newest)
        return list(reversed(messages))
    
    @staticmethod
    def build_context_from_history(
        messages: List[Message],
        max_messages: int = 5
    ) -> str:
        """
        Build context string from message history for LLM.
        
        Args:
            messages: List of Message objects
            max_messages: Maximum number of messages to include
            
        Returns:
            Formatted context string
        """
        if not messages:
            return ""
        
        # Take last N messages
        recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
        
        context_parts = []
        for msg in recent_messages:
            role = msg.role.upper()
            context_parts.append(f"{role}: {msg.content}")
        
        return "\n".join(context_parts)
    
    @staticmethod
    async def update_conversation_metadata(
        db: AsyncSession,
        conversation_id: UUID,
        documents: Optional[List[str]] = None,
        topics: Optional[List[str]] = None
    ):
        """
        Update conversation metadata (documents discussed, topics covered).
        
        Args:
            db: Database session
            conversation_id: Conversation UUID
            documents: List of document IDs to add
            topics: List of topics to add
        """
        conversation = await ConversationService.get_conversation(db, conversation_id)
        if not conversation:
            return
        
        # Merge new documents (avoid duplicates)
        if documents:
            existing_docs = set(conversation.documents_discussed or [])
            existing_docs.update(documents)
            conversation.documents_discussed = list(existing_docs)
        
        # Merge new topics (avoid duplicates)
        if topics:
            existing_topics = set(conversation.topics_covered or [])
            existing_topics.update(topics)
            conversation.topics_covered = list(existing_topics)
        
        await db.commit()
        await db.refresh(conversation)
    
    @staticmethod
    def extract_topics_from_query(query: str) -> List[str]:
        """
        Extract key topics from user query using simple keyword extraction.
        
        Args:
            query: User query string
            
        Returns:
            List of extracted topics
        """
        # Simple topic extraction: find important nouns/phrases
        # Remove common question words
        stop_words = {'what', 'when', 'where', 'who', 'why', 'how', 'is', 'are', 'the', 'a', 'an', 'can', 'do', 'does'}
        
        # Clean and tokenize
        words = re.findall(r'\b\w+\b', query.lower())
        
        # Filter stop words and short words
        topics = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Take unique topics (first 5)
        unique_topics = []
        seen = set()
        for topic in topics:
            if topic not in seen:
                unique_topics.append(topic)
                seen.add(topic)
                if len(unique_topics) >= 5:
                    break
        
        return unique_topics
    
    @staticmethod
    async def delete_conversation(
        db: AsyncSession,
        conversation_id: UUID
    ) -> bool:
        """
        Delete a conversation and all its messages.
        
        Args:
            db: Database session
            conversation_id: Conversation UUID
            
        Returns:
            True if deleted, False if not found
        """
        conversation = await ConversationService.get_conversation(db, conversation_id)
        if not conversation:
            return False
        
        await db.delete(conversation)
        await db.commit()
        return True
