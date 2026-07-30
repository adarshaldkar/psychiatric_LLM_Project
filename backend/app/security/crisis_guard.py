"""
Dual-Stage Clinical Safety & Crisis Override Guard
Stage 1: Intent & Academic Context Classifier (Prevents false positives on educational queries)
Stage 2: Emergency Self-Harm & Crisis Interceptor (Triggers 988 Lifeline resources)
"""
import re
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# High-risk crisis trigger phrases
CRISIS_KEYWORDS = [
    r"\bsuicide\b", r"\bsuicidal\b", r"\bkill myself\b", r"\bend my life\b",
    r"\bwant to die\b", r"\bself-harm\b", r"\bcutting myself\b", r"\boverdose\b",
    r"\bno reason to live\b", r"\bcan't go on\b", r"\bbetter off dead\b"
]

# Educational / Academic context indicators (False Positive Suppressors)
EDUCATIONAL_KEYWORDS = [
    r"\bpaper\b", r"\bresearch\b", r"\bthesis\b", r"\bstudy\b", r"\bhistory of\b",
    r"\bstatistics\b", r"\bprevention\b", r"\bguidance\b", r"\bdefinition\b",
    r"\bwriting an essay\b", r"\bclass\b", r"\bassignment\b"
]


@dataclass
class CrisisAssessment:
    is_crisis: bool
    risk_score: float  # 0.0 to 1.0
    category: Optional[str] = None
    override_message: Optional[str] = None
    emergency_resources: Optional[Dict[str, str]] = None


class DualStageCrisisGuard:
    def __init__(self):
        self.crisis_pattern = re.compile("|".join(CRISIS_KEYWORDS), re.I)
        self.edu_pattern = re.compile("|".join(EDUCATIONAL_KEYWORDS), re.I)

    def evaluate_prompt(self, user_prompt: str) -> CrisisAssessment:
        if not user_prompt:
            return CrisisAssessment(is_crisis=False, risk_score=0.0)

        # Stage 1: Check for crisis keywords
        has_crisis_keyword = bool(self.crisis_pattern.search(user_prompt))
        has_edu_context = bool(self.edu_pattern.search(user_prompt))

        if not has_crisis_keyword:
            return CrisisAssessment(is_crisis=False, risk_score=0.0)

        # Stage 2: Dual-stage classification
        # If user explicitly states self-harm or immediate distress, override regardless
        is_direct_intent = bool(re.search(r"\b(i (want|plan|feel like|am going) to (kill|end|die|harm))\b", user_prompt, re.I))

        if has_edu_context and not is_direct_intent:
            logger.info(f"[CRISIS GUARD] Educational context detected for query: '{user_prompt[:40]}...'. False positive suppressed.")
            return CrisisAssessment(
                is_crisis=False,
                risk_score=0.25,
                category="EDUCATIONAL_INQUIRY"
            )

        # Active distress / crisis override trigger
        risk_score = 0.95 if is_direct_intent else 0.85

        emergency_resources = {
            "national_lifeline": "988 (Call or Text 24/7 - Free & Confidential)",
            "crisis_text_line": "Text HOME to 741741",
            "international_services": "112 (EU) / 911 (US) / 999 (UK)",
            "website": "https://988lifeline.org"
        }

        override_message = (
            "🚨 **CRISIS SAFETY OVERRIDE**\n\n"
            "If you or someone you know is going through a difficult time, please know that **you are not alone** and support is available 24/7:\n\n"
            "• **National Suicide & Crisis Lifeline**: Call or text **988** (Available 24/7, free and confidential)\n"
            "• **Crisis Text Line**: Text **HOME** to **741741**\n"
            "• **International Emergency Services**: Call **112**, **911**, or **999**\n"
            "• **Online Chat**: [https://988lifeline.org](https://988lifeline.org)\n\n"
            "Please reach out to one of these resources right away."
        )

        logger.warning(f"[CRISIS GUARD] Emergency safety override triggered for user prompt (Risk Score: {risk_score})")

        return CrisisAssessment(
            is_crisis=True,
            risk_score=risk_score,
            category="ACTIVE_CRISIS_DISTRESS",
            override_message=override_message,
            emergency_resources=emergency_resources
        )


crisis_guard = DualStageCrisisGuard()
