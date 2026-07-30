"""
Ingestion pipeline coordinator — Progressive / Streaming Ingestion.

Flow:
  1. Upload → validate → parse → clean → chunk
  2. Save all chunks (parents + children with embedding=NULL) to DB immediately.
  3. Status → 'chat_ready' (User can start querying via FTS search instantly!)
  4. Background ThreadPool parallel embedding:
     - Worker threads process batches concurrently.
     - Each batch UPDATEs child chunk embeddings in DB and increments `embedded_chunk_count`.
     - Retrieval automatically uses vectors as they become available.
  5. All batches done → Status → 'ready'.
"""
import os
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import Document, DocumentChunk
from app.rag.parsers import parse_document, SUPPORTED_TYPES
from app.rag.chunker import build_chunks, ChunkData
from app.rag.embedder import get_embedder

logger = logging.getLogger(__name__)


def _set_status(db: Session, doc: Document, status: str, error: str = None):
    """Update document processing status and flush to DB."""
    doc.status = status
    if error:
        doc.error_message = error
    if status == 'ready':
        doc.ready_at = datetime.utcnow()
    db.add(doc)
    db.commit()
    logger.info(f"[{doc.id}] status -> {status}")
    print(f"[INGEST] [{doc.original_name}] status -> {status}" + (f" | ERROR: {error}" if error else ""))


