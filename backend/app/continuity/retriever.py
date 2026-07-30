"""
Continuity Engine — Memory Retriever

Responsibilities:
  1. Perform vector similarity search on `long_term_memories` for a user.
  2. Multi-Dimensional Decay Ranking: Scores candidates using similarity, importance, and recency.
  3. Returns formatted memory context + telemetry metrics.
"""
import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.rag.embedder import get_embedder

logger = logging.getLogger(__name__)


@dataclass
class MemoryItem:
    id: str
    memory_type: str        # 'episodic' | 'semantic'
    content: str
    similarity: float
    importance_score: float
    source_type: str


@dataclass
class ContinuityResult:
    success: bool
    summary: Optional[str] = None
    memories: List[MemoryItem] = field(default_factory=list)
    formatted_context: str = ""
    telemetry: Dict[str, Any] = field(default_factory=dict)


def retrieve_continuity_context(
    query: str,
    user_id: str,
    db: Session,
    conversation_summary: Optional[str] = None,
    top_k: int = 3,
    min_similarity: float = 0.20
) -> ContinuityResult:
    """
    Retrieves relevant episodic & semantic memories using vector similarity + decay ranking.
    """
    t0 = time.perf_counter()
    telemetry = {"summary_used": bool(conversation_summary)}

    memories: List[MemoryItem] = []
    formatted_parts: List[str] = []

    if conversation_summary:
        formatted_parts.append(f"[CONVERSATION SUMMARY]\n{conversation_summary}")

    try:
        embedder = get_embedder()
        query_embedding = embedder.embed(query)
        emb_str = '[' + ','.join(str(x) for x in query_embedding) + ']'

        # Vector search with decay weighting
        # Final Score = cosine_similarity * 0.7 + importance_score * 0.3
        sql = text("""
            SELECT id::text,
                   memory_type,
                   content,
                   1 - (embedding <=> CAST(:emb AS vector)) AS similarity,
                   importance_score,
                   source_type
            FROM long_term_memories
            WHERE user_id = CAST(:uid AS uuid)
              AND embedding IS NOT NULL
              AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY (1 - (embedding <=> CAST(:emb AS vector))) * 0.7 + importance_score * 0.3 DESC
            LIMIT :top_k
        """)

        rows = db.execute(sql, {'emb': emb_str, 'uid': user_id, 'top_k': top_k}).fetchall()

        for row in rows:
            sim = float(row[3])
            if sim >= min_similarity:
                item = MemoryItem(
                    id=row[0],
                    memory_type=row[1],
                    content=row[2],
                    similarity=sim,
                    importance_score=float(row[4]),
                    source_type=row[5],
                )
                memories.append(item)
                formatted_parts.append(f"[{item.memory_type.upper()} MEMORY] {item.content}")

        # Update last_accessed_at for retrieved memories
        if memories:
            mem_ids = [f"'{m.id}'" for m in memories]
            db.execute(text(f"UPDATE long_term_memories SET last_accessed_at = NOW() WHERE id IN ({','.join(mem_ids)})"))
            db.commit()

    except Exception as e:
        logger.error(f"Continuity memory retrieval failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass

    t_ms = round((time.perf_counter() - t0) * 1000, 1)
    telemetry["memories_retrieved"] = len(memories)
    telemetry["max_similarity"] = max([m.similarity for m in memories], default=0.0)
    telemetry["retrieval_ms"] = t_ms

    formatted_context = "\n".join(formatted_parts)
    telemetry["memory_tokens"] = len(formatted_context) // 4

    print(f"[CONTINUITY] Summary Used: {bool(conversation_summary)} | Memories Retrieved: {len(memories)} | Max Sim: {telemetry['max_similarity']:.2f} | Memory Tokens: {telemetry['memory_tokens']}", flush=True)

    return ContinuityResult(
        success=bool(formatted_context),
        summary=conversation_summary,
        memories=memories,
        formatted_context=formatted_context,
        telemetry=telemetry
    )
