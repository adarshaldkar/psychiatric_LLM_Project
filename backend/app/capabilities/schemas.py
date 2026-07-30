"""
Capability Layer Data Schemas & Contracts
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

class CapabilityType(str, Enum):
    DOCUMENTS = "DOCUMENTS"
    MEMORY = "MEMORY"
    WEB_SEARCH = "WEB_SEARCH"
    MCP_TOOLS = "MCP_TOOLS"
    CALCULATOR = "CALCULATOR"

class CapabilityStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    SKIPPED = "SKIPPED"

@dataclass
class ContextChunk:
    text: str
    source_title: str
    source_type: str               # 'document' | 'memory' | 'web' | 'mcp'
    document_id: Optional[str] = None
    page_number: Optional[int] = None
    url: Optional[str] = None
    confidence_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CapabilityResult:
    capability: CapabilityType
    status: CapabilityStatus
    chunks: List[ContextChunk] = field(default_factory=list)
    latency_ms: float = 0.0
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExecutionPlan:
    capabilities: List[CapabilityType]
    retrieval_budget_tokens: int = 2500
    timeout_ms: int = 4000
    safety_level: str = "STANDARD" # 'STANDARD' | 'CRISIS' | 'STRICT'
    response_style: str = "CONVERSATIONAL"
    raw_query: str = ""
    rewritten_query: str = ""
    document_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