def ingest_document(document_id: str):
    """
    Full progressive ingestion pipeline for a document.
    Called as a FastAPI BackgroundTask — runs after HTTP 202 response.
    """
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"Document {document_id} not found in DB")
            print(f"[INGEST] ERROR: Document {document_id} not found in DB")
            return

        print(f"\n{'='*60}")
        print(f"[INGEST] Starting ingestion for: {doc.original_name}")
        print(f"[INGEST] File type: {doc.file_type} | Size: {(doc.file_size_bytes or 0) / 1024 / 1024:.2f} MB")
        print(f"{'='*60}")

        # ── 1. VALIDATING ────────────────────────────────────────────
        _set_status(db, doc, 'validating')
        file_type = doc.file_type.lower()

        if file_type not in SUPPORTED_TYPES:
            _set_status(db, doc, 'failed', f"Unsupported file type: {file_type}")
            return

        file_path = os.path.join(settings.UPLOAD_DIR, doc.filename)
        if not os.path.exists(file_path):
            _set_status(db, doc, 'failed', f"File not found on disk: {file_path}")
            return

        # ── 2. EXTRACTING (+ OCR if needed) ─────────────────────────
        _set_status(db, doc, 'extracting')
        print(f"[INGEST] Parsing file: {file_path}")
        try:
            parsed = parse_document(file_path, file_type)
        except ValueError as e:
            _set_status(db, doc, 'failed', str(e))
            return

        print(f"[INGEST] Parsed: {len(parsed.pages)} pages | {len(parsed.full_text):,} chars | OCR pages: {parsed.ocr_page_count}")

        if parsed.ocr_page_count > 0:
            _set_status(db, doc, 'ocr')

        if not doc.author and parsed.author:
            doc.author = parsed.author

        # ── 3. CLEANING ──────────────────────────────────────────────
        _set_status(db, doc, 'cleaning')
        full_text = _clean_text(parsed.full_text)
        print(f"[INGEST] Cleaned text: {len(full_text):,} chars")

        if not full_text.strip():
            _set_status(db, doc, 'failed', 'No text could be extracted from document')
            return

        # ── 4. CHUNKING ──────────────────────────────────────────────
        _set_status(db, doc, 'chunking')
        chunks = build_chunks(full_text)
        chunks = _attach_page_metadata(chunks, parsed)

        parent_chunks = [c for c in chunks if c.chunk_type == 'parent']
        child_chunks  = [c for c in chunks if c.chunk_type == 'child']
        total_tokens  = sum(c.token_count for c in parent_chunks)
        print(f"[INGEST] Chunking complete: {len(parent_chunks)} parents | {len(child_chunks)} children | {total_tokens:,} tokens")

        # ── 5. STORE ALL CHUNKS IMMEDIATELY (FTS UNLOCKED) ──────────
        parent_id_map: dict[int, uuid.UUID] = {}

        # Insert parent chunks
        for chunk_data in parent_chunks:
            db_chunk = DocumentChunk(
                document_id=doc.id,
                user_id=doc.user_id,
                is_global=doc.is_global,
                chunk_type='parent',
                parent_chunk_id=None,
                chunk_text=chunk_data.text,
                embedding=None,
                chapter=chunk_data.chapter,
                section=chunk_data.section,
                page_number=chunk_data.page_number,
                page_range=chunk_data.page_range,
                chunk_index=chunk_data.chunk_index,
                token_count=chunk_data.token_count,
            )
            db.add(db_chunk)
            db.flush()
            parent_id_map[chunk_data.chunk_index] = db_chunk.id

        # Insert child chunks (embedding=None)
        child_db_records: List[Tuple[uuid.UUID, str]] = []  # (db_chunk_id, text)
        for chunk_data in child_chunks:
            parent_uuid = parent_id_map.get(chunk_data.parent_index)
            db_chunk = DocumentChunk(
                document_id=doc.id,
                user_id=doc.user_id,
                is_global=doc.is_global,
                chunk_type='child',
                parent_chunk_id=parent_uuid,
                chunk_text=chunk_data.text,
                embedding=None,
                chapter=chunk_data.chapter,
                section=chunk_data.section,
                page_number=chunk_data.page_number,
                page_range=chunk_data.page_range,
                chunk_index=chunk_data.chunk_index,
                token_count=chunk_data.token_count,
            )
            db.add(db_chunk)
            db.flush()
            child_db_records.append((db_chunk.id, chunk_data.text))

        doc.chunk_count = len(chunks)
        doc.child_chunk_count = len(child_chunks)
        doc.embedded_chunk_count = 0
        doc.total_tokens = total_tokens

        # Mark document as CHAT_READY so user can ask questions immediately using FTS!
        _set_status(db, doc, 'chat_ready')
        print(f"[INGEST] *** CHAT_READY! *** User can ask questions NOW via FTS!")
        print(f"[INGEST] Starting parallel embedding: {len(child_db_records)} child chunks | batch={settings.EMBEDDING_BATCH_SIZE} | workers={settings.EMBEDDING_WORKERS}")
        db.close()  # close main session for background thread work

        # ── 6. PARALLEL EMBEDDING IN BACKGROUND ─────────────────
        if child_db_records:
            _embed_and_update_parallel(doc.id, child_db_records)

        # ── 7. READY ──────────────────────────────────────────────
        db = SessionLocal()
        doc = db.query(Document).filter(Document.id == doc.id).first()
        if doc:
            _set_status(db, doc, 'ready')
            print(f"[INGEST] *** FULLY OPTIMIZED! *** {len(child_chunks)} vectors embedded. Document ready.")
            print(f"{'='*60}\n")

    except Exception as e:
        logger.exception(f"Ingestion failed for document {document_id}: {e}")
        try:
            db_err = SessionLocal()
            doc_err = db_err.query(Document).filter(Document.id == document_id).first()
            if doc_err:
                _set_status(db_err, doc_err, 'failed', str(e))
            db_err.close()
        except Exception:
            pass
    finally:
        try:
            db.close()
        except Exception:
            pass


def _embed_single_batch(batch: List[Tuple[uuid.UUID, str]]) -> List[Tuple[uuid.UUID, Optional[List[float]]]]:
    """Worker function to embed a single batch of (chunk_id, text)."""
    embedder = get_embedder()
    texts = [t[1] for t in batch]
    try:
        embeddings = embedder.embed_batch(texts)
        return [(batch[i][0], embeddings[i]) for i in range(len(batch))]
    except Exception as e:
        logger.error(f"Batch embedding failed: {e}")
        return [(batch[i][0], None) for i in range(len(batch))]


