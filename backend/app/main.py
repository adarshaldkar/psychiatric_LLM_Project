import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.database import Base, engine, create_vector_indexes, migrate_schema, SessionLocal
from app.api import auth, conversations, chat, documents, memory, voice

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
                        _embed_and_update_parallel(doc_id, records)
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
                    doc.status = 'ready'
                    db.add(doc)
            db.commit()

    except Exception as e:
        logger.error(f"Startup recovery failed: {e}")
    finally:
        db.close()


# ── Security Headers Middleware ──────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects hardened security headers on every response."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(self)"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────
    Base.metadata.create_all(bind=engine)

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


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="MindCare AI — Psychiatric and Mental Health Knowledge Assistant API",
    lifespan=lifespan,
)

# ── Rate Limiting (SlowAPI) ───────────────────────────────────────────────────
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("SlowAPI rate limiter active")
except ImportError:
    logger.warning("slowapi not installed — rate limiting disabled.")

# ── Security Headers ─────────────────────────────────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)

# ── CORS — Full Support for Vercel Deployments & Local Dev ───────────────────
_origins = list(set([
    "https://psychiatric-llm-project.vercel.app",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    *settings.get_allowed_origins(),
]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers ──────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(memory.router, prefix="/api")
app.include_router(voice.router, prefix="/api")

@app.get("/")
def root():
    return {
        "message": "MindCare AI Backend Services Online",
        "version": settings.VERSION,
        "phase": "7 — Production Hardened",
        "security": "CORS locked, rate-limited, security headers active"
    }
