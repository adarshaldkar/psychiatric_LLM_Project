"""
Abstract Base Capability Class
"""
from abc import ABC, abstractmethod
from typing import Any
from sqlalchemy.orm import Session

from app.capabilities.schemas import CapabilityResult, ExecutionPlan, CapabilityType

class BaseCapability(ABC):
    capability_type: CapabilityType

    @abstractmethod
    async def execute(
        self,
        plan: ExecutionPlan,
        user_id: str,
        db: Session
    ) -> CapabilityResult:
        """Execute capability and return standardized CapabilityResult."""
        pass
