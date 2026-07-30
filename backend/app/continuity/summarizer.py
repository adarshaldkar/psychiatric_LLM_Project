"""
Continuity Engine — Rolling Conversation Summarizer

Responsibilities:
  1. Detect when a conversation's total message count exceeds threshold (e.g. > 6 turns).
  2. Generate a rolling summary of older turns.
  3. Save the updated summary into PostgreSQL `conversations.summary`.
"""
import logging
from typing import List
from sqlalchemy.orm import Session

from app.models.models import Conversation, Message
from app.orchestrator.llm_client import llm_router

logger = logging.getLogger(__name__)


async def update_conversation_summary(
    conversation_id: str,
    db: Session
) -> str:
    """
    Checks if conversation requires summarization and updates `conversations.summary`.
    Returns current or updated summary.
    """
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return ""

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    if len(messages) <= 6:
        return conv.summary or ""

    # Generate summary for turns older than the last 4
    older_messages = messages[:-4]
    formatted_past = "\n".join([f"{m.role.upper()}: {m.content[:300]}" for m in older_messages])

    prompt = (
        f"Summarize the key psychiatric concepts, user concerns, and topics discussed in this conversation:\n\n"
        f"{formatted_past}\n\n"
        f"Produce a concise 2-3 sentence executive summary. No commentary."
    )

    summary_text = ""
    try:
        async for token in llm_router.stream_chat(
            messages=[{"role": "user", "content": prompt}],
            intent="summary",
            temperature=0.2,
            max_tokens=200
        ):
            summary_text += token

        summary_clean = summary_text.strip()
        if summary_clean:
            conv.summary = summary_clean
            db.commit()
            print(f"[CONTINUITY] Updated Conversation Summary ({len(messages)} turns): {summary_clean[:60]}...", flush=True)
            return summary_clean
    except Exception as e:
        logger.error(f"Conversation summarization failed: {e}")

    return conv.summary or ""
