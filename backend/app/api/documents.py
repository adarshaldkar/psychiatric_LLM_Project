"""
Documents API — upload, list, delete, status endpoints.

POST /documents/upload  → HTTP 202, starts background ingestion
GET  /documents         → list user's documents + global documents
GET  /documents/{id}    → single document details + status
DELETE /documents/{id}  → delete document and all its chunks
"""
import os
import uuid
import logging
import mimetypes
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

import aiofiles

from app.core.database import get_db
from app.core.config import settings
from app.api.auth import get_current_user
from app.models.models import Document, DocumentChunk, User
from app.rag.parsers import SUPPORTED_TYPES
from app.rag.ingestion import ingest_document

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/documents', tags=['Documents'])

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

ALLOWED_MIME_TYPES = {
    'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'image/png', 'image/jpeg',
}


def _ext_from_filename(filename: str) -> str:
    """Extract lowercase extension without dot."""
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''


_STATUS_LABELS = {
    'uploaded':   '📄 Uploading...',
    'validating': '📄 Uploading...',
    'extracting': '📖 Reading document...',
    'ocr':        '🔍 OCR scanning...',
    'cleaning':   '📖 Reading document...',
    'chunking':   '✂️ Preparing document...',
    'chat_ready': '💬 Chat ready',
    'ready':      '✅ Fully optimized',
    'failed':     '❌ Failed',
}


def _doc_to_dict(doc: Document) -> dict:
    total_child = doc.child_chunk_count or 0
    embedded    = doc.embedded_chunk_count or 0
    # Progress: 0–100 (child chunks only — parents never get embeddings)
    progress = round((embedded / total_child * 100) if total_child > 0 else 0)

    return {
        'id': str(doc.id),
        'original_name': doc.original_name,
        'file_type': doc.file_type,
        'file_size_bytes': doc.file_size_bytes,
        'is_global': doc.is_global,
        'status': doc.status,
        'status_label': _STATUS_LABELS.get(doc.status, doc.status),
        'error_message': doc.error_message,
        'chunk_count': doc.chunk_count,
        'child_chunk_count': total_child,
        'embedded_chunk_count': embedded,
        'embedding_progress': progress,   # 0–100 %
        'total_tokens': doc.total_tokens,
        'author': doc.author,
        'tags': doc.tags or [],
        'version_number': doc.version_number,
        'is_latest': doc.is_latest,
        'uploaded_at': doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        'ready_at': doc.ready_at.isoformat() if doc.ready_at else None,
    }



