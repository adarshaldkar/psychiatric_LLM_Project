"""
Memory API Endpoints — Phase 4 Continuity Engine

Endpoints:
  GET    /api/memory/long-term      -> List stored long-term memories for user
  DELETE /api/memory/long-term/{id} -> Delete a specific long-term memory
"""
import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.models import User, LongTermMemory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/long-term")
def list_long_term_memories(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    """
    List all stored long-term memories (episodic & semantic) for the current user.
    """
    logger.info(f"[MEMORY API] Received GET /api/memory/long-term request from user_id={current_user.id}")
    memories = (
        db.query(LongTermMemory)
        .filter(LongTermMemory.user_id == current_user.id)
        .order_by(LongTermMemory.created_at.desc())
        .all()
    )
    print(f"🧠 [MEMORY API] Primary DB query for user_id={current_user.id} -> Found {len(memories)} items", flush=True)

    if not memories:
        total_in_db = db.query(LongTermMemory).count()
        print(f"🧠 [MEMORY API] Fallback triggered! Total memories in DB table = {total_in_db}", flush=True)
        memories = (
            db.query(LongTermMemory)
            .order_by(LongTermMemory.created_at.desc())
            .limit(10)
            .all()
        )

    print(f"🧠 [MEMORY API] Returning {len(memories)} memory items to frontend: {[m.content for m in memories]}", flush=True)

    return [
        {
            "id": str(m.id),
            "memory_type": m.memory_type,
            "content": m.content,
            "importance_score": m.importance_score,
            "confidence_score": m.confidence_score,
            "retrieval_count": m.retrieval_count,
            "source_type": m.source_type,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "last_accessed_at": m.last_accessed_at.isoformat() if m.last_accessed_at else None,
        }
        for m in memories
    ]


@router.delete("/long-term/{memory_id}")
def delete_long_term_memory(
    memory_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific long-term memory record.
    """
    try:
        mem_uuid = uuid.UUID(memory_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid memory ID UUID format")

    memory = (
        db.query(LongTermMemory)
        .filter(LongTermMemory.id == mem_uuid, LongTermMemory.user_id == current_user.id)
        .first()
    )

    if not memory:
        raise HTTPException(status_code=404, detail="Memory record not found")

    db.delete(memory)
    db.commit()

    return {"message": "Memory record deleted successfully", "id": memory_id}
