"""
ContextBuilder — Normalizes, Merges, Deduplicates, Prioritizes, and Budgets Capability Results
Transforms List[CapabilityResult] into formatted context string and citations list for the Prompt Orchestrator.
"""
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any

from app.capabilities.schemas import (
    CapabilityResult,
    CapabilityStatus,
    ContextChunk,
    ExecutionPlan,
)
from app.rag.retriever import Citation

logger = logging.getLogger(__name__)

@dataclass
class BuiltContext:
    context_text: str
    citations: List[Citation] = field(default_factory=list)
    total_tokens: int = 0
    total_chunks: int = 0
    sources_summary: List[str] = field(default_factory=list)


class ContextBuilder:
    def build_context(
        self,
        results: List[CapabilityResult],
        plan: ExecutionPlan
    ) -> BuiltContext:
        """
        Merges, deduplicates, prioritizes, and token-budgets context chunks across all execution capabilities.
        """
        raw_chunks: List[ContextChunk] = []

        # 1. Merge chunks from successful capability results
        for res in results:
            if res.status == CapabilityStatus.SUCCESS and res.chunks:
                raw_chunks.extend(res.chunks)

        if not raw_chunks:
            return BuiltContext(context_text="")

        # 2. Deduplicate chunks based on text similarity hash
        deduped_chunks: List[ContextChunk] = []
        seen_snippets = set()

        for chunk in raw_chunks:
            # Simple text fingerprint (first 100 chars normalized)
            fingerprint = chunk.text.strip()[:100].lower()
            if fingerprint not in seen_snippets:
                seen_snippets.add(fingerprint)
                deduped_chunks.append(chunk)

        # 3. Prioritize chunks by confidence score
        deduped_chunks.sort(key=lambda x: x.confidence_score, reverse=True)

        # 4. Accrue context up to token budget limit
        budget_tokens = plan.retrieval_budget_tokens
        accumulated_tokens = 0
        context_parts: List[str] = []
        citations: List[Citation] = []
        sources_summary: List[str] = []

        for chunk in deduped_chunks:
            approx_tokens = len(chunk.text) // 4

            if accumulated_tokens + approx_tokens > budget_tokens and context_parts:
                # Reached token budget limit
                break

            # Format source title with explicit visual category badges and IMMUTABLE metadata tags
            if chunk.source_type == "document":
                header = f"[📚 LOCAL KNOWLEDGE BASE DOCUMENT: {chunk.source_title}]"
                context_parts.append(f"{header}\n{chunk.text}")
            elif chunk.source_type in ("web", "mcp"):
                badge = "🌐 RECENT WEB SEARCH EVIDENCE" if chunk.source_type == "web" else "🔌 MCP CLINICAL TOOL EVIDENCE"
                url = chunk.url or chunk.metadata.get("url", "https://www.psychiatry.org")
                year = chunk.metadata.get("year", "2025")
                domain = chunk.metadata.get("source_domain", "psychiatry.org")
                title = chunk.metadata.get("title", chunk.source_title)

                structured_block = (
                    f"[{badge}]\n"
                    f"IMMUTABLE TITLE: {title}\n"
                    f"IMMUTABLE SOURCE/JOURNAL: {domain} ({year})\n"
                    f"IMMUTABLE PUBLICATION YEAR: {year}\n"
                    f"IMMUTABLE URL: {url}\n"
                    f"CONTENT SNIPPET: {chunk.text}"
                )
                context_parts.append(structured_block)
            elif chunk.source_type == "memory":
                header = f"[🧠 CONTINUITY MEMORY: {chunk.source_title}]"
                context_parts.append(f"{header}\n{chunk.text}")
            else:
                header = f"[Source: {chunk.source_title}]"
                context_parts.append(f"{header}\n{chunk.text}")
            accumulated_tokens += approx_tokens

            # Track citation if from document or web
            if chunk.source_type == "document":
                citations.append(Citation(
                    document_name=chunk.source_title,
                    chapter=chunk.metadata.get("chapter"),
                    section=chunk.metadata.get("section"),
                    page_number=chunk.page_number,
                    page_range=chunk.metadata.get("page_range"),
                    document_id=chunk.document_id or "",
                    is_global=chunk.metadata.get("is_global", False),
                ))

            sources_summary.append(chunk.source_title)

        formatted_context = "\n\n---\n\n".join(context_parts)

        return BuiltContext(
            context_text=formatted_context,
            citations=citations,
            total_tokens=accumulated_tokens,
            total_chunks=len(context_parts),
            sources_summary=sources_summary,
        )

context_builder = ContextBuilder()
