"""
Continuity Engine package initializer.
"""
from app.continuity.short_term import get_short_term_context
from app.continuity.summarizer import update_conversation_summary
from app.continuity.consolidation import consolidate_user_memories
from app.continuity.retriever import retrieve_continuity_context, ContinuityResult
