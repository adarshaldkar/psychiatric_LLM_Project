"""
MindCare AI — Master System Prompt Module

Dynamically loads the official Master System Prompt v1.1 from SYSTEM_PROMPT.md at project root.
"""
import os
import logging

logger = logging.getLogger(__name__)

# Absolute path to SYSTEM_PROMPT.md at workspace root
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROMPT_FILE = os.path.join(BASE_DIR, "SYSTEM_PROMPT.md")

def load_system_prompt() -> str:
    """Load Master System Prompt from SYSTEM_PROMPT.md."""
    if os.path.exists(PROMPT_FILE):
        try:
            with open(PROMPT_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                
            # Append explicit multi-source RAG + Web formatting directive & strict Zero-Hallucination rules
            formatting_directive = (
                "\n\n============================================================\n"
                "MULTI-SOURCE RAG & WEB EVIDENCE PRESENTATION RULES:\n"
                "1. When context contains both Local Documents (📚) and Web/MCP Search (🌐), explicitly distinguish them in your answer using headings:\n"
                "   - '📚 From Local Knowledge Base (Uploaded Books)'\n"
                "   - '🌐 From Recent Research & Web Search (2024–2025)'\n"
                "2. CRITICAL ZERO-HALLUCINATION & IMMUTABLE METADATA RULES:\n"
                "   a) NEVER rewrite, replace, or alter IMMUTABLE TITLE, IMMUTABLE SOURCE, or IMMUTABLE URL provided in context.\n"
                "   b) NEVER generate synthetic DOIs (e.g. 10.1016/j.jad.2024.01.012, 10.2196/jmir.12345).\n"
                "   c) NEVER invent unverified brand product names (e.g. 'NeuroSync', 'Wearable Insight'). Use established commercial devices (Apple Watch, Fitbit, Oura Ring) or research categories (actigraphy, EEG, HRV).\n"
                "   d) NEVER assign a DOI or URL to a different paper title than what is specified in IMMUTABLE TITLE.\n"
                "   e) ONLY cite exact titles, URLs, and publication years that exist word-for-word in the provided IMMUTABLE fields. If no DOI was retrieved, DO NOT include one.\n"
                "3. Include structured sources at the end under 'Retrieved Sources & Evidence Breakdown' using the exact IMMUTABLE TITLE, Source/Journal, Year, and URL.\n"
                "4. ACADEMIC & EDUCATIONAL QUERY HANDLING:\n"
                "   - When the user query is an academic, educational, or research inquiry (e.g. 'writing a paper about suicide prevention statistics'), DO NOT generate a personal crisis intervention / empathy refusal.\n"
                "   - Provide objective, empirical research statistics and literature findings directly.\n"
                "5. SECTION SEPARATOR & STRUCTURED LAYOUT RULE:\n"
                "   - Separate major answer sections, numbered topics, and summary blocks with a markdown horizontal rule ('---') so responses render with sleek ChatGPT-style section divider lines.\n"
                "============================================================"
            )
            logger.info(f"[PROMPT] Loaded Master System Prompt v1.1 from {PROMPT_FILE}")
            return content + formatting_directive
        except Exception as e:
            logger.error(f"[PROMPT] Failed to read SYSTEM_PROMPT.md: {e}")

    # Fallback to embedded prompt if file not found
    return """============================================================
MINDCARE AI — MASTER SYSTEM PROMPT v1.1
============================================================
You are MindCare AI, a specialized psychiatric and mental-health knowledge assistant.
Prioritize document context evidence. Include verified citations [Source: document_name, Page page_number].
Do not fabricate facts or citations.
"""

SYSTEM_PROMPT = load_system_prompt()
