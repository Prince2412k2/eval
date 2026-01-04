from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CitationType(str, Enum):
    """Types of citations for tracking how information is used"""
    DIRECT_QUOTE = "direct_quote"
    PARAPHRASE = "paraphrase"
    INFERENCE = "inference"


class Citation(BaseModel):
    """
    Citation linking a claim to its source document.
    
    Attributes:
        document_name: Human-readable document name
        document_id: Document hash/ID for lookup
        document_url: Optional URL to the source document.
        page_number: Page number in source document
        section: Section name/hierarchy (e.g., "Returns and Refunds")
        text_span: Exact text from source (50-200 chars)
        claim_text: The claim being cited
        citation_type: How the information is used (quote/paraphrase/inference)
        chunk_index: Index of the chunk this citation references
        confidence_score: Confidence in citation accuracy (0.0-1.0)
    """
    document_name: str
    document_id: str
    document_url: Optional[str] = None
    page_number: int
    section: Optional[str] = None
    text_span: str = Field(..., min_length=10, max_length=300)
    claim_text: str
    citation_type: CitationType
    chunk_index: int
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    
    class Config:
        use_enum_values = True


class VerificationRequest(BaseModel):
    """Request to verify a citation's accuracy"""
    document_id: str
    chunk_index: int
    claim_text: str
    expected_text_span: Optional[str] = None


class VerificationResponse(BaseModel):
    """
    Response from citation verification.
    
    Attributes:
        source_text: The actual text from the source chunk
        context: Surrounding text for context (full chunk or adjacent chunks)
        confidence_score: How well the claim matches the source (0.0-1.0)
        is_accurate: Boolean indicating if citation is accurate
        citation: The verified citation object
        issues: Optional list of issues found (e.g., "text_span_mismatch")
    """
    source_text: str
    context: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    is_accurate: bool
    citation: Optional[Citation] = None
    issues: List[str] = Field(default_factory=list)


class CitationExtractionResponse(BaseModel):
    """
    Structured response from citation extraction LLM.
    Used for parsing JSON output.
    """
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        extra = "allow"
