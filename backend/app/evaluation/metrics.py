"""
Evaluation Metrics & Standardized Result Schema
Defines EvaluationResult data structures and metric calculation utilities.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class EvaluationResult:
    evaluator_name: str
    score: float  # 0.0 to 1.0 (1.0 = 100% Perfect)
    passed: bool
    latency_ms: float = 0.0
    metrics_dict: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
