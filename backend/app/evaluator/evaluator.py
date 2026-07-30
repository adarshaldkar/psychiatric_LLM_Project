"""
Output Evaluator Layer — Quality & Safety Validation Gate

Evaluates the generated LLM response before/after completion against:
  1. Entity Coverage: Ensures all requested entities (e.g. ADHD AND ASD) are addressed.
  2. Citation Verification: Verifies source citations when document RAG context was used.
  3. Diagnostic Claim Guard: Detects forbidden medical diagnostic claims (e.g. "You have Bipolar").
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    passed: bool
    score: float                                # 0.0 to 1.0
    entity_coverage_passed: bool = True
    citation_passed: bool = True
    safety_passed: bool = True
    warnings: List[str] = field(default_factory=list)


class OutputEvaluator:
    def evaluate(
        self,
        query: str,
        response_text: str,
        intent: str = "general",
        used_rag: bool = False,
        requested_entities: Optional[List[str]] = None
    ) -> EvaluationResult:
        """
        Runs rule-based validation checks on the generated response.
        """
        warnings = []
        entity_passed = True
        citation_passed = True
        safety_passed = True

        # ── Check 1: Entity Coverage ──────────────────────────────────────────
        if intent == "comparison" and requested_entities and len(requested_entities) >= 2:
            missing_entities = [
                ent for ent in requested_entities
                if not re.search(re.escape(ent), response_text, re.I)
            ]
            if missing_entities:
                entity_passed = False
                warnings.append(f"Entity Coverage Warning: Missing requested entities {missing_entities}")

        # ── Check 2: Citation Verification & Placeholder Detection ─────────
        if used_rag and len(response_text) > 100:
            has_citation = bool(re.search(r'\[(?:Source|DSM|ICD|Page|p\.)', response_text, re.I))
            if not has_citation:
                citation_passed = False
                warnings.append("Citation Warning: Response used RAG context but omitted explicit citation tags.")

        # Detect fake generic placeholder citations (e.g. 'Book 1 Page 12', 'Book 2 Page 25')
        placeholder_pattern = re.search(r'Book \d+\s*(?:Page \d+|p\.?\s*\d+)?', response_text, re.I)
        if placeholder_pattern:
            citation_passed = False
            warnings.append(f"Fake Placeholder Citation Detected: '{placeholder_pattern.group(0)}'")

        # ── Check 3: Diagnostic Safety Guard ──────────────────────────────────
        diagnostic_claims = re.findall(
            r'\b(you (have|are diagnosed with|suffer from|definitely have)\s+[A-Z][a-z]+(?:\s+Disorder)?)\b',
            response_text,
            re.I
        )
        if diagnostic_claims:
            safety_passed = False
            warnings.append(f"Safety Violation: Direct diagnostic claim detected -> '{diagnostic_claims[0][0]}'")

        # ── Check 4: Grounded Evidence & Web URL Verification ─────────────────
        web_evidence_passed = True
        if ("WEB SEARCH EVIDENCE" in response_text or "MCP EVIDENCE" in response_text or "http://" in response_text or "https://" in response_text):
            has_url = bool(re.search(r'https?://[^\s)]+', response_text, re.I))
            if not has_url:
                web_evidence_passed = False
                warnings.append("Grounding Warning: Web search/MCP response omitted source URL links.")

        # ── Check 5: Zero Synthetic Citation & Fake Product Audit ─────────────
        zero_hallucination_passed = True
        fake_doi_match = re.search(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', response_text, re.I)
        if fake_doi_match and not ("context" in response_text.lower() and fake_doi_match.group(0) in response_text):
            # Synthetic DOI generated without being in context
            zero_hallucination_passed = False
            warnings.append(f"Synthetic Citation Warning: Generated unverified DOI '{fake_doi_match.group(0)}'")

        fake_product_match = re.search(r'\b(NeuroSync|Wearable Insight)\b', response_text, re.I)
        if fake_product_match:
            zero_hallucination_passed = False
            warnings.append(f"Synthetic Product Warning: Generated unverified brand name '{fake_product_match.group(0)}'")

        # Calculate overall score
        checks = [entity_passed, citation_passed, safety_passed, web_evidence_passed, zero_hallucination_passed]
        passed_count = sum(1 for c in checks if c)
        score = round(passed_count / len(checks), 2)
        passed = (score >= 0.66) and safety_passed

        if warnings:
            print(f"[EVALUATOR] Score: {score:.2f} | Warnings: {warnings}", flush=True)
        else:
            print(f"[EVALUATOR] Response Verification PASSED (Score: {score:.2f})", flush=True)

        return EvaluationResult(
            passed=passed,
            score=score,
            entity_coverage_passed=entity_passed,
            citation_passed=citation_passed,
            safety_passed=safety_passed,
            warnings=warnings
        )


output_evaluator = OutputEvaluator()
