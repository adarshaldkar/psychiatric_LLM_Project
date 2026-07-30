import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, Integer,
    ForeignKey, JSON, Float, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base
from app.core.config import settings

# ────────────────────────────────────────────────
# Phase 1 Models (unchanged)
# ────────────────────────────────────────────────

class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    preferences = Column(JSON, default=dict)

    conversations = relationship('Conversation', back_populates='user', cascade='all, delete-orphan')
    documents = relationship('Document', back_populates='user', cascade='all, delete-orphan')
    memories = relationship('LongTermMemory', back_populates='user', cascade='all, delete-orphan')

class Conversation(Base):
    __tablename__ = 'conversations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(String, default='New Conversation')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    summary = Column(Text, nullable=True)
    is_archived = Column(Boolean, default=False)

    user = relationship('User', back_populates='conversations')
    messages = relationship('Message', back_populates='conversation', cascade='all, delete-orphan', order_by='Message.created_at')

class Message(Base):
    __tablename__ = 'messages'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False)
    role = Column(String, nullable=False)  # user | assistant | system | tool
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_info = Column('metadata', JSON, default=dict)
    token_count = Column(Integer, nullable=True)

    conversation = relationship('Conversation', back_populates='messages')

# ────────────────────────────────────────────────
# Phase 2 Models — RAG
# ────────────────────────────────────────────────

class Document(Base):
    """Represents an uploaded document in the knowledge base."""
    __tablename__ = 'documents'

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    filename        = Column(String, nullable=False)          # stored filename on disk
    original_name   = Column(String, nullable=False)          # original upload filename
    file_type       = Column(String, nullable=False)          # pdf, docx, txt, pptx, jpg, png, jpeg
    file_size_bytes = Column(Integer, nullable=True)
    is_global       = Column(Boolean, default=False, nullable=False)  # visible to all users?

    # Processing state
    # uploaded | validating | extracting | ocr | cleaning | chunking
    # | chat_ready | ready | failed
    status                = Column(String, default='uploaded', nullable=False)
    error_message         = Column(Text, nullable=True)
    chunk_count           = Column(Integer, nullable=True)   # total chunks (parent + child)
    child_chunk_count     = Column(Integer, nullable=True)   # child chunks only (get embeddings)
    embedded_chunk_count  = Column(Integer, default=0, nullable=False)  # children with embeddings
    total_tokens          = Column(Integer, nullable=True)

    # Document metadata
    author          = Column(String, nullable=True)
    tags            = Column(JSON, default=list)              # ["psychiatry", "DSM-5"]

    # Versioning
    version_number  = Column(Integer, default=1, nullable=False)
    is_latest       = Column(Boolean, default=True, nullable=False)
    previous_doc_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=True)

    # Timestamps
    uploaded_at         = Column(DateTime, default=datetime.utcnow)
    ready_at            = Column(DateTime, nullable=True)
    processing_version  = Column(String, default='2.0')

    # Relationships
    user    = relationship('User', back_populates='documents')
    chunks  = relationship('DocumentChunk', back_populates='document', cascade='all, delete-orphan')
    previous_version = relationship('Document', remote_side='Document.id', foreign_keys='Document.previous_doc_id')


class DocumentChunk(Base):
    """A single chunk of text from a document, with embedding for vector search."""
    __tablename__ = 'document_chunks'

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id     = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    user_id         = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    is_global       = Column(Boolean, default=False, nullable=False)

    # Parent-Child relationship
    chunk_type      = Column(String, nullable=False)          # 'parent' or 'child'
    parent_chunk_id = Column(UUID(as_uuid=True), ForeignKey('document_chunks.id'), nullable=True)

    # Content
    chunk_text      = Column(Text, nullable=False)
    embedding       = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)  # child only

    # Structure metadata
    chapter         = Column(String, nullable=True)
    section         = Column(String, nullable=True)
    subsection      = Column(String, nullable=True)
    page_number     = Column(Integer, nullable=True)
    page_range      = Column(String, nullable=True)           # "217-219"
    chunk_index     = Column(Integer, nullable=False)
    token_count     = Column(Integer, nullable=False)

    # Extra metadata (flexible)
    metadata_info   = Column('metadata', JSON, default=dict)
    created_at      = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship('Document', back_populates='chunks')
    # Note: parent-child navigation is done via raw SQL in retriever.py and ingestion.py
    # (WHERE parent_chunk_id = :id) — no ORM relationship needed here.


    # ── Indexes (created via DDL after table creation) ──────
    # HNSW index for vector similarity (created in init_db)
    # GIN index for full-text search (created in init_db)
    # Index on (is_global, user_id) for access filtering
    __table_args__ = (
        Index('ix_chunks_global_user', 'is_global', 'user_id'),
        Index('ix_chunks_doc_type', 'document_id', 'chunk_type'),
    )


# ────────────────────────────────────────────────
# Phase 4 Models — Continuity Engine
# ────────────────────────────────────────────────

class LongTermMemory(Base):
    """
    Phase 4: Continuity Engine — Multi-dimensional Long-Term Memory.
    Stores episodic (interaction events) and semantic (persistent facts/preferences) memories.
    """
    __tablename__ = 'long_term_memories'

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id                 = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    memory_type             = Column(String, default='semantic', nullable=False)  # 'episodic' | 'semantic'
    content                 = Column(Text, nullable=False)
    embedding               = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)
    importance_score        = Column(Float, default=0.5, nullable=False)
    confidence_score        = Column(Float, default=0.8, nullable=False)
    retrieval_count         = Column(Integer, default=0, nullable=False)
    source_type             = Column(String, default='explicit_statement')  # explicit_statement | inferred_preference | event
    source_conversation_id  = Column(UUID(as_uuid=True), ForeignKey('conversations.id', ondelete='SET NULL'), nullable=True)
    created_at              = Column(DateTime, default=datetime.utcnow)
    last_accessed_at        = Column(DateTime, default=datetime.utcnow)
    expires_at              = Column(DateTime, nullable=True)

    user = relationship('User', back_populates='memories')

