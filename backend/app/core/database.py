import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_vector_indexes():
    """
    Create pgvector extension, HNSW vector index, and GIN full-text index.

    Each statement runs with AUTOCOMMIT so a single failure cannot abort
    the entire session or poison the connection pool.
    """
    # Use AUTOCOMMIT isolation — DDL must not run inside a transaction block
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:

        # 1. Enable pgvector extension (safe to call repeatedly)
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            logger.info("pgvector extension: OK")
        except Exception as e:
            logger.warning(f"pgvector extension skipped: {e}")

        # 2. HNSW index for fast approximate nearest-neighbour vector search
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw
                ON document_chunks
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """))
            logger.info("HNSW index: OK")
        except Exception as e:
            logger.warning(f"HNSW index skipped (will retry on next start): {e}")

        # 3. GIN index for PostgreSQL full-text search
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_chunks_fts
                ON document_chunks
                USING gin(to_tsvector('english', chunk_text))
            """))
            logger.info("GIN FTS index: OK")
        except Exception as e:
            logger.warning(f"GIN index skipped: {e}")

        # 4. HNSW index for long-term memory vector search
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_memories_embedding_hnsw
                ON long_term_memories
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """))
            logger.info("Memory HNSW index: OK")
        except Exception as e:
            logger.warning(f"Memory HNSW index skipped: {e}")


def migrate_schema():
    """
    Safe schema migrations — adds new columns without dropping existing data.
    Uses ALTER TABLE ... ADD COLUMN IF NOT EXISTS so it is always safe to
    re-run on every startup (idempotent).
    """
    migrations = [
        # Progressive ingestion: track per-document embedding progress
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS embedded_chunk_count INTEGER DEFAULT 0 NOT NULL",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS child_chunk_count INTEGER",
    ]
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
            except Exception as e:
                logger.warning(f"Migration skipped: {e}")
    logger.info("Schema migrations: OK")
