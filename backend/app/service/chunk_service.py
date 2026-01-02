from enum import Enum
import re
from typing import List, Dict, Optional
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
        overlap: int = 150,
        header_content_min: int = 200  # Min chars of content to keep with header
    ):
        """
        Semantic chunker that handles policy document edge cases.
        
        Args:
            max_chunk_size: Maximum characters per chunk
            min_chunk_size: Minimum characters per chunk
            overlap: Character overlap between chunks
            header_content_min: Minimum content to attach to headers
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap = overlap
        self.header_content_min = header_content_min
    
    def chunk_documents(self, documents: List[Dict]) -> List[Chunk]:
        """
        Chunk documents from LlamaIndex: [{'text': markdown, 'page': int}, ...]
        """
        all_chunks = []
        global_chunk_idx = 0
        
        for doc in documents:
            page_chunks = self._chunk_page(doc['text'], doc['page'], global_chunk_idx)
            all_chunks.extend(page_chunks)
            global_chunk_idx += len(page_chunks)
        
        # Link adjacent chunks
        for i in range(len(all_chunks) - 1):
            all_chunks[i].metadata['next_chunk_index'] = all_chunks[i + 1].chunk_index
            all_chunks[i + 1].metadata['prev_chunk_index'] = all_chunks[i].chunk_index
        
        return all_chunks
    
    def _chunk_page(self, text: str, page: int, start_idx: int) -> List[Chunk]:
        """Chunk a single page with edge case handling"""
        # Parse into semantic units
        units = self._parse_semantic_units(text, page)
        
        # Group units into chunks
        chunks = self._group_units_into_chunks(units, page, start_idx)
        
        return chunks
    
    def _parse_semantic_units(self, text: str, page: int) -> List[Dict]:
        """
        Parse markdown into semantic units with edge case detection.
        Returns list of units with metadata about atomicity and structure.
        """
        units = []
        lines = text.split('\n')
        i = 0
        current_section_hierarchy = []
        
        while i < len(lines):
            line = lines[i].rstrip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
            
            # EDGE CASE 1: Headers - must stay with content
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_match:
                level = len(header_match.group(1))
                header_text = header_match.group(2)
                
                # Update section hierarchy
                current_section_hierarchy = current_section_hierarchy[:level-1] + [header_text]
                
                # Collect content after header (at least header_content_min chars)
                content_lines = [line]
                j = i + 1
                content_size = len(line)
                
                while j < len(lines) and content_size < self.header_content_min:
                    next_line = lines[j].rstrip()
                    # Stop at next same-level or higher header
                    next_header = re.match(r'^(#{1,6})\s+', next_line)
                    if next_header and len(next_header.group(1)) <= level:
                        break
                    if next_line:
                        content_lines.append(next_line)
                        content_size += len(next_line)
                    j += 1
                
                units.append({
                    'type': 'header_section',
                    'content': '\n'.join(content_lines),
                    'keep_together': True,
                    'priority': 'high',
                    'section_hierarchy': current_section_hierarchy.copy(),
                    'header_level': level
                })
                i = j
                continue
            
            # EDGE CASE 2: Tables - never split
            if re.match(r'^\|.+\|$', line):
                table_lines = [line]
                j = i + 1
                # Collect all table rows
                while j < len(lines):
                    if re.match(r'^\|.+\|$', lines[j].rstrip()):
                        table_lines.append(lines[j].rstrip())
                        j += 1
                    else:
                        break
                
                units.append({
                    'type': 'table',
                    'content': '\n'.join(table_lines),
                    'keep_together': True,
                    'priority': 'critical',
                    'section_hierarchy': current_section_hierarchy.copy(),
                })
                i = j
                continue
            
            # EDGE CASE 3: Numbered lists - check for cross-references
            if re.match(r'^\d+\.\s+', line):
                list_lines = [line]
                j = i + 1
                
                # Collect entire numbered list
                while j < len(lines):
                    next_line = lines[j].rstrip()
                    # Continue if numbered item or indented continuation
                    if re.match(r'^\d+\.\s+', next_line) or re.match(r'^\s{2,}', next_line):
                        list_lines.append(next_line)
                        j += 1
                    elif not next_line:
                        j += 1
                    else:
                        break
                
                list_content = '\n'.join(list_lines)
                has_refs = self._detect_cross_references(list_content)
                
                units.append({
                    'type': 'numbered_list',
                    'content': list_content,
                    'keep_together': True,  # Always keep numbered lists together
                    'priority': 'critical' if has_refs else 'high',
                    'section_hierarchy': current_section_hierarchy.copy(),
                    'has_cross_references': has_refs
                })
                i = j
                continue
            
            # Bullet lists
            if re.match(r'^[-*+]\s+', line):
                list_lines = [line]
                j = i + 1
                
                while j < len(lines):
                    next_line = lines[j].rstrip()
                    if re.match(r'^[-*+]\s+', next_line) or re.match(r'^\s{2,}', next_line):
                        list_lines.append(next_line)
                        j += 1
                    elif not next_line:
                        j += 1
                    else:
                        break
                
                list_content = '\n'.join(list_lines)
                
                units.append({
                    'type': 'bullet_list',
                    'content': list_content,
                    'keep_together': len(list_content) < self.max_chunk_size,
                    'priority': 'medium',
                    'section_hierarchy': current_section_hierarchy.copy(),
                })
                i = j
                continue
            
            # Code blocks
            if line.startswith('```'):
                code_lines = [line]
                j = i + 1
                while j < len(lines):
                    code_lines.append(lines[j].rstrip())
                    if lines[j].rstrip().startswith('```'):
                        j += 1
                        break
                    j += 1
                
                units.append({
                    'type': 'code_block',
                    'content': '\n'.join(code_lines),
                    'keep_together': True,
                    'priority': 'high',
                    'section_hierarchy': current_section_hierarchy.copy(),
                })
                i = j
                continue
            
            # EDGE CASE 4: Regular paragraphs - split by sentences if needed
            para_lines = [line]
            j = i + 1
            
            while j < len(lines):
                next_line = lines[j].rstrip()
                # Stop at structural elements
                if (not next_line or 
                    re.match(r'^#{1,6}\s+', next_line) or
                    re.match(r'^\d+\.\s+', next_line) or
                    re.match(r'^[-*+]\s+', next_line) or
                    re.match(r'^\|.+\|$', next_line) or
                    next_line.startswith('```')):
                    break
                para_lines.append(next_line)
                j += 1
            
            para_content = '\n'.join(para_lines)
            
            units.append({
                'type': 'paragraph',
                'content': para_content,
                'keep_together': False,  # Can split if needed
                'priority': 'low',
                'section_hierarchy': current_section_hierarchy.copy(),
            })
            i = j
        
        return units
    
    def _detect_cross_references(self, text: str) -> bool:
        """
        Detect if text contains cross-references to other items.
        Examples: "See item 3", "as mentioned in section 2.1", "refer to above"
        """
        patterns = [
            r'\bsee\s+(item|section|point|paragraph|rule)\s+\d+',
            r'\brefer\s+to\s+(item|section|point|paragraph)\s+\d+',
            r'\bas\s+(mentioned|stated|described|noted)\s+(above|below|earlier|in\s+item\s+\d+)',
            r'\b(item|section|point|paragraph)\s+\d+\s+(above|below)',
            r'\bsection\s+\d+(\.\d+)*',
            r'\babove|below|aforementioned|previously\s+mentioned',
        ]
        
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)
    
    def _group_units_into_chunks(
        self, 
        units: List[Dict], 
        page: int, 
        start_idx: int
    ) -> List[Chunk]:
        """
        Group semantic units into chunks, respecting atomicity rules.
        """
        chunks = []
        current_units = []
        current_size = 0
        chunk_idx = start_idx
        
        for i, unit in enumerate(units):
            unit_size = len(unit['content'])
            
            # Critical priority: MUST keep together (tables, numbered lists with refs)
            if unit.get('priority') == 'critical':
                # If unit alone exceeds max_size, we still keep it together
                # This is a design choice: better to have oversized chunk than break critical structure
                if unit_size > self.max_chunk_size:
                    # Save current chunk if exists
                    if current_units:
                        chunks.append(self._create_chunk(current_units, page, chunk_idx))
                        chunk_idx += 1
                        current_units = []
                        current_size = 0
                    
                    # Add oversized unit as its own chunk
                    chunks.append(self._create_chunk([unit], page, chunk_idx))
                    chunk_idx += 1
                    continue
                
                # If adding would exceed max_size, save current chunk
                if current_size + unit_size > self.max_chunk_size and current_units:
                    chunks.append(self._create_chunk(current_units, page, chunk_idx))
                    chunk_idx += 1
                    
                    # Start new chunk with overlap context
                    overlap_unit = self._create_overlap_context(current_units)
                    current_units = [overlap_unit, unit] if overlap_unit else [unit]
                    current_size = sum(len(u['content']) for u in current_units)
                else:
                    current_units.append(unit)
                    current_size += unit_size
                
                continue
            
            # High priority: Try to keep together (headers, lists)
            if unit.get('keep_together'):
                # If too large, split it by sentences
                if unit_size > self.max_chunk_size:
                    if current_units:
                        chunks.append(self._create_chunk(current_units, page, chunk_idx))
                        chunk_idx += 1
                        current_units = []
                        current_size = 0
                    
                    # Split unit by sentences
                    sub_units = self._split_by_sentences(unit)
                    for sub_unit in sub_units:
                        sub_size = len(sub_unit['content'])
                        if current_size + sub_size > self.max_chunk_size and current_units:
                            chunks.append(self._create_chunk(current_units, page, chunk_idx))
                            chunk_idx += 1
                            
                            overlap_unit = self._create_overlap_context(current_units)
                            current_units = [overlap_unit, sub_unit] if overlap_unit else [sub_unit]
                            current_size = sum(len(u['content']) for u in current_units)
                        else:
                            current_units.append(sub_unit)
                            current_size += sub_size
                    continue
                
                # Normal flow
                if current_size + unit_size > self.max_chunk_size and current_units:
                    chunks.append(self._create_chunk(current_units, page, chunk_idx))
                    chunk_idx += 1
                    
                    overlap_unit = self._create_overlap_context(current_units)
                    current_units = [overlap_unit, unit] if overlap_unit else [unit]
                    current_size = sum(len(u['content']) for u in current_units)
                else:
                    current_units.append(unit)
                    current_size += unit_size
                
                continue
            
            # Low priority: Can split freely (paragraphs)
            # Split by sentences
            sentences = self._split_by_sentences(unit)
            for sent_unit in sentences:
                sent_size = len(sent_unit['content'])
                
                if current_size + sent_size > self.max_chunk_size and current_units:
                    chunks.append(self._create_chunk(current_units, page, chunk_idx))
                    chunk_idx += 1
                    
                    overlap_unit = self._create_overlap_context(current_units)
                    current_units = [overlap_unit, sent_unit] if overlap_unit else [sent_unit]
                    current_size = sum(len(u['content']) for u in current_units)
                else:
                    current_units.append(sent_unit)
                    current_size += sent_size
        
        # Add remaining units
        if current_units:
            chunks.append(self._create_chunk(current_units, page, chunk_idx))
        
        return chunks
    
    def _split_by_sentences(self, unit: Dict) -> List[Dict]:
        """Split a unit by sentences for long content"""
        content = unit['content']
        
        # Split by sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        sub_units = []
        for sentence in sentences:
            if sentence.strip():
                sub_units.append({
                    'type': unit['type'],
                    'content': sentence,
                    'keep_together': False,
                    'priority': 'low',
                    'section_hierarchy': unit.get('section_hierarchy', []),
                })
        
        return sub_units if sub_units else [unit]
    
    def _create_overlap_context(self, units: List[Dict]) -> Optional[Dict]:
        """
        Create overlap context from previous chunk.
        Prioritize including section hierarchy (headers) for context.
        """
        if not units:
            return None
        
        # Try to include the last header for context
        for unit in reversed(units):
            if unit['type'] == 'header_section':
                return {
                    'type': 'context_overlap',
                    'content': unit['content'][:self.overlap],
                    'keep_together': False,
                    'priority': 'low',
                    'section_hierarchy': unit.get('section_hierarchy', []),
                }
        
        # Otherwise, use last N characters
        combined = '\n'.join(u['content'] for u in units)
        if len(combined) <= self.overlap:
            overlap_content = combined
        else:
            overlap_content = combined[-self.overlap:]
        
        return {
            'type': 'context_overlap',
            'content': overlap_content,
            'keep_together': False,
            'priority': 'low',
            'section_hierarchy': units[-1].get('section_hierarchy', []),
        }
    
    def _create_chunk(self, units: List[Dict], page: int, chunk_idx: int) -> Chunk:
        """Create a Chunk object from semantic units"""
        content = '\n\n'.join(u['content'] for u in units)
        
        # Aggregate metadata
        chunk_types = list(set(u['type'] for u in units))
        has_cross_refs = any(u.get('has_cross_references', False) for u in units)
        section_hierarchy = units[0].get('section_hierarchy', []) if units else []
        
        # Determine primary type
        priority_order = ['table', 'numbered_list', 'header_section', 'bullet_list', 'code_block', 'paragraph']
        primary_type = 'mixed'
        for ptype in priority_order:
            if ptype in chunk_types:
                primary_type = ptype
                break
        
        return Chunk(
            text=content.strip(),
            page=page,
            chunk_index=chunk_idx,
            metadata={
                'char_count': len(content),
                'chunk_types': chunk_types,
                'primary_type': primary_type,
                'section_hierarchy': section_hierarchy,
                'has_cross_references': has_cross_refs,
                'has_table': 'table' in chunk_types,
                'has_list': any(t in chunk_types for t in ['numbered_list', 'bullet_list']),
                'has_code': 'code_block' in chunk_types,
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
