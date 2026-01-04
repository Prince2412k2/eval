import uuid
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship

Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = {"schema": "public"}

    hash = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=True)
    mime_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, index=True, nullable=True)  # Optional for now
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Metadata tracking
    documents_discussed = Column(ARRAY(String), default=list)
    topics_covered = Column(ARRAY(String), default=list)
    
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = {"schema": "public"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("public.conversations.id"), nullable=False
    )
    role = Column(
        Enum("user", "assistant", "system", name="message_roles"), nullable=False
    )
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Enhanced metadata
    sources = Column(ARRAY(String), nullable=True)
    citations = Column(JSONB, nullable=True)
    extra_metadata = Column(JSONB, nullable=True)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    
    conversation = relationship("Conversation", back_populates="messages")
