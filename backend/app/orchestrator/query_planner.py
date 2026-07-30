"""
Query Planner module — Component 1 of the Adaptive AI Runtime Engine (Phase 3).

Responsibilities:
  1. Intent & Complexity Classification (DEFINITION, COMPARISON, SUMMARY, FACT_LOOKUP, BROAD, GREETING, OUT_OF_SCOPE)
  2. Normalized Document Intent & Filter Resolution (matches "ICD-11", "DSM-5", "my latest book" -> document_ids)
  3. Conversation Resolution & Anaphora Rewriting ("its treatment" -> "treatment of Major Depressive Disorder")
  4. Candidate Pool Range Sizing & Target Context Budgeting
  5. Deterministic Temperature Strategy Assignment

Produces an immutable `RetrievalPlan` dataclass consumed by downstream components.
"""
import re
import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.models import Document, Message
from app.orchestrator.scope_guard import classify_scope, ScopeCategory
from app.orchestrator.safety import check_crisis_safety

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievalPlan:
    raw_query: str
    rewritten_query: str
    rewritten_flag: bool
    document_ids: Tuple[str, ...]          # Resolved document UUID strings
    document_names: Tuple[str, ...]        # Resolved document original filenames
    intent: str                            # definition | comparison | summary | fact_lookup | broad | greeting
    complexity: str                        # simple | moderate | complex
    recall_target: int                     # Candidate pool size (8 to 40)
    context_budget_tokens: int             # e.g., 2500
    temperature: float                     # 0.1 to 0.5
    requires_search: bool                  # False for greetings, out of scope, or crisis
    is_crisis: bool = False
    crisis_message: Optional[str] = None
    scope_category: str = "IN_SCOPE"
    scope_message: Optional[str] = None
    requires_memory: bool = False


# ── OpenRouter Free-Tier Total Token Budget ──────────────────────────────
# Free tier hard limit: ~7580 input tokens total.
# We reserve 650 tokens for LLM output, leaving ~6350 tokens for the prompt.
# Breakdown: system_prompt (~600) + history (~800) + query (~100) = ~1500 fixed.
# Remaining ~4850 tokens available for RAG context. We stay well below that.
OPENROUTER_INPUT_LIMIT = 128000   # High-capacity cloud model input limit (Groq 128k context)
RESERVED_OUTPUT_TOKENS = 5000     # Maximum output token budget for detailed responses
MIN_OUTPUT_TOKENS = 500           # Guaranteed output budget floor

# Intent candidate targets and context budgets
INTENT_CONFIG = {
    "fact_lookup": {"candidates": 10, "budget_tokens": 700,  "temp": 0.25},
    "definition":  {"candidates": 15, "budget_tokens": 900,  "temp": 0.25},
    "comparison":  {"candidates": 28, "budget_tokens": 1000, "temp": 0.25},
    "summary":     {"candidates": 20, "budget_tokens": 900,  "temp": 0.3},
    "broad":       {"candidates": 20, "budget_tokens": 900,  "temp": 0.3},
    "general":     {"candidates": 15, "budget_tokens": 700,  "temp": 0.4},
}


def _normalize_tokens(text: str) -> set:
    """Normalize text into alphanumeric tokens for alias matching."""
    return set(re.findall(r'[a-z0-9]+', text.lower()))


