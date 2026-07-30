"""
Hybrid retriever: vector search + FTS → RRF merge → calibrated margin rerank → parent fetch.

Pipeline (Phase 3 Adaptive AI Runtime Engine):
  1. Accept `RetrievalPlan` (from QueryPlanner) or raw query.
  2. Filter by document_ids if specified in plan (e.g. ICD-11 vs DSM-5).
  3. Hybrid Search: Vector search (pgvector) + FTS search (PostgreSQL tsvector).
  4. Dynamic RRF Weighting scaled by database vector coverage.
  5. Calibrated Margin Reranker Bypass:
     - Check bi-encoder cosine similarity & top score margin (score1 - score2).
     - If top_score ≥ 0.88 AND margin ≥ 0.15 ➔ Bypass Cross-Encoder (saves ~45ms latency!).
     - Else ➔ Pass candidate pool to Cross-Encoder (BAAI/bge-reranker-base).
  6. Token-Based Context Budgeting: Accrue context text up to target context token limit.
  7. Return RetrievalResult with context, citations, and detailed stage telemetry.
"""
import re
import time
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.rag.embedder import get_embedder

logger = logging.getLogger(__name__)

# Lazy-load cross-encoder
_reranker = None

def _get_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        logger.info("Loading fast CrossEncoder cross-encoder/ms-marco-MiniLM-L-6-v2...")
        print("[RERANK] Loading lightweight CrossEncoder cross-encoder/ms-marco-MiniLM-L-6-v2...")
        _reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        logger.info("Cross-encoder loaded successfully.")
        print("[RERANK] Cross-encoder loaded successfully!")
    return _reranker


@dataclass
class Citation:
    document_name: str
    chapter: Optional[str]
    section: Optional[str]
    page_number: Optional[int]
    page_range: Optional[str]
    document_id: str
    is_global: bool


@dataclass
class RetrievalResult:
    success: bool                              # True if confidence ≥ threshold
    context: str                               # formatted context for LLM
    citations: List[Citation] = field(default_factory=list)
    best_score: float = 0.0
    chunks_found: int = 0
    bypassed_reranker: bool = False
    message: Optional[str] = None             # set when success=False
    telemetry: Dict[str, Any] = field(default_factory=dict)