def _embed_and_update_parallel(doc_id: uuid.UUID, child_records: List[Tuple[uuid.UUID, str]]):
    """
    Splits child chunks into batches and runs them in parallel using ThreadPoolExecutor.
    As each batch finishes, updates database embeddings and increments embedded_chunk_count.
    """
    batch_size = getattr(settings, 'EMBEDDING_BATCH_SIZE', 48)
    max_workers = getattr(settings, 'EMBEDDING_WORKERS', 6)

    batches = [child_records[i:i + batch_size] for i in range(0, len(child_records), batch_size)]
    print(f"[EMBED] {len(child_records)} chunks -> {len(batches)} batches x {batch_size} | {max_workers} parallel workers")
    logger.info(f"[{doc_id}] Embedding {len(child_records)} chunks in {len(batches)} batches across {max_workers} workers.")

    completed_batches = 0
    total_embedded   = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_batch = {executor.submit(_embed_single_batch, b): b for b in batches}

        for future in as_completed(future_to_batch):
            batch_result = future.result()
            valid_results = [(cid, emb) for cid, emb in batch_result if emb is not None]

            if valid_results:
                db = SessionLocal()
                try:
                    # Update each chunk's embedding
                    for chunk_id, emb in valid_results:
                        emb_str = f"[{','.join(str(x) for x in emb)}]"
                        db.execute(
                            text("UPDATE document_chunks SET embedding = :emb WHERE id = :id"),
                            {'emb': emb_str, 'id': str(chunk_id)}
                        )

                    # Update document embedded_chunk_count
                    db.execute(
                        text("UPDATE documents SET embedded_chunk_count = embedded_chunk_count + :cnt WHERE id = :doc_id"),
                        {'cnt': len(valid_results), 'doc_id': str(doc_id)}
                    )
                    db.commit()

                    # Progress print
                    completed_batches += 1
                    total_embedded   += len(valid_results)
                    pct = round(total_embedded / len(child_records) * 100)
                    print(f"[EMBED] Batch {completed_batches}/{len(batches)} done | "
                          f"{len(valid_results)} embedded | "
                          f"{total_embedded}/{len(child_records)} total ({pct}%)")

                except Exception as e:
                    logger.error(f"Failed to save batch embeddings to DB: {e}")
                    print(f"[EMBED] ERROR saving batch: {e}")
                    db.rollback()
                finally:
                    db.close()


def _clean_text(text_content: str) -> str:
    """Remove noise from extracted text."""
    import re
    text_content = re.sub(r'[ \t]+', ' ', text_content)
    text_content = re.sub(r'\n{3,}', '\n\n', text_content)
    text_content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text_content)
    return text_content.strip()


def _attach_page_metadata(chunks, parsed) -> list:
    """Attach chapter/section/page info to chunks based on text position."""
    import re
    pages_text = [(p.page_number, p.text) for p in parsed.pages]

    for chunk in chunks:
        best_page = None
        best_overlap = 0
        chunk_words = set(chunk.text.lower().split()[:20])

        for page_num, page_text in pages_text:
            page_words = set(page_text.lower().split()[:50])
            overlap = len(chunk_words & page_words)
            if overlap > best_overlap:
                best_overlap = overlap
                best_page = page_num

        chunk.page_number = best_page

        heading_match = re.search(
            r'^(?:#{1,3}\s+|Chapter\s+\d+[:\s]|Section\s+\d+[:\s])(.+)',
            chunk.text,
            re.MULTILINE | re.IGNORECASE
        )
        if heading_match:
            heading = heading_match.group(1).strip()
            if 'chapter' in chunk.text[:100].lower():
                chunk.chapter = heading[:200]
            else:
                chunk.section = heading[:200]

    return chunks
