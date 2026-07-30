"""
Continuity Engine — Two-Stage Memory Consolidation Pipeline

Flow:
  Stage 1 (Extraction): LLM identifies high-value user facts (Semantic) and interaction events (Episodic).
  Stage 2 (Consolidation & Deduplication): Check vector similarity against existing user memories.
           If similar memory exists (> 0.82 cosine similarity), update recency/retrieval_count.
           If new fact, generate embedding and store in `long_term_memories`.
"""
import re
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.models import LongTermMemory
from app.rag.embedder import get_embedder
from app.orchestrator.llm_client import llm_router

logger = logging.getLogger(__name__)


async def consolidate_user_memories(
    user_id: str,
    user_message: str,
    assistant_response: str,
    conversation_id: str,
    db: Session
):
    """
    Two-stage background memory consolidation.
    Extracts durable facts/events and stores/updates long-term vector memories.
    """
    # Quick filter: skip trivial messages
    if len(user_message.strip()) < 15:
        return

    # Stage 1: Candidate Extraction
    extraction_prompt = (
        f"Analyze the following conversation turn between a User and MindCare AI.\n"
        f"USER: {user_message}\n"
        f"ASSISTANT: {assistant_response[:400]}\n\n"
        f"Task: Extract explicit durable facts about the user (Semantic Memory) or major key actions performed (Episodic Memory).\n"
        f"Format as a raw JSON array of objects:\n"
        f'[{{\"type\": \"semantic\"|\"episodic\", \"content\": \"Concise fact or event statement\", \"importance\": 0.1-1.0}}]\n'
        f"Rules:\n"
        f"1. Extract ONLY clear durable information (e.g., 'User is a medical student', 'User suffers from insomnia', 'User queried ADHD vs ASD comparison').\n"
        f"2. Ignore greetings, general questions, or non-personal facts.\n"
        f"3. Return ONLY valid JSON array. If no durable facts, return []."
    )

    extracted_raw = ""
    try:
        async for token in llm_router.stream_chat(
            messages=[{"role": "user", "content": extraction_prompt}],
            intent="fact_lookup",
            temperature=0.1,
            max_tokens=250
        ):
            extracted_raw += token

        # Clean JSON markdown fences if present
        json_match = re.search(r'\[.*\]', extracted_raw, re.DOTALL)
        if not json_match:
            return
        
        candidates = json.loads(json_match.group(0))
        if not isinstance(candidates, list) or not candidates:
            return

        embedder = get_embedder()

        # Stage 2: Consolidation & Vector Deduplication
        for item in candidates:
            content = item.get("content", "").strip()
            mem_type = item.get("type", "semantic")
            importance = float(item.get("importance", 0.5))

            if not content or len(content) < 10:
                continue

            # Embed content
            embedding = embedder.embed(content)
            emb_str = '[' + ','.join(str(x) for x in embedding) + ']'

            # Check existing similar memories for this user
            check_sql = text("""
                SELECT id::text, 1 - (embedding <=> CAST(:emb AS vector)) AS similarity
                FROM long_term_memories
                WHERE user_id = CAST(:uid AS uuid)
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:emb AS vector)
                LIMIT 1
            """)
            existing = db.execute(check_sql, {'emb': emb_str, 'uid': user_id}).fetchone()

            if existing and float(existing.similarity) >= 0.82:
                # Deduplicate: update last_accessed_at and boost retrieval_count
                mem_id = existing[0]
                update_sql = text("""
                    UPDATE long_term_memories
                    SET last_accessed_at = NOW(),
                        retrieval_count = retrieval_count + 1,
                        confidence_score = LEAST(1.0, confidence_score + 0.05)
                    WHERE id = CAST(:mid AS uuid)
                """)
                db.execute(update_sql, {'mid': mem_id})
                db.commit()
                print(f"[CONSOLIDATION] Deduplicated existing memory (similarity={float(existing.similarity):.2f}): {content}", flush=True)
            else:
                # Insert new memory record
                new_memory = LongTermMemory(
                    user_id=user_id,
                    memory_type=mem_type,
                    content=content,
                    embedding=embedding,
                    importance_score=importance,
                    confidence_score=0.85,
                    retrieval_count=1,
                    source_type='explicit_statement' if mem_type == 'semantic' else 'event',
                    source_conversation_id=conversation_id,
                )
                db.add(new_memory)
                db.commit()
                print(f"[CONSOLIDATION] Inserted new {mem_type.upper()} memory: {content}", flush=True)

    except Exception as e:
        logger.error(f"Memory consolidation failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