def retrieve(
    query: str,
    user_id: str,
    db: Session,
    filters: Optional[Dict] = None,
    plan: Optional[Any] = None,               # Optional RetrievalPlan from QueryPlanner
) -> RetrievalResult:
    """
    Full Phase 3 hybrid retrieval pipeline.
    Consumes RetrievalPlan or raw query string.
    """
    t_start = time.perf_counter()
    telemetry = {}

    # Extract parameters from RetrievalPlan if provided
    search_query = query
    document_ids = ()
    recall_target = settings.RETRIEVAL_TOP_K
    budget_tokens = settings.MAX_RAG_CONTEXT_TOKENS

    if plan:
        search_query = plan.rewritten_query or plan.raw_query
        document_ids = plan.document_ids
        recall_target = plan.recall_target or settings.RETRIEVAL_TOP_K
        budget_tokens = plan.context_budget_tokens or settings.MAX_RAG_CONTEXT_TOKENS

    if filters and "document_id" in filters:
        document_ids = (str(filters["document_id"]),)

    # ── Step 1: Embed query ───────────────────────────────────────────────────
    t0 = time.perf_counter()
    try:
        embedder = get_embedder()
        query_embedding = embedder.embed(search_query)
        telemetry["embed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    except Exception as e:
        logger.error(f"Query embedding failed: {e}")
        return RetrievalResult(
            success=False,
            context='',
            message="Embedding service unavailable. Please try again."
        )

    # ── Step 2: Vector search ─────────────────────────────────────────────────
    t0 = time.perf_counter()
    vector_results = _vector_search(query_embedding, user_id, db, document_ids, top_k=recall_target)
    telemetry["vector_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    # ── Step 3: Full-text search ──────────────────────────────────────────────
    t0 = time.perf_counter()
    fts_results = _fts_search(search_query, user_id, db, document_ids, top_k=recall_target)
    telemetry["fts_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    # ── Step 4: Coverage-scaled RRF merge ─────────────────────────────────────
    t0 = time.perf_counter()
    coverage = _get_embedding_coverage(user_id, db)
    if coverage < 0.20:
        v_weight, f_weight = 0.2, 0.8
    elif coverage < 0.60:
        v_weight, f_weight = 0.5, 0.5
    else:
        v_weight, f_weight = 0.7, 0.3

    candidates_with_scores = _rrf_merge(vector_results, fts_results, vector_weight=v_weight, fts_weight=f_weight)
    candidates = [cid for cid, _ in candidates_with_scores]
    telemetry["rrf_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    telemetry["candidates_count"] = len(candidates)
    telemetry["coverage_pct"] = round(coverage * 100)

    # ── Gap 2: Multi-entity FTS boost for comparison queries ───────────────
    # For comparison queries with 2+ entities, run per-entity FTS sub-queries
    # to guarantee each entity has representation in the candidate pool.
    if plan and plan.intent == "comparison":
        entities = _extract_entities(plan.raw_query)
        if len(entities) >= 2:
            print(f"[RETRIEVER] Multi-entity comparison: {entities}")
            existing_ids = set(candidates)
            for entity in entities:
                entity_chunks = _fts_search(entity, user_id, db, document_ids, top_k=6)
                for chunk_id, score in entity_chunks:
                    if chunk_id not in existing_ids:
                        candidates_with_scores.append((chunk_id, score * 0.75))  # slight discount
                        candidates.append(chunk_id)
                        existing_ids.add(chunk_id)
            telemetry["entity_boost_count"] = len(entities)

    if not candidates:
        telemetry["retrieval_total_ms"] = round((time.perf_counter() - t_start) * 1000, 1)
        doc_note = f" in {plan.document_names[0]}" if plan and plan.document_names else ""
        return RetrievalResult(
            success=False,
            context='',
            chunks_found=0,
            message=f"I searched your uploaded document{doc_note} but couldn't find relevant information.",
            telemetry=telemetry
        )

    # ── Step 5: Calibrated Margin Reranker Bypass ─────────────────────────────
    # Evaluate bi-encoder top score & margin (score1 - score2)
    top_vector_score = vector_results[0][1] if vector_results else 0.0
    second_vector_score = vector_results[1][1] if len(vector_results) > 1 else 0.0
    score_margin = top_vector_score - second_vector_score

    bypassed_reranker = False
    t0 = time.perf_counter()

    if top_vector_score >= settings.RERANK_BYPASS_COSINE_THRESHOLD and score_margin >= settings.RERANK_BYPASS_MARGIN_THRESHOLD:
        bypassed_reranker = True
        # ── Gap 6 fix: use actual per-candidate RRF scores (not identical top_vector_score) ──
        scored_candidates = candidates_with_scores
        telemetry["rerank_ms"] = 0.0
        telemetry["rerank_bypassed"] = True
        logger.info(f"Reranker bypassed: top_score={top_vector_score:.3f} >= {settings.RERANK_BYPASS_COSINE_THRESHOLD}, margin={score_margin:.3f}")
    else:
        # ── Gap 4 fix: pass existing db session instead of opening a new one ──
        scored_candidates = _rerank(search_query, candidates, db)
        telemetry["rerank_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        telemetry["rerank_bypassed"] = False

    # ── Step 6: Confidence gate ───────────────────────────────────────────────
    best_score = scored_candidates[0][1] if scored_candidates else 0.0
    if not scored_candidates or best_score < settings.CONFIDENCE_THRESHOLD:
        telemetry["retrieval_total_ms"] = round((time.perf_counter() - t_start) * 1000, 1)
        return RetrievalResult(
            success=False,
            context='',
            best_score=best_score,
            chunks_found=len(candidates),
            bypassed_reranker=bypassed_reranker,
            message=(
                f"Related content was found, but the relevance score ({best_score:.0%}) "
                f"is below the confidence threshold ({settings.CONFIDENCE_THRESHOLD:.0%})."
            ),
            telemetry=telemetry
        )

    # ── Step 7: Fetch parent chunks with Multi-Document Fair Share Sampling ────
    top_children = [chunk_id for chunk_id, score in scored_candidates[:35]]
    parent_contexts = _fetch_parents_fair_share(top_children, db, max_parents=16)

    context_parts: List[str] = []
    citations: List[Citation] = []
    accumulated_tokens = 0

    for ctx in parent_contexts:
        parent_text = ctx['parent_text']
        approx_tokens = len(parent_text) // 4

        if accumulated_tokens + approx_tokens > budget_tokens and context_parts:
            # Exceeded token budget limit
            break

        source_label = _format_source(ctx)
        context_parts.append(f"[Source: {source_label}]\n{parent_text}")
        accumulated_tokens += approx_tokens

        citations.append(Citation(
            document_name=ctx.get('document_name', 'Unknown'),
            chapter=ctx.get('chapter'),
            section=ctx.get('section'),
            page_number=ctx.get('page_number'),
            page_range=ctx.get('page_range'),
            document_id=str(ctx.get('document_id', '')),
            is_global=ctx.get('is_global', False),
        ))

    context = '\n\n---\n\n'.join(context_parts)
    telemetry["retrieval_total_ms"] = round((time.perf_counter() - t_start) * 1000, 1)
    telemetry["context_tokens"] = accumulated_tokens
    telemetry["context_chars"] = len(context)
    telemetry["context_sources"] = len(citations)

    return RetrievalResult(
        success=True,
        context=context,
        citations=citations,
        best_score=best_score,
        chunks_found=len(candidates),
        bypassed_reranker=bypassed_reranker,
        telemetry=telemetry
    )


def _vector_search(
    embedding: List[float],
    user_id: str,
    db: Session,
    document_ids: Tuple[str, ...],
    top_k: int = 35,
) -> List[Tuple[str, float]]:
    """HNSW cosine similarity search on child chunk embeddings with optional document filtering."""
    try:
        embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
        doc_filter_sql = ""
        params: Dict[str, Any] = {
            'embedding': embedding_str,
            'user_id': user_id,
            'top_k': top_k,
        }

        if document_ids:
            doc_filter_sql = " AND d.id IN :doc_ids"
            params['doc_ids'] = tuple(document_ids)

        sql = text(f"""
            SELECT dc.id::text,
                   1 - (dc.embedding <=> CAST(:embedding AS vector)) AS score
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE dc.chunk_type = 'child'
              AND dc.embedding IS NOT NULL
              AND d.is_latest = TRUE
              AND (dc.is_global = TRUE OR dc.user_id = CAST(:user_id AS uuid))
              {doc_filter_sql}
            ORDER BY dc.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """)
        rows = db.execute(sql, params).fetchall()
        return [(row[0], float(row[1])) for row in rows]
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return []


def _fts_search(
    query: str,
    user_id: str,
    db: Session,
    document_ids: Tuple[str, ...],
    top_k: int = 35,
) -> List[Tuple[str, float]]:
    """PostgreSQL full-text search on child chunks with optional document filtering."""
    try:
        doc_filter_sql = ""
        params: Dict[str, Any] = {
            'query': query,
            'user_id': user_id,
            'top_k': top_k,
        }

        if document_ids:
            doc_filter_sql = " AND d.id IN :doc_ids"
            params['doc_ids'] = tuple(document_ids)

        sql = text(f"""
            SELECT dc.id::text,
                   ts_rank(to_tsvector('english', dc.chunk_text),
                           plainto_tsquery('english', :query)) AS score
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE dc.chunk_type = 'child'
              AND d.is_latest = TRUE
              AND (dc.is_global = TRUE OR dc.user_id = CAST(:user_id AS uuid))
              {doc_filter_sql}
              AND to_tsvector('english', dc.chunk_text) @@ plainto_tsquery('english', :query)
            ORDER BY score DESC
            LIMIT :top_k
        """)
        rows = db.execute(sql, params).fetchall()
        return [(row[0], float(row[1])) for row in rows]
    except Exception as e:
        logger.error(f"FTS search failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return []


def _get_embedding_coverage(user_id: str, db: Session) -> float:
    try:
        sql = text("""
            SELECT
                COUNT(*) FILTER (WHERE dc.embedding IS NOT NULL) AS embedded,
                COUNT(*)                                           AS total
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE dc.chunk_type = 'child'
              AND d.is_latest = TRUE
              AND (dc.is_global = TRUE OR dc.user_id = CAST(:user_id AS uuid))
        """)
        row = db.execute(sql, {'user_id': user_id}).fetchone()
        if not row or row.total == 0:
            return 1.0
        return float(row.embedded) / float(row.total)
    except Exception as e:
        logger.warning(f"Coverage query failed: {e} -- defaulting to balanced weights")
        try:
            db.rollback()
        except Exception:
            pass
        return 0.5


def _rrf_merge(
    vector_results: List[Tuple[str, float]],
    fts_results: List[Tuple[str, float]],
    k: int = 60,
    vector_weight: float = 0.7,
    fts_weight: float = 0.3,
) -> List[Tuple[str, float]]:
    """Reciprocal Rank Fusion. Returns (chunk_id, rrf_score) sorted by score desc."""
    scores: Dict[str, float] = {}
    for rank, (doc_id, _) in enumerate(vector_results):
        scores[doc_id] = scores.get(doc_id, 0.0) + vector_weight * (1.0 / (k + rank + 1))
    for rank, (doc_id, _) in enumerate(fts_results):
        scores[doc_id] = scores.get(doc_id, 0.0) + fts_weight * (1.0 / (k + rank + 1))
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def _extract_entities(query: str) -> List[str]:
    """Extract psychiatric/medical entity names from a comparison query."""
    pattern = re.compile(
        r'\b(ADHD|Attention[\s-]Deficit[\s\w]*Disorder|Autism\s+Spectrum\s+Disorder|ASD|'
        r'Bipolar\s+(?:I+|Type\s+[I1-2]+)?(?:\s+Disorder)?|Schizophrenia|'
        r'Major\s+Depressive\s+Disorder|MDD|PTSD|Post[\s-]Traumatic[\s\w]+Disorder|'
        r'OCD|Obsessive[\s-]Compulsive\s+Disorder|BPD|Borderline\s+Personality\s+Disorder|'
        r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Disorder|Syndrome|Condition|Spectrum))\b',
        re.I
    )
    seen: set = set()
    result: List[str] = []
    for match in pattern.finditer(query):
        key = re.sub(r'\s+', ' ', match.group(0)).lower().strip()
        if key not in seen:
            seen.add(key)
            result.append(match.group(0).strip())
    return result


def _rerank(query: str, chunk_ids: List[str], db: Session) -> List[Tuple[str, float]]:
    """Cross-encoder reranker. Uses the passed db session (no new session opened)."""
    if not chunk_ids:
        return []
    try:
        id_strs = [f"'{cid}'" for cid in chunk_ids]
        sql = text(f"SELECT id::text, chunk_text FROM document_chunks WHERE id IN ({','.join(id_strs)})")
        rows = db.execute(sql).fetchall()
        id_to_text = {row[0]: row[1] for row in rows}

        pairs = [(query, id_to_text[cid]) for cid in chunk_ids if cid in id_to_text]
        valid_ids = [cid for cid in chunk_ids if cid in id_to_text]

        if not pairs:
            return []

        reranker = _get_reranker()
        scores = reranker.predict(pairs, batch_size=16, max_length=256)
        scored = list(zip(valid_ids, [float(s) for s in scores]))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
    except Exception as e:
        logger.error(f"Reranking failed: {e}")
        return [(cid, 0.5) for cid in chunk_ids]


def _fetch_parents(child_ids: List[str], db: Session) -> List[Dict]:
    if not child_ids:
        return []
    try:
        id_strs = [f"'{cid}'" for cid in child_ids]
        sql = text(f"""
            SELECT
                p.id::text           AS parent_id,
                p.chunk_text         AS parent_text,
                p.chapter,
                p.section,
                p.page_number,
                p.page_range,
                d.id::text           AS document_id,
                d.original_name      AS document_name,
                d.is_global
            FROM document_chunks c
            JOIN document_chunks p ON c.parent_chunk_id = p.id
            JOIN documents d        ON c.document_id = d.id
            WHERE c.id IN ({','.join(id_strs)})
        """)
        rows = db.execute(sql).fetchall()
        seen_parents = set()
        results = []
        for row in rows:
            pid = row[0]
            if pid not in seen_parents:
                seen_parents.add(pid)
                results.append({
                    'parent_id': row[0],
                    'parent_text': row[1],
                    'chapter': row[2],
                    'section': row[3],
                    'page_number': row[4],
                    'page_range': row[5],
                    'document_id': row[6],
                    'document_name': row[7],
                    'is_global': row[8],
                })
        return results
    except Exception as e:
        logger.error(f"Fetch parents failed: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        return []


def _fetch_parents_fair_share(child_ids: List[str], db: Session, max_parents: int = 16) -> List[Dict]:
    """
    Multi-Document Fair-Share Round-Robin Sampling:
    Prevents single large documents from dominating the RAG prompt context.
    Ensures every retrieved document gets fair representation in multi-book synthesis.
    """
    raw_results = _fetch_parents(child_ids, db)
    if not raw_results:
        return []

    doc_groups: Dict[str, List[Dict]] = {}
    for r in raw_results:
        doc_id = r['document_id']
        doc_groups.setdefault(doc_id, []).append(r)

    balanced = []
    max_per_doc = max(len(g) for g in doc_groups.values()) if doc_groups else 0

    for i in range(max_per_doc):
        for doc_id, items in doc_groups.items():
            if i < len(items):
                balanced.append(items[i])
                if len(balanced) >= max_parents:
                    break
        if len(balanced) >= max_parents:
            break

    return balanced


def _format_source(ctx: Dict) -> str:
    doc_name = ctx.get('document_name', 'Unknown')
    parts = [f"Book Title: {doc_name}"]
    if ctx.get('chapter'):
        parts.append(f"Chapter: {ctx['chapter']}")
    if ctx.get('section'):
        parts.append(f"Section: {ctx['section']}")
    if ctx.get('page_range'):
        parts.append(f"Page: {ctx['page_range']}")
    elif ctx.get('page_number'):
        parts.append(f"Page: {ctx['page_number']}")
    return ' | '.join(parts)
