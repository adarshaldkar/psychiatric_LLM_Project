"""
Classified Prompt Injection Guard
Detects and categorizes adversarial prompts against a 6-attack taxonomy:
1. Jailbreak Persona
2. System Prompt Extraction
3. Tool Abuse / Command Escalation
4. Data Exfiltration
5. Role Override
6. Instruction Override
"""
import re
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

@dataclass
class InjectionCheckResult:
    is_injection: bool
    attack_category: Optional[str] = None
    matched_pattern: Optional[str] = None
    redirect_message: Optional[str] = None


class ClassifiedInjectionGuard:
    def __init__(self):
        # 6 Attack Taxonomy Regular Expressions
        self.attack_patterns = {
            "JAILBREAK_PERSONA": r'\b(act as (DAN|jailbroken|unfiltered)|do anything now|ignore all ethics|pretend to be evil)\b',
            "SYSTEM_PROMPT_EXTRACTION": r'\b(repeat (your|the) (system prompt|master instructions|initial instructions|prompt verbatim)|show me your rules)\b',
            "TOOL_ABUSE_ESCALATION": r'\b(run (terminal|shell|cmd|powershell) command|execute script|drop database|rm -rf)\b',
            "DATA_EXFILTRATION": r'\b(expose (other|all) (user|patient) (data|records|memories|emails)|dump database)\b',
            "ROLE_OVERRIDE": r'\b(you are no longer (an AI|MindCare AI)|forget you are a psychiatric assistant)\b',
            "INSTRUCTION_OVERRIDE": r'\b(ignore (all )?previous instructions|disregard prior directives|override system rules)\b',
        }

    def evaluate_prompt(self, user_message: str) -> InjectionCheckResult:
        """
        Classifies user prompt against attack taxonomy.
        Returns InjectionCheckResult.
        """
        if not user_message:
            return InjectionCheckResult(is_injection=False)

        text_lower = user_message.lower()

        for category, pattern in self.attack_patterns.items():
            match = re.search(pattern, text_lower, re.I)
            if match:
                matched_text = match.group(0)
                logger.warning(f"Security Alert: Classified Prompt Injection Detected [{category}] -> '{matched_text}'")
                return InjectionCheckResult(
                    is_injection=True,
                    attack_category=category,
                    matched_pattern=matched_text,
                    redirect_message=(
                        "I am specialized in mental-health and psychiatric topics. "
                        "I cannot fulfill instructions attempting to override system guardrails or expose internal configurations."
                    )
                )

        return InjectionCheckResult(is_injection=False)

injection_guard = ClassifiedInjectionGuard()
