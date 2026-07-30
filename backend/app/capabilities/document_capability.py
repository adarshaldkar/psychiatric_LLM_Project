"""
Document Retrieval Capability Module
Wraps Hybrid RAG Retriever (HNSW vector + tsvector FTS) and returns normalized ContextChunk objects.
"""
import time
import logging
from typing import List, Any
from sqlalchemy.orm import Session

from app.capabilities.base_capability import BaseCapability
from app.capabilities.schemas import (
    CapabilityResult,
    ExecutionPlan,
    CapabilityType,
    CapabilityStatus,
    ContextChunk,
)
from app.rag.retriever import retrieve, RetrievalResult

logger = logging.getLogger(__name__)


class DocumentCapability(BaseCapability):
    capability_type = CapabilityType.DOCUMENTS

    async def execute(
        self,
        plan: ExecutionPlan,
        user_id: str,
        db: Session
    ) -> CapabilityResult:
        t0 = time.perf_counter()
        query = plan.rewritten_query or plan.raw_query

        try:
            rag_res: RetrievalResult = retrieve(
                query=query,
                user_id=user_id,
                db=db,
                plan=plan
            )

            latency_ms = round((time.perf_counter() - t0) * 1000, 1)

            if not rag_res.success or not rag_res.context:
                return CapabilityResult(
                    capability=CapabilityType.DOCUMENTS,
                    status=CapabilityStatus.SUCCESS,
                    chunks=[],
                    latency_ms=latency_ms,
                    message=rag_res.message or "No relevant document passages found."
                )

            # Convert citations into ContextChunk objects
            chunks: List[ContextChunk] = []

            # Split RAG context blocks into discrete chunks
            raw_blocks = rag_res.context.split("\n\n---\n\n")
            for idx, block in enumerate(raw_blocks):
                lines = block.strip().split("\n")
                header = lines[0] if lines else ""
                body = "\n".join(lines[1:]) if len(lines) > 1 else block

                # Extract title from header '[Source: Title | ...]'
                source_title = "Uploaded Document"
                if header.startswith("[Source:"):
                    source_title = header.replace("[Source:", "").rstrip("]").strip()

                # Match corresponding citation if available
                cit = rag_res.citations[idx] if idx < len(rag_res.citations) else None
                doc_id = cit.document_id if cit else None
                page_num = cit.page_number if cit else None

                chunks.append(ContextChunk(
                    text=body,
                    source_title=source_title,
                    source_type="document",
                    document_id=doc_id,
                    page_number=page_num,
                    confidence_score=rag_res.best_score or 0.85,
                    metadata={"citation": cit}
                ))

            return CapabilityResult(
                capability=CapabilityType.DOCUMENTS,
                status=CapabilityStatus.SUCCESS,
                chunks=chunks,
                latency_ms=latency_ms,
                metadata={"best_score": rag_res.best_score}
            )

        except Exception as e:
            latency_ms = round((time.perf_counter() - t0) * 1000, 1)
            logger.error(f"Document capability execution failed: {e}")
            return CapabilityResult(
                capability=CapabilityType.DOCUMENTS,
                status=CapabilityStatus.FAILED,
                latency_ms=latency_ms,
                message=str(e)
            )

document_capability = DocumentCapability()
