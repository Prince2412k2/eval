import uuid
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, DateTime,func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

Base = declarative_base()
# --- association table ---

class Document(Base):
    __tablename__ = "documents"

    hash = Column(String,primary_key=True, index=True)
    title = Column(String, nullable=True)
    mime_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

