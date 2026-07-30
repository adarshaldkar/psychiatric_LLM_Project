"""
Structure-aware two-level parent-child chunker.

PARENT chunks (400-1200 tokens): preserve logical sections → sent to LLM
CHILD  chunks (150-300  tokens): precise sub-segments     → embedded & searched

Algorithm:
  1. Split full text into logical sections (headings, paragraphs)
  2. Build parent chunks by merging/splitting sections to fit PARENT range
  3. For each parent, slide a window to produce child chunks
  4. Each child stores parent_chunk_id for later retrieval
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional

import tiktoken

from app.core.config import settings

logger = logging.getLogger(__name__)

# Use cl100k_base (same tokenizer as text-embedding-3-small)
_ENC = tiktoken.get_encoding('cl100k_base')

# Regex patterns to detect section headings
_HEADING_RE = re.compile(
    r'^(?:'
    r'#{1,3}\s+'                       # ## Markdown heading
    r'|(?:Chapter|Section|Part)\s+\d'  # Chapter 12
    r'|\d+\.\s+[A-Z]'                  # 1. Introduction
    r'|\d+\.\d+\s+[A-Z]'              # 1.2 Sub-section
    r'|[A-Z][A-Z\s]{4,}$'             # ALL CAPS LINE
    r')',
    re.MULTILINE
)


def _count_tokens(text: str) -> int:
    return len(_ENC.encode(text))


def _split_into_sentences(text: str) -> List[str]:
    """Split text into sentences without breaking clinical abbreviations."""
    # Simple sentence split — respects Dr., e.g., i.e., etc.
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [p.strip() for p in parts if p.strip()]


def _split_into_sections(text: str) -> List[str]:
    """Split text at heading boundaries to get logical sections."""
    lines = text.splitlines()
    sections: List[str] = []
    current: List[str] = []

    for line in lines:
        if _HEADING_RE.match(line.strip()) and current:
            # Save current section, start a new one with this heading
            sections.append('\n'.join(current).strip())
            current = [line]
        else:
            current.append(line)

    if current:
        sections.append('\n'.join(current).strip())

    # Remove empty sections
    return [s for s in sections if s.strip()]


@dataclass
class ChunkData:
    """Raw chunk data before DB insertion."""
    chunk_type: str           # 'parent' or 'child'
    text: str
    token_count: int
    chunk_index: int
    parent_index: Optional[int] = None  # index of parent in parent list (for children)
    # Structure metadata (populated during ingestion from page data)
    chapter: Optional[str] = None
    section: Optional[str] = None
    page_number: Optional[int] = None
    page_range: Optional[str] = None


def build_chunks(full_text: str) -> List[ChunkData]:
    """
    Build parent and child chunks from full document text.

    Returns list of ChunkData — parents first, then children.
    Children have parent_index set to reference their parent's position.
    """
    # ── Step 1: Split into logical sections ─────────────────────────
    sections = _split_into_sections(full_text)
    if not sections:
        sections = [full_text]

    # ── Step 2: Build parent chunks ──────────────────────────────────
    parent_chunks: List[str] = []
    current_parent = ''

    for section in sections:
        candidate = (current_parent + '\n\n' + section).strip() if current_parent else section
        token_count = _count_tokens(candidate)

        if token_count < settings.PARENT_MIN_TOKENS:
            # Too small — keep accumulating
            current_parent = candidate

        elif token_count <= settings.PARENT_MAX_TOKENS:
            # Perfect size — save as one parent
            parent_chunks.append(candidate)
            current_parent = ''

        else:
            # This section alone is too large — save what we have, then split this
            if current_parent:
                parent_chunks.append(current_parent)
                current_parent = ''

            # Split oversized section into PARENT_MAX_TOKENS pieces with overlap
            parent_chunks.extend(_split_large_section(section))

    # Save any remaining accumulated text
    if current_parent.strip():
        parent_chunks.append(current_parent.strip())

    # ── Step 3: Build child chunks from each parent ──────────────────
    all_chunks: List[ChunkData] = []
    parent_index = 0

    for p_idx, parent_text in enumerate(parent_chunks):
        p_tokens = _count_tokens(parent_text)
        all_chunks.append(ChunkData(
            chunk_type='parent',
            text=parent_text,
            token_count=p_tokens,
            chunk_index=p_idx,
        ))

        children = _make_children(parent_text, p_idx)
        all_chunks.extend(children)

    logger.info(
        f"Chunking complete: {len(parent_chunks)} parents, "
        f"{len(all_chunks) - len(parent_chunks)} children, "
        f"total {len(all_chunks)} chunks"
    )
    return all_chunks


def _split_large_section(text: str) -> List[str]:
    """Split a section that exceeds PARENT_MAX_TOKENS into overlapping pieces."""
    sentences = _split_into_sentences(text)
    chunks: List[str] = []
    current_sentences: List[str] = []
    current_tokens = 0

    for sentence in sentences:
        s_tokens = _count_tokens(sentence)
        if current_tokens + s_tokens > settings.PARENT_MAX_TOKENS and current_sentences:
            chunks.append(' '.join(current_sentences))
            # Keep overlap sentences
            overlap_tokens = 0
            overlap_sents: List[str] = []
            for s in reversed(current_sentences):
                t = _count_tokens(s)
                if overlap_tokens + t <= settings.CHUNK_OVERLAP:
                    overlap_sents.insert(0, s)
                    overlap_tokens += t
                else:
                    break
            current_sentences = overlap_sents + [sentence]
            current_tokens = sum(_count_tokens(s) for s in current_sentences)
        else:
            current_sentences.append(sentence)
            current_tokens += s_tokens

    if current_sentences:
        chunks.append(' '.join(current_sentences))

    return chunks


def _make_children(parent_text: str, parent_index: int) -> List[ChunkData]:
    """Slide a window over parent text to produce child chunks."""
    sentences = _split_into_sentences(parent_text)
    if not sentences:
        return []

    children: List[ChunkData] = []
    current: List[str] = []
    current_tokens = 0
    child_idx = 0
    step = settings.CHILD_MAX_TOKENS - settings.CHUNK_OVERLAP

    for sentence in sentences:
        s_tokens = _count_tokens(sentence)

        if current_tokens + s_tokens > settings.CHILD_MAX_TOKENS and current:
            child_text = ' '.join(current)
            child_tokens = _count_tokens(child_text)

            if child_tokens >= settings.CHILD_MIN_TOKENS:
                children.append(ChunkData(
                    chunk_type='child',
                    text=child_text,
                    token_count=child_tokens,
                    chunk_index=child_idx,
                    parent_index=parent_index,
                ))
                child_idx += 1

            # Overlap: keep last CHUNK_OVERLAP tokens worth of sentences
            overlap: List[str] = []
            overlap_tokens = 0
            for s in reversed(current):
                t = _count_tokens(s)
                if overlap_tokens + t <= settings.CHUNK_OVERLAP:
                    overlap.insert(0, s)
                    overlap_tokens += t
                else:
                    break
            current = overlap + [sentence]
            current_tokens = sum(_count_tokens(s) for s in current)
        else:
            current.append(sentence)
            current_tokens += s_tokens

    # Last child
    if current:
        child_text = ' '.join(current)
        child_tokens = _count_tokens(child_text)
        # Merge tiny tail into previous child instead of creating micro-chunk
        if child_tokens >= settings.CHILD_MIN_TOKENS or not children:
            children.append(ChunkData(
                chunk_type='child',
                text=child_text,
                token_count=child_tokens,
                chunk_index=child_idx,
                parent_index=parent_index,
            ))
        elif children:
            # Append tail to last child
            last = children[-1]
            merged = last.text + ' ' + child_text
            children[-1] = ChunkData(
                chunk_type='child',
                text=merged,
                token_count=_count_tokens(merged),
                chunk_index=last.chunk_index,
                parent_index=parent_index,
            )

    return children
