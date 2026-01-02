from enum import Enum
import re
from typing import List, Dict
from dataclasses import dataclass

from pydantic import BaseModel

from app.schema.Enums import Strategy
from app.schema.chunk import Chunk



class NaiveChunker:
    def __init__(self, chunk_size: int = 1000, overlap: int = 100):
        """
        Initialize naive chunker with fixed chunk size and overlap.
        
        Args:
            chunk_size: Number of characters per chunk
            overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        
        if overlap >= chunk_size:
            raise ValueError("Overlap must be less than chunk_size")
    
    def chunk_documents(self, documents: List[Dict]) -> List[Chunk]:
        """
        Chunk a list of documents with structure: [{'text': str, 'page': int}, ...]
        
        Args:
            documents: List of dicts with 'text' and 'page' keys
            
        Returns:
            List of Chunk objects
        """
        all_chunks = []
        
        for doc in documents:
            page_chunks = self._chunk_page(doc['text'], doc['page'])
            all_chunks.extend(page_chunks)
        
        return all_chunks
    
    def _chunk_page(self, text: str, page: int) -> List[Chunk]:
        """Chunk a single page's text using fixed size windows"""
        chunks = []
        chunk_idx = 0
        start = 0
        text_length = len(text)
        
        while start < text_length:
            # Calculate end position
            end = start + self.chunk_size
            
            # Extract chunk
            chunk_text = text[start:end]
            
            # Only add non-empty chunks
            if chunk_text.strip():
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        page=page,
                        chunk_index=chunk_idx,
                        metadata={
                            'char_count': len(chunk_text),
                            'start_pos': start,
                            'end_pos': min(end, text_length)
                        }
                    )
                )
                chunk_idx += 1
            
            # Move start position (chunk_size - overlap)
            start += self.chunk_size - self.overlap
        
        return chunks


class SemanticChunker:
    def __init__(
        self,
        max_chunk_size: int = 1000,
        min_chunk_size: int = 100,
        overlap: int = 100
    ):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap = overlap
    
    def chunk_documents(self, documents: List[Dict]) -> List[Chunk]:
        """
        Chunk a list of documents with structure: [{'text': str, 'page': int}, ...]
        """
        all_chunks = []
        
        for doc in documents:
            page_chunks = self._chunk_page(doc['text'], doc['page'])
            all_chunks.extend(page_chunks)
        
        return all_chunks
    
    def _chunk_page(self, text: str, page: int) -> List[Chunk]:
        """Chunk a single page's text"""
        chunks = []
        
        # Split by semantic boundaries (headers, paragraphs, lists)
        sections = self._split_by_semantic_boundaries(text)
        
        current_chunk = []
        current_size = 0
        chunk_idx = 0
        
        for section in sections:
            section_size = len(section)
            
            # If section alone exceeds max size, split it further
            if section_size > self.max_chunk_size:
                # Save current chunk if exists
                if current_chunk:
                    chunks.append(self._create_chunk(
                        ' '.join(current_chunk), page, chunk_idx
                    ))
                    chunk_idx += 1
                    current_chunk = []
                    current_size = 0
                
                # Split large section by sentences
                subsections = self._split_large_section(section)
                for subsection in subsections:
                    chunks.append(self._create_chunk(subsection, page, chunk_idx))
                    chunk_idx += 1
            
            # If adding section exceeds max size, save current chunk
            elif current_size + section_size > self.max_chunk_size and current_chunk:
                chunks.append(self._create_chunk(
                    ' '.join(current_chunk), page, chunk_idx
                ))
                chunk_idx += 1
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = [overlap_text, section] if overlap_text else [section]
                current_size = len(' '.join(current_chunk))
            
            # Add section to current chunk
            else:
                current_chunk.append(section)
                current_size += section_size
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(self._create_chunk(
                ' '.join(current_chunk), page, chunk_idx
            ))
        
        return chunks
    
    def _split_by_semantic_boundaries(self, text: str) -> List[str]:
        """Split text by markdown headers, paragraphs, and lists"""
        sections = []
        
        # Split by headers (# ## ###) and preserve them
        parts = re.split(r'(\n#{1,6}\s+.+?\n)', text)
        
        for part in parts:
            if not part.strip():
                continue
            
            # If it's a header, keep it as is
            if re.match(r'\n#{1,6}\s+', part):
                sections.append(part.strip())
            else:
                # Split by double newlines (paragraphs)
                paragraphs = re.split(r'\n\n+', part)
                for para in paragraphs:
                    para = para.strip()
                    if para:
                        # Handle lists - keep list items together
                        if re.match(r'^[\*\-\+]\s+', para) or re.match(r'^\d+\.\s+', para):
                            sections.append(para)
                        else:
                            sections.append(para)
        
        return sections
    
    def _split_large_section(self, text: str) -> List[str]:
        """Split a large section by sentences"""
        # Split by sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > self.max_chunk_size and current:
                chunks.append(' '.join(current))
                
                # Add overlap
                overlap_sentences = self._get_last_sentences(current, self.overlap)
                current = overlap_sentences + [sentence]
                current_size = len(' '.join(current))
            else:
                current.append(sentence)
                current_size += sentence_size
        
        if current:
            chunks.append(' '.join(current))
        
        return chunks
    
    def _get_overlap_text(self, chunks: List[str]) -> str:
        """Get overlap text from the end of current chunks"""
        if not chunks:
            return ""
        
        combined = ' '.join(chunks)
        if len(combined) <= self.overlap:
            return combined
        
        return combined[-self.overlap:]
    
    def _get_last_sentences(self, sentences: List[str], target_size: int) -> List[str]:
        """Get last few sentences up to target size"""
        result = []
        size = 0
        
        for sentence in reversed(sentences):
            if size + len(sentence) > target_size:
                break
            result.insert(0, sentence)
            size += len(sentence)
        
        return result
    
    def _create_chunk(self, text: str, page: int, chunk_idx: int) -> Chunk:
        """Create a Chunk object with metadata"""
        return Chunk(
            text=text.strip(),
            page=page,
            chunk_index=chunk_idx,
            metadata={
                'char_count': len(text),
                'has_header': bool(re.search(r'#{1,6}\s+', text)),
                'has_list': bool(re.search(r'^[\*\-\+\d+\.]\s+', text, re.MULTILINE))
            }
        )

class ChunkerFactory:
    @staticmethod
    def get_chunker(strategy: Strategy) -> NaiveChunker | SemanticChunker:
        match strategy:
            case Strategy.NAIVE:
                return NaiveChunker()
            case Strategy.SEMANTIC:
                return SemanticChunker()
            case _:
                raise ValueError(f"Unknown chunking strategy: {strategy}")
