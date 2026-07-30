"""
CapabilityExecutor — Async Parallel Capability Execution Manager
Runs required capabilities in parallel with strict per-task timeout management.
"""
import time
import asyncio
import logging
from typing import Dict, List
from sqlalchemy.orm import Session

from app.capabilities.schemas import (
    ExecutionPlan,
    CapabilityResult,
    CapabilityType,
    CapabilityStatus,
)
from app.capabilities.base_capability import BaseCapability

logger = logging.getLogger(__name__)

class CapabilityExecutor:
    def __init__(self):
        self._registry: Dict[CapabilityType, BaseCapability] = {}

    def register(self, capability: BaseCapability):
        """Register a capability handler."""
        self._registry[capability.capability_type] = capability

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        user_id: str,
        db: Session
    ) -> List[CapabilityResult]:
        """
        Executes all capabilities specified in ExecutionPlan concurrently.
        Applies per-task timeout management to prevent any single capability from blocking execution.
        """
        tasks = []
        capability_order: List[CapabilityType] = []
        timeout_sec = max(0.5, float(plan.timeout_ms) / 1000.0)

        for cap_type in plan.capabilities:
            if cap_type in self._registry:
                handler = self._registry[cap_type]
                task = self._execute_single_with_timeout(handler, plan, user_id, db, timeout_sec)
                tasks.append(task)
                capability_order.append(cap_type)
            else:
                logger.warning(f"Capability {cap_type} not registered in CapabilityExecutor.")

        if not tasks:
            return []

        t0 = time.perf_counter()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time_ms = round((time.perf_counter() - t0) * 1000, 1)

        final_results: List[CapabilityResult] = []

        for cap_type, res in zip(capability_order, results):
            if isinstance(res, Exception):
                logger.error(f"Capability {cap_type} failed with exception: {res}")
                final_results.append(CapabilityResult(
                    capability=cap_type,
                    status=CapabilityStatus.FAILED,
                    latency_ms=total_time_ms,
                    message=str(res)
                ))
            elif isinstance(res, CapabilityResult):
                final_results.append(res)

        return final_results

    async def _execute_single_with_timeout(
        self,
        handler: BaseCapability,
        plan: ExecutionPlan,
        user_id: str,
        db: Session,
        timeout_sec: float
    ) -> CapabilityResult:
        t0 = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                handler.execute(plan, user_id, db),
                timeout=timeout_sec
            )
            result.latency_ms = round((time.perf_counter() - t0) * 1000, 1)
            return result
        except asyncio.TimeoutError:
            latency = round((time.perf_counter() - t0) * 1000, 1)
            logger.warning(f"Capability {handler.capability_type} TIMEOUT after {latency}ms")
            return CapabilityResult(
                capability=handler.capability_type,
                status=CapabilityStatus.TIMEOUT,
                latency_ms=latency,
                message=f"Capability execution timed out after {timeout_sec}s"
            )
        except Exception as e:
            latency = round((time.perf_counter() - t0) * 1000, 1)
            logger.error(f"Capability {handler.capability_type} failed: {e}")
            return CapabilityResult(
                capability=handler.capability_type,
                status=CapabilityStatus.FAILED,
                latency_ms=latency,
                message=str(e)
            )

capability_executor = CapabilityExecutor()

# Register core default capabilities
from app.capabilities.document_capability import document_capability
from app.capabilities.web_search import web_search_capability
from app.capabilities.memory_capability import memory_capability

capability_executor.register(document_capability)
capability_executor.register(web_search_capability)
capability_executor.register(memory_capability)

from app.capabilities.mcp_capability import mcp_capability
capability_executor.register(mcp_capability)