class QueryPlanner:
    def plan(
        self,
        user_message: str,
        past_messages: List[Message],
        user_id: str,
        db: Session
    ) -> RetrievalPlan:
        """
        Build an immutable RetrievalPlan for a user query.
        """
        # Truncate prompt input to 4000 chars ceiling to prevent context budget overflow
        raw_query = user_message.strip()[:4000]

        # ── 1. Safety Check ───────────────────────────────────────────────────
        is_crisis, crisis_msg = check_crisis_safety(raw_query)
        if is_crisis:
            return RetrievalPlan(
                raw_query=raw_query,
                rewritten_query=raw_query,
                rewritten_flag=False,
                document_ids=(),
                document_names=(),
                intent="crisis",
                complexity="simple",
                recall_target=0,
                context_budget_tokens=0,
                temperature=0.0,
                requires_search=False,
                is_crisis=True,
                crisis_message=crisis_msg,
            )

        # ── 2. Scope Guard Check ──────────────────────────────────────────────
        scope_cat, scope_msg = classify_scope(raw_query)
        if scope_cat == ScopeCategory.OUT_OF_SCOPE and scope_msg:
            return RetrievalPlan(
                raw_query=raw_query,
                rewritten_query=raw_query,
                rewritten_flag=False,
                document_ids=(),
                document_names=(),
                intent="out_of_scope",
                complexity="simple",
                recall_target=0,
                context_budget_tokens=0,
                temperature=0.4,
                requires_search=False,
                scope_category=scope_cat.value,
                scope_message=scope_msg,
            )

        # ── 3. Greeting / Simple Conversational Detection (Gap 3 fix: regex-based, 20+ patterns) ──
        text_lower = raw_query.lower().strip()
        GREETING_RE = re.compile(
            r'^(hi+|hello+|hey+|good\s+(morning|afternoon|evening|night)|'
            r'thanks?(?:\s+you)?|thank\s+you|how\s+are\s+you|how\s+r\s+u|'
            r'what\s+can\s+you\s+do|who\s+are\s+you|nice\s+to\s+meet|'
            r'greetings|howdy|sup|okay|ok|sure|got\s+it|alright|'
            r'sounds?\s+good|great|perfect|awesome|cool|nice)[\s!?.,]*$',
            re.I
        )
        if GREETING_RE.match(text_lower):
            return RetrievalPlan(
                raw_query=raw_query,
                rewritten_query=raw_query,
                rewritten_flag=False,
                document_ids=(),
                document_names=(),
                intent="greeting",
                complexity="simple",
                recall_target=0,
                context_budget_tokens=0,
                temperature=0.5,
                requires_search=False,
            )

        # ── 4. Document Intent & Filter Resolution ────────────────────────────
        matched_doc_ids, matched_doc_names = self._resolve_document_filters(raw_query, user_id, db)

        # ── 5. Anaphora & Co-reference Query Rewriting ────────────────────────
        rewritten_query, rewritten_flag = self._rewrite_query_if_needed(raw_query, past_messages)

        # ── 6. Intent & Complexity Classification (Gap 1 fix: ternary complexity) ──
        intent = self._classify_intent(raw_query)
        cfg = INTENT_CONFIG.get(intent, INTENT_CONFIG["general"])

        if intent in {"comparison", "summary", "broad"}:
            complexity = "complex"
        elif intent in {"definition", "general"}:
            complexity = "moderate"
        else:  # fact_lookup, greeting, crisis
            complexity = "simple"

        # ── 7. Continuity Memory Determination ──────────────────────────────
        memory_indicators = {"i", "my", "me", "remember", "past", "last", "mentioned", "preference", "discussed", "talked", "earlier", "before", "history"}
        query_words = set(re.findall(r'[a-z0-9]+', raw_query.lower()))
        requires_memory = bool(query_words.intersection(memory_indicators) or rewritten_flag or len(past_messages) >= 3)

        return RetrievalPlan(
            raw_query=raw_query,
            rewritten_query=rewritten_query,
            rewritten_flag=rewritten_flag,
            document_ids=tuple(matched_doc_ids),
            document_names=tuple(matched_doc_names),
            intent=intent,
            complexity=complexity,
            recall_target=cfg["candidates"],
            context_budget_tokens=cfg["budget_tokens"],
            temperature=cfg["temp"],
            requires_search=True,
            scope_category=scope_cat.value,
            requires_memory=requires_memory,
        )

    def _resolve_document_filters(
        self,
        query: str,
        user_id: str,
        db: Session
    ) -> Tuple[List[str], List[str]]:
        """
        Extract explicit document references from query by comparing query tokens
        against accessible user documents (and global documents).
        Matches normalized aliases like 'icd-11' -> 'icd-_11_2018.pdf'.
        """
        query_tokens = _normalize_tokens(query)
        if not query_tokens:
            return [], []

        # Fetch accessible documents for user
        docs = (
            db.query(Document)
            .filter(
                (Document.is_global == True) | (Document.user_id == user_id),
                Document.is_latest == True,
                Document.status.in_(["chat_ready", "ready"])
            )
            .all()
        )

        matched_ids = []
        matched_names = []

        # Keywords indicating document intent
        has_doc_indicator = any(kw in query_tokens for kw in {"document", "book", "pdf", "file", "icd", "dsm", "manual", "uploaded", "guide"})

        if not has_doc_indicator:
            return [], []

        # Handle "latest uploaded book"
        if "latest" in query_tokens and ("book" in query_tokens or "document" in query_tokens or "file" in query_tokens):
            sorted_docs = sorted(docs, key=lambda d: d.created_at, reverse=True)
            if sorted_docs:
                return [str(sorted_docs[0].id)], [sorted_docs[0].original_name]

        for doc in docs:
            # Tokenize document name & title
            doc_name_clean = re.sub(r'\.(pdf|docx|txt|pptx|png|jpg|jpeg)$', '', doc.original_name.lower(), flags=re.I)
            doc_tokens = _normalize_tokens(doc_name_clean)

            # Extract key acronyms/numbers e.g. "icd11", "icd", "11", "dsm5", "dsm", "5"
            acronyms = set()
            for t in doc_tokens:
                if t in {"icd", "dsm", "dsm5", "icd11"}:
                    acronyms.add(t)
                m = re.match(r'^(icd|dsm)(\d+)$', t)
                if m:
                    acronyms.add(m.group(1))
                    acronyms.add(m.group(2))
                    acronyms.add(m.group(1) + m.group(2))

            # Check overlap
            overlap = query_tokens.intersection(acronyms)
            if overlap:
                matched_ids.append(str(doc.id))
                matched_names.append(doc.original_name)
                continue

            # Fallback: check token subset match (e.g. "dsm" in doc_name)
            for qt in query_tokens:
                if len(qt) >= 3 and qt in doc_name_clean:
                    matched_ids.append(str(doc.id))
                    matched_names.append(doc.original_name)
                    break

        return matched_ids, matched_names

    def _rewrite_query_if_needed(
        self,
        query: str,
        past_messages: List[Message]
    ) -> Tuple[str, bool]:
        """
        Co-reference & Anaphora resolution:
        If query contains pronouns like "its", "it", "they", "the disorder",
        extract the primary subject from recent past messages and rewrite the query.
        """
        pronominal_patterns = [
            r'\b(its?|they|them|these|this|that|the disorder|the condition)\b'
        ]
        has_pronoun = any(re.search(p, query, re.I) for p in pronominal_patterns)

        if not has_pronoun or not past_messages:
            return query, False

        # Find last user message topic
        last_user_msgs = [m for m in past_messages if m.role == "user"]
        if not last_user_msgs:
            return query, False

        last_msg = last_user_msgs[-1].content.strip()

        # Extract main psychiatric topic from previous message
        topic_match = re.search(
            r'\b(ADHD|Autism|Bipolar|Depression|PTSD|OCD|Schizophrenia|Anxiety|[A-Z][a-z]+ (Disorder|Syndrome|Condition))\b',
            last_msg, re.I
        )

        if topic_match:
            topic = topic_match.group(0)
            cleaned_query = re.sub(
                r'\b(using (only )?the uploaded (ICD-11|DSM-5|document|book|pdf|file))\b',
                '', query, flags=re.I
            ).strip()

            rewritten = f"{cleaned_query} (Subject: {topic})"
            logger.info(f"Query rewritten: '{query}' -> '{rewritten}'")
            return rewritten, True

        return query, False

    def _classify_intent(self, query: str) -> str:
        """Classify query intent into task categories."""
        q = query.lower()
        if any(kw in q for kw in ["compare", "difference between", "versus", "vs.", "differentiate"]):
            return "comparison"
        if any(kw in q for kw in ["summarize", "summary", "overview", "brief me"]):
            return "summary"
        if any(kw in q for kw in ["what is", "define", "meaning of", "definition"]):
            return "definition"
        if any(kw in q for kw in ["what are the criteria", "symptoms of", "diagnostic features", "age of onset", "dosage"]):
            return "fact_lookup"
        if any(kw in q for kw in ["explain", "tell me about", "describe"]):
            return "broad"
        return "general"


query_planner = QueryPlanner()
