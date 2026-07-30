"""
Continuity Engine — Short-Term Memory Manager

Responsibilities:
  1. Fetch recent messages for a conversation.
  2. Perform Deep History Sanitization (strip past RAG context & sources).
  3. Dynamic Token Budgeting: Select recent turns fitting within token budget (~1000 tokens).
"""
import re
import logging
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.models import Message

logger = logging.getLogger(__name__)


def _sanitize_history_message(content: str) -> str:
    """Sanitize past assistant messages by stripping old RAG context blocks and footers."""
    if not content:
        return ""
    
    # Strip RETRIEVED DOCUMENT CONTEXT blocks
    content = re.sub(
        r'={10,}\s*RETRIEVED DOCUMENT CONTEXT\s*={10,}.*?={10,}',
        '',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )
    # Strip SOURCES & CITATIONS footers
    content = re.sub(
        r'SOURCES & CITATIONS:.*$',
        '',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )
    # Strip Fallback notices
    content = re.sub(
        r'Notice:.*?Answering from general knowledge\.\.\.',
        '',
        content,
        flags=re.IGNORECASE
    )
    return content.strip()


def get_short_term_context(
    messages: List[Message],
    max_tokens: int = 1000
) -> List[Dict[str, str]]:
    """
    Returns a sanitized list of recent OpenAI-style messages
    fitting within the max_tokens context budget.
    """
    sanitized_messages: List[Dict[str, str]] = []
    accumulated_tokens = 0

    # Process from newest to oldest
    for msg in reversed(messages[-8:]):
        clean_text = _sanitize_history_message(msg.content)
        if not clean_text:
            continue

        approx_tokens = len(clean_text) // 4
        if accumulated_tokens + approx_tokens > max_tokens and sanitized_messages:
            break

        sanitized_messages.append({"role": msg.role, "content": clean_text})
        accumulated_tokens += approx_tokens

    # Reverse back to chronological order
    sanitized_messages.reverse()
    return sanitized_messages
