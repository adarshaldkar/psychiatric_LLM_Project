import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ── Core ────────────────────────────────────────────────
    PROJECT_NAME: str = 'MindCare AI'
    VERSION: str = '1.0.0'

    # ── Auth ────────────────────────────────────────────────
    OPENROUTER_API_KEY: str
    DATABASE_URL: str
    JWT_SECRET: str = 'default_secret'
    JWT_ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ── LLM ─────────────────────────────────────────────────
    DEFAULT_MODEL: str = 'google/gemini-2.5-flash'

    # ── Multi-Provider LLM Router ────────────────────────────
    GROQ_API_KEY: str = ''
    SAMBANOVA_API_KEY: str = ''
    OPENAI_API_KEY: str = ''
    ANTHROPIC_API_KEY: str = ''
    GOOGLE_API_KEY: str = ''
    OLLAMA_BASE_URL: str = 'http://localhost:11434'
    OLLAMA_MODEL: str = 'llama3.2'

    # ── Embedding ───────────────────────────────────────────
    EMBEDDING_MODEL: str = 'text-embedding-3-small'
    EMBEDDING_DIMENSION: int = 1536
    EMBEDDING_WORKERS: int = 6         # parallel batch workers for fast embedding
    EMBEDDING_BATCH_SIZE: int = 48     # chunks per batch call

    # ── Chunking — Parent level (for LLM context) ───────────
    PARENT_MIN_TOKENS: int = 400
    PARENT_MAX_TOKENS: int = 1200

    # ── Chunking — Child level (for retrieval) ──────────────
    CHILD_MIN_TOKENS: int = 150
    CHILD_MAX_TOKENS: int = 300

    # ── Overlap between splits ───────────────────────────────
    CHUNK_OVERLAP: int = 40

    # ── Retrieval & Adaptive AI Runtime (Phase 3) ────────────
    RETRIEVAL_TOP_K: int = 35                  # candidate pool size
    RERANK_TOP_K: int = 5                      # default final chunks sent to LLM
    CONFIDENCE_THRESHOLD: float = 0.65         # RAG confidence gate cutoff
    RERANK_BYPASS_COSINE_THRESHOLD: float = 0.88  # top cosine score threshold to bypass Cross-Encoder
    RERANK_BYPASS_MARGIN_THRESHOLD: float = 0.15  # score margin threshold (top - 2nd) to bypass Cross-Encoder
    MAX_RAG_CONTEXT_TOKENS: int = 2500         # token budget cap for retrieved context

    # ── Ingestion ────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 100
    UPLOAD_DIR: str = 'uploads'

    # ── Retry ────────────────────────────────────────────────
    RETRY_ATTEMPTS: int = 3
    RETRY_WAIT_MIN: int = 1
    RETRY_WAIT_MAX: int = 10

    # ── Security — CORS ─────────────────────────────────────
    # Comma-separated allowed origins. Override in .env for production.
    ALLOWED_ORIGINS: str = 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173'

    # ── Voice STT ────────────────────────────────────────────
    WHISPER_MODEL: str = 'base'  # Options: tiny, base, small, medium, large
    WHISPER_LANGUAGE: str = 'en'

    # ── Rate Limiting ────────────────────────────────────────
    RATE_LIMIT_AUTH: str = '5/minute'    # login / register
    RATE_LIMIT_CHAT: str = '30/minute'   # chat messages
    RATE_LIMIT_UPLOAD: str = '10/minute' # document uploads

    def get_allowed_origins(self) -> list[str]:
        """Returns parsed list of CORS allowed origins."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(',') if o.strip()]

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore'

settings = Settings()

# ── Startup security validation ───────────────────────────────────────────────
import logging as _logging
_log = _logging.getLogger(__name__)

if settings.JWT_SECRET in ('default_secret', 'secret', 'changeme', ''):
    _log.critical(
        "SECURITY WARNING: JWT_SECRET is set to an insecure default value '%s'. "
        "Set a strong random secret in .env: "
        "JWT_SECRET=$(python -c \"import secrets; print(secrets.token_hex(32))\")",
        settings.JWT_SECRET
    )