@router.post('/upload', status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    is_global: bool = Form(False),
    author: str = Form(None),
    tags: str = Form(''),         # comma-separated
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document for ingestion.
    Returns HTTP 202 immediately — processing runs in background.
    """
    # ── Validate file type ──────────────────────────────────────────
    file_ext = _ext_from_filename(file.filename or '')
    if file_ext not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file_ext}'. Supported: {', '.join(sorted(SUPPORTED_TYPES))}"
        )

    # ── Check file size ─────────────────────────────────────────────
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f}MB). Max allowed: {settings.MAX_FILE_SIZE_MB}MB"
        )

    # ── Handle versioning if same filename already uploaded ─────────
    existing = db.query(Document).filter(
        Document.user_id == current_user.id,
        Document.original_name == file.filename,
        Document.is_latest == True
    ).first()

    old_version = None
    new_version = 1
    if existing:
        old_version = existing
        new_version = (existing.version_number or 1) + 1
        # Mark old version as not latest
        existing.is_latest = False
        db.add(existing)

    # ── Save file to disk ───────────────────────────────────────────
    safe_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)

    # ── Create Document record ──────────────────────────────────────
    tag_list = [t.strip() for t in tags.split(',') if t.strip()] if tags else []

    doc = Document(
        user_id=current_user.id,
        filename=safe_filename,
        original_name=file.filename,
        file_type=file_ext,
        file_size_bytes=len(content),
        is_global=is_global,
        status='uploaded',
        author=author,
        tags=tag_list,
        version_number=new_version,
        is_latest=True,
        previous_doc_id=old_version.id if old_version else None,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # ── Queue background ingestion ──────────────────────────────────
    doc_id = str(doc.id)
    background_tasks.add_task(ingest_document, doc_id)

    logger.info(f"Document uploaded: {file.filename} (v{new_version}) by user {current_user.id}")

    return JSONResponse(
        status_code=202,
        content={
            'message': 'Document uploaded successfully. Processing in background.',
            'document': _doc_to_dict(doc),
        }
    )


@router.get('')
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all documents accessible to the current user (own + global)."""
    docs = db.query(Document).filter(
        Document.is_latest == True,
        (Document.user_id == current_user.id) | (Document.is_global == True)
    ).order_by(Document.uploaded_at.desc()).all()

    return [_doc_to_dict(d) for d in docs]


@router.get('/{document_id}')
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single document status and details."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    doc = db.query(Document).filter(Document.id == doc_uuid).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Access control: must be owner or global
    if doc.user_id != current_user.id and not doc.is_global:
        raise HTTPException(status_code=403, detail="Access denied")

    return _doc_to_dict(doc)


@router.delete('/{document_id}', status_code=204)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a document and all its chunks. Only owner can delete."""
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    doc = db.query(Document).filter(Document.id == doc_uuid).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can delete this document")

    # Delete file from disk
    file_path = os.path.join(settings.UPLOAD_DIR, doc.filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            logger.warning(f"Could not delete file {file_path}: {e}")

    # Delete chunks in FK-safe order: children first, then parents
    # (parent_chunk_id FK prevents deleting a parent before its children)
    db.query(DocumentChunk).filter(
        DocumentChunk.document_id == doc_uuid,
        DocumentChunk.chunk_type == 'child'
    ).delete(synchronize_session=False)
    db.query(DocumentChunk).filter(
        DocumentChunk.document_id == doc_uuid,
        DocumentChunk.chunk_type == 'parent'
    ).delete(synchronize_session=False)

    db.delete(doc)
    db.commit()
    logger.info(f"Document deleted: {document_id} by user {current_user.id}")


@router.get('/{document_id}/page/{page_number}')
def get_document_page(
    document_id: str,
    page_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    MCP Tool: get_document_page
    Retrieve the full aggregated text of a specific page from an uploaded document.
    Used by the MCP layer when the AI needs to read a complete page in context.
    """
    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    doc = db.query(Document).filter(Document.id == doc_uuid).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Access control: must be owner or global document
    if doc.user_id != current_user.id and not doc.is_global:
        raise HTTPException(status_code=403, detail="Access denied")

    if page_number < 1:
        raise HTTPException(status_code=400, detail="Page number must be >= 1")

    # Fetch all parent chunks on this page (parents contain the richer context)
    chunks = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id == doc_uuid,
            DocumentChunk.page_number == page_number,
            DocumentChunk.chunk_type == 'parent'
        )
        .order_by(DocumentChunk.chunk_index)
        .all()
    )

    # Fallback: if no parent chunks, try child chunks
    if not chunks:
        chunks = (
            db.query(DocumentChunk)
            .filter(
                DocumentChunk.document_id == doc_uuid,
                DocumentChunk.page_number == page_number,
            )
            .order_by(DocumentChunk.chunk_index)
            .all()
        )

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail=f"Page {page_number} not found in document '{doc.original_name}'"
        )

    # Aggregate page text from all chunks on that page
    page_text = "\n\n".join(c.chunk_text for c in chunks if c.chunk_text)
    section = chunks[0].section if chunks else None

    return {
        "document_id": str(doc.id),
        "document_name": doc.original_name,
        "page_number": page_number,
        "section": section,
        "page_text": page_text,
        "chunk_count": len(chunks),
        "token_estimate": sum(c.token_count or 0 for c in chunks),
    }
