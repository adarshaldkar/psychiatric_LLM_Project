import re
from enum import Enum
from typing import Tuple, List, Optional

class ScopeCategory(str, Enum):
    IN_SCOPE = "IN_SCOPE"
    RELATED_OR_CONTEXTUAL = "RELATED_OR_CONTEXTUAL"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNCLEAR = "UNCLEAR"

OUT_OF_SCOPE_PATTERNS = [
    r"\b(dsa|leetcode|code|coding|python|javascript|java|cpp|c\+\+|sql|database|html|css)\s+(problem|assignment|solution|bug|error)\b",
    r"\b(write|create|solve|fix)\s+(a\s+)?(script|program|code|function|algorithm|class)\b",
    r"\b(who\s+won|score|match|game|football|cricket|basketball|nba|ipl)\b",
    r"\b(math|calculus|algebra|physics|chemistry)\s+(homework|equation|problem|integral)\b"
]

IN_SCOPE_PATTERNS = [
    r"\b(anxiety|depression|therap|psychiatr|psycholog|counseling|mental|stress|trauma|ptsd|cbt|dbt|dsm|ocd|bipolar|schizophrenia|medication|antidepressant|ssri|panic|phobia|grief|burnout|emotion|wellbeing|mood|self-esteem)\b"
]

OUT_OF_SCOPE_RESPONSE = (
    "I am specialized in mental-health, psychiatric, and psychotherapy topics, "
    "so I cannot assist with general programming, math, sports, or unrelated academic assignments.\n\n"
    "If you are dealing with study stress, exam anxiety, concentration challenges, or any emotional wellbeing topic, "
    "I am here to help with that!"
)

def classify_scope(message: str, history: Optional[List[dict]] = None) -> Tuple[ScopeCategory, Optional[str]]:
    text_lower = message.lower()
    for pattern in OUT_OF_SCOPE_PATTERNS:
        if re.search(pattern, text_lower):
            if "stress" in text_lower or "anxiety" in text_lower or "panic" in text_lower:
                return ScopeCategory.RELATED_OR_CONTEXTUAL, None
            return ScopeCategory.OUT_OF_SCOPE, OUT_OF_SCOPE_RESPONSE
    for pattern in IN_SCOPE_PATTERNS:
        if re.search(pattern, text_lower):
            return ScopeCategory.IN_SCOPE, None
    return ScopeCategory.IN_SCOPE, None
