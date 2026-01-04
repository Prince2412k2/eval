from typing import List, Dict, Optional
from difflib import SequenceMatcher
from app.schema.citation import Citation, CitationType, VerificationResponse


class CitationService:
    """Service for creating, formatting, and verifying citations"""
    
    @staticmethod
    def create_citation_from_chunk(
        chunk: Dict,
        claim_text: str,
        citation_type: CitationType,
        document_name: str,
        text_span: Optional[str] = None,
        confidence_score: float = 1.0
    ) -> Citation:
        """
        Create a Citation object from chunk metadata and claim information.
        
        Args:
            chunk: Chunk dict with metadata
            claim_text: The claim being cited
            citation_type: Type of citation (quote/paraphrase/inference)
            document_name: Human-readable document name
            text_span: Specific text span from chunk (auto-extracted if None)
            confidence_score: Confidence in citation accuracy
            
        Returns:
            Citation object
        """
        # Extract text span if not provided
        if text_span is None:
            chunk_text = chunk.get('text', '')
            # Use first 150 chars as default span
            text_span = chunk_text[:150].strip()
            if len(chunk_text) > 150:
                text_span += "..."
        
        # Ensure text_span is within limits (50-200 chars)
        if len(text_span) < 50 and len(chunk.get('text', '')) >= 50:
            text_span = chunk.get('text', '')[:150].strip()
        
        # Get section hierarchy
        metadata = chunk.get('metadata', {})
        section_hierarchy = metadata.get('section_hierarchy', [])
        section = ' > '.join(section_hierarchy) if section_hierarchy else None
        
        return Citation(
            document_name=document_name,
            document_id=chunk.get('document_id', 'unknown'),
            page_number=chunk.get('page', 0),
            section=section,
            text_span=text_span,
            claim_text=claim_text,
            citation_type=citation_type,
            chunk_index=chunk.get('chunk_index', 0),
            confidence_score=confidence_score
        )
    
    @staticmethod
    def verify_citation(
        citation: Citation,
        chunk: Dict
    ) -> VerificationResponse:
        """
        Verify a citation's accuracy against the source chunk.
        
        Args:
            citation: Citation to verify
            chunk: Source chunk to verify against
            
        Returns:
            VerificationResponse with verification results
        """
        source_text = chunk.get('text', '')
        metadata = chunk.get('metadata', {})
        
        # Build context (include adjacent chunks if available)
        context = source_text
        
        # Calculate confidence score based on text similarity
        issues = []
        
        # Check if text_span exists in source
        if citation.text_span not in source_text:
            # Use fuzzy matching
            similarity = SequenceMatcher(
                None, 
                citation.text_span.lower(), 
                source_text.lower()
            ).ratio()
            
            if similarity < 0.7:
                issues.append("text_span_not_found_in_source")
                confidence_score = similarity
            else:
                issues.append("text_span_fuzzy_match")
                confidence_score = similarity
        else:
            confidence_score = 1.0
        
        # Check claim relevance (basic keyword matching)
        claim_words = set(citation.claim_text.lower().split())
        source_words = set(source_text.lower().split())
        overlap = len(claim_words & source_words) / max(len(claim_words), 1)
        
        if overlap < 0.3:
            issues.append("low_claim_relevance")
            confidence_score = min(confidence_score, overlap + 0.3)
        
        # Determine if accurate
        is_accurate = confidence_score >= 0.7 and len(issues) == 0
        
        return VerificationResponse(
            source_text=source_text,
            context=context,
            confidence_score=confidence_score,
            is_accurate=is_accurate,
            citation=citation,
            issues=issues
        )
    
    @staticmethod
    def format_citations_for_response(
        citations: List[Citation]
    ) -> List[Dict]:
        """
        Format citations for API response.
        
        Args:
            citations: List of Citation objects
            
        Returns:
            List of citation dicts for JSON serialization
        """
        return [citation.model_dump() for citation in citations]
    
    @staticmethod
    def build_citation_extraction_prompt(
        query: str,
        chunks: List[Dict]
    ) -> str:
        """
        Build prompt for citation extraction LLM.
        
        Args:
            query: User's question
            chunks: Context chunks
            
        Returns:
            Formatted prompt string
        """
        # Build numbered chunks
        numbered_chunks = []
        for i, chunk in enumerate(chunks):
            doc_id = chunk.get('document_id', 'Unknown')
            page = chunk.get('page', 'N/A')
            text = chunk.get('text', '')
            metadata = chunk.get('metadata', {})
            section = ' > '.join(metadata.get('section_hierarchy', []))
            
            chunk_str = f"[Chunk {i}]\n"
            chunk_str += f"Document: {doc_id}\n"
            chunk_str += f"Page: {page}\n"
            if section:
                chunk_str += f"Section: {section}\n"
            chunk_str += f"Text: {text}\n"
            
            numbered_chunks.append(chunk_str)
        
        numbered_chunks_str = "\n\n".join(numbered_chunks)
        
        prompt = f"""You are a citation extraction assistant. Analyze the user's question and the provided context chunks to identify which specific parts of the context support potential claims in an answer.

For each relevant piece of information, create a citation with:
1. The chunk number it comes from
2. The exact text span (50-200 characters) from that chunk
3. What claim this supports
4. Citation type: "direct_quote", "paraphrase", or "inference"

User Question: {query}

Context Chunks:
{numbered_chunks_str}

Return ONLY a valid JSON object with a "citations" array in this exact format:
{{
  "citations": [
    {{
      "chunk_index": 0,
      "text_span": "exact text from chunk (50-200 chars)",
      "claim_text": "the claim this supports",
      "citation_type": "direct_quote"
    }}
  ]
}}

Guidelines:
- For direct quotes, use exact wording from the source
- For paraphrases, the claim should closely match the source meaning
- For inferences, the claim should be a logical conclusion from the source
- Be thorough - identify all relevant citations that would support a complete answer
- Ensure text_span is between 50-200 characters
- Return valid JSON only, no additional text"""

        return prompt
    
    @staticmethod
    def extract_best_text_span(
        chunk_text: str,
        claim_text: str,
        min_length: int = 50,
        max_length: int = 200
    ) -> str:
        """
        Extract the most relevant text span from chunk for a claim.
        
        Args:
            chunk_text: Full chunk text
            claim_text: The claim being cited
            min_length: Minimum span length
            max_length: Maximum span length
            
        Returns:
            Best matching text span
        """
        # Simple approach: find sentences containing claim keywords
        claim_words = set(claim_text.lower().split())
        sentences = chunk_text.split('.')
        
        best_sentence = ""
        best_score = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_words = set(sentence.lower().split())
            overlap = len(claim_words & sentence_words)
            
            if overlap > best_score:
                best_score = overlap
                best_sentence = sentence
        
        # Ensure length constraints
        if best_sentence:
            if len(best_sentence) < min_length:
                # Expand to include more context
                idx = chunk_text.find(best_sentence)
                if idx != -1:
                    end_idx = min(idx + max_length, len(chunk_text))
                    return chunk_text[idx:end_idx].strip()
            elif len(best_sentence) > max_length:
                return best_sentence[:max_length].strip() + "..."
            return best_sentence
        
        # Fallback: return first max_length chars
        return chunk_text[:max_length].strip()
