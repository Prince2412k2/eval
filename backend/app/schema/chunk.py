from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """Structured metadata for document chunks"""
    
    # Basic chunk info
    char_count: Optional[int] = None
    start_pos: Optional[int] = None
    end_pos: Optional[int] = None
    
    # Semantic chunking metadata
    chunk_types: Optional[List[str]] = None
    primary_type: Optional[str] = None
    section_hierarchy: Optional[List[str]] = Field(default_factory=list)
    
    # Content flags
    has_cross_references: Optional[bool] = False
    has_table: Optional[bool] = False
    has_list: Optional[bool] = False
    has_code: Optional[bool] = False
    
    # Adjacency tracking
    prev_chunk_index: Optional[int] = None
    next_chunk_index: Optional[int] = None
    
    # Document metadata
    created_at: Optional[str] = None
    document_version: Optional[str] = None
    
    # Allow additional fields for flexibility
    class Config:
        extra = "allow"


class Chunk(BaseModel):
    """Document chunk with text, location, and metadata"""
    
    text: str
    page: int
    chunk_index: int
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Optional fields for reranking
    score: Optional[float] = None
    rerank_score: Optional[float] = None
    score_breakdown: Optional[Dict[str, Any]] = None
    is_adjacent_context: Optional[bool] = False
    
    class Config:
        # Allow extra fields for backward compatibility
        extra = "allow"
