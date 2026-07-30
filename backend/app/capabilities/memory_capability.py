"""
Memory Capability Module
Wraps 3-Tier Continuity Engine (Long-Term Vector Memory) and returns normalized ContextChunk objects.
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
from app.continuity import retrieve_continuity_context, ContinuityResult
from app.models.models import Conversation

logger = logging.getLogger(__name__)


class MemoryCapability(BaseCapability):
    capability_type = CapabilityType.MEMORY

    async def execute(
        self,
        plan: ExecutionPlan,
        user_id: str,
        db: Session
    ) -> CapabilityResult:
        t0 = time.perf_counter()
        query = plan.raw_query

        try:
            # Fetch conversation summary if available
            conv_summary = None
            if plan.metadata and "conversation_id" in plan.metadata:
                conv = db.query(Conversation).filter(Conversation.id == plan.metadata["conversation_id"]).first()
                if conv:
                    conv_summary = conv.summary

            cont_res: ContinuityResult = retrieve_continuity_context(
                query=query,
                user_id=user_id,
                db=db,
                conversation_summary=conv_summary,
                top_k=3
            )

            latency_ms = round((time.perf_counter() - t0) * 1000, 1)

            if not cont_res.formatted_context:
                return CapabilityResult(
                    capability=CapabilityType.MEMORY,
                    status=CapabilityStatus.SUCCESS,
                    chunks=[],
                    latency_ms=latency_ms,
                    message="No relevant past memories retrieved."
                )

            chunks: List[ContextChunk] = []

            # Format memory context block as normalized chunk
            chunks.append(ContextChunk(
                text=cont_res.formatted_context,
                source_title="User Continuity Memory",
                source_type="memory",
                confidence_score=0.90,
                metadata={"memory_count": len(cont_res.retrieved_memories)}
            ))

            return CapabilityResult(
                capability=CapabilityType.MEMORY,
                status=CapabilityStatus.SUCCESS,
                chunks=chunks,
                latency_ms=latency_ms
            )

        except Exception as e:
            latency_ms = round((time.perf_counter() - t0) * 1000, 1)
            logger.error(f"Memory capability execution failed: {e}")
            return CapabilityResult(
                capability=CapabilityType.MEMORY,
                status=CapabilityStatus.FAILED,
                latency_ms=latency_ms,
                message=str(e)
            )

memory_capability = MemoryCapability()
