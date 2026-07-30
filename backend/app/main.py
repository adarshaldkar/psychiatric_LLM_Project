from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine, create_vector_indexes, migrate_schema, SessionLocal
from app.api import auth, conversations, chat
from app.api import documents
import os
import logging

logger = logging.getLogger(__name__)

# States that mean a background job was killed by a server restart
_HARD_STUCK_STATES  = {'uploading', 'validating', 'extracting', 'ocr', 'cleaning', 'chunking'}
_EMBED_STUCK_STATES = {'chat_ready'}   # chunks exist but embedding was interrupted


def _recover_stuck_documents():
    """
    On startup, handle documents that were interrupted by a server restart:

    • Hard-stuck (uploading/extracting/chunking):
      Chunks may not exist yet → mark as 'failed' so user can delete & re-upload.

    • Embed-stuck (chat_ready):
      All chunks are already in DB. Only embedding was interrupted.
      Re-queue embedding in background so the doc finishes becoming 'ready'
      without the user needing to re-upload.
    """
    from app.models.models import Document, DocumentChunk
    from app.rag.ingestion import _embed_and_update_parallel
    import threading

    db = SessionLocal()
    try:
        # ── Hard-stuck → failed ───────────────────────────────────────────────
        hard_stuck = db.query(Document).filter(Document.status.in_(_HARD_STUCK_STATES)).all()
        if hard_stuck:
            logger.warning(f"Found {len(hard_stuck)} hard-stuck document(s) — marking as failed")
            for doc in hard_stuck:
                doc.status = 'failed'
                doc.error_message = (
                    f"Processing interrupted (server restarted during '{doc.status}'). "
                    "Please delete and re-upload."
                )
                db.add(doc)
            db.commit()

        # ── Embed-stuck → re-queue embedding in background ───────────────────
        embed_stuck = db.query(Document).filter(Document.status.in_(_EMBED_STUCK_STATES)).all()
        if embed_stuck:
            logger.info(f"Found {len(embed_stuck)} embed-stuck document(s) — re-queuing embedding")
            for doc in embed_stuck:
                # Fetch child chunks that still lack embeddings
                unembedded = db.query(DocumentChunk).filter(
                    DocumentChunk.document_id == doc.id,
                    DocumentChunk.chunk_type == 'child',
                    DocumentChunk.embedding == None,   # noqa: E711
                ).all()

                if unembedded:
                    child_records = [(c.id, c.chunk_text) for c in unembedded]
                    doc_id = doc.id
                    logger.info(f"[{doc_id}] Re-embedding {len(unembedded)} unembedded child chunks")

                    def _resume(doc_id=doc_id, records=child_records):
                        from app.rag.ingestion import _embed_and_update_parallel
                        from app.core.database import SessionLocal
                        _embed_and_update_parallel(doc_id, records)
                        # Mark ready when done
                        _db = SessionLocal()
                        try:
                            from app.models.models import Document as Doc
                            d = _db.query(Doc).filter(Doc.id == doc_id).first()
                            if d:
                                d.status = 'ready'
                                _db.commit()
                        finally:
                            _db.close()

                    threading.Thread(target=_resume, daemon=True).start()
                else:
                    # All chunks embedded — just mark ready
                    doc.status = 'ready'
                    db.add(doc)
            db.commit()

    except Exception as e:
        logger.error(f"Startup recovery failed: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────
    Base.metadata.create_all(bind=engine)

    # Run schema migrations FIRST (adds new columns before anything queries them)
    try:
        migrate_schema()
    except Exception as e:
        logger.warning(f"Schema migration failed: {e}")

    try:
        create_vector_indexes()
    except Exception as e:
        logger.warning(f"Vector index creation skipped: {e}")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    _recover_stuck_documents()

    yield  # ← app runs here

    # ── Shutdown ─────────────────────────────────────────────────────


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="MindCare AI — Psychiatric and Mental Health Knowledge Assistant API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import auth, conversations, chat, documents, memory

app.include_router(auth.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(memory.router)

@app.get("/")
def root():
    return {"message": "MindCare AI Backend Services Online", "version": settings.VERSION, "phase": "4 — Continuity Engine Active"}

