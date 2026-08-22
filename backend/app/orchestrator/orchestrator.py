import re
import json
import time
import logging
from datetime import datetime
from typing import AsyncGenerator, List, Dict
from sqlalchemy.orm import Session

from app.prompts.system_prompt import SYSTEM_PROMPT
from app.orchestrator.query_planner import query_planner, RetrievalPlan, OPENROUTER_INPUT_LIMIT, RESERVED_OUTPUT_TOKENS, MIN_OUTPUT_TOKENS
from app.orchestrator.llm_client import llm_router
from app.models.models import Message, Conversation
from app.rag.retriever import retrieve, RetrievalResult
from app.continuity import (
    get_short_term_context,
    update_conversation_summary,
    retrieve_continuity_context,
    consolidate_user_memories,
    ContinuityResult
)
from app.evaluator import output_evaluator

logger = logging.getLogger(__name__)


def _sanitize_history_message(content: str) -> str:
    """
    Deep History Sanitization:
    Strips past [RETRIEVED DOCUMENT CONTEXT] blocks, duplicate citations,
    repeated safety disclaimers, and fallback messages from history turns.
    """
    if not content:
        return ""
    # Strip past RAG context blocks (including headers)
    content = re.sub(r'={20,}\s*\n?RETRIEVED DOCUMENT CONTEXT\s*\n?={20,}.*?(?=(SOURCES & CITATIONS|={20,}|$))', '', content, flags=re.DOTALL)
    # Strip past SOURCES & CITATIONS footer
    content = re.sub(r'SOURCES & CITATIONS:.*$', '', content, flags=re.DOTALL)
    # Strip past fallback notices & disclaimers
    content = re.sub(r'I searched your uploaded document.*?\n', '', content)
    content = re.sub(r'Related content was found, but the relevance score.*?\n', '', content)
    content = re.sub(r'I am specialized in mental-health.*?\n\n', '', content)
    return content.strip()


class AIOrchestrator:
    def __init__(self):
        self.system_prompt = SYSTEM_PROMPT

    async def process_chat_message(
        self,
        user_message: str,
        conversation_id: str,
        user_id: str,
        db: Session
    ) -> AsyncGenerator[str, None]:
        try:
            t_start = time.perf_counter()
            time_asked = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"\n[TIMING {time_asked}] 📥 USER ASKED QUESTION: '{user_message[:70]}...'", flush=True)
            print(f"📜 [SYSTEM PROMPT VERIFIED] Loaded SYSTEM_PROMPT.md ({len(self.system_prompt):,} characters | v1.1 Master System Prompt)", flush=True)

            # ── Step 0: Dual-Stage Clinical Safety & Crisis Override ─────────────
            from app.security.crisis_guard import crisis_guard
            crisis_res = crisis_guard.evaluate_prompt(user_message)
            if crisis_res.is_crisis and crisis_res.override_message:
                print(f"[ORCHESTRATOR] 🚨 CRISIS SAFETY OVERRIDE TRIGGERED for conversation '{conversation_id}'", flush=True)
                yield json.dumps({"type": "token", "text": crisis_res.override_message}) + "\n"
                yield json.dumps({"type": "done"}) + "\n"
                return

            # ── Step 1: Fetch conversation history ─────────────────────────
            past_messages = (
                db.query(Message)
                .filter(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
                .all()
            )

            # ── Step 2: Query Planner ──────────────────────────────────────
            t0 = time.perf_counter()
            plan: RetrievalPlan = query_planner.plan(user_message, past_messages, user_id, db)
            t_planner_ms = round((time.perf_counter() - t0) * 1000, 1)

            print(f"\n{'='*60}")
            print(f"[PLANNER] Intent: {plan.intent.upper()} | Scope: {plan.scope_category} | Complexity: {plan.complexity}")
            if plan.document_names:
                print(f"[PLANNER] Resolved Document Filters: {list(plan.document_names)}")
            if plan.rewritten_flag:
                print(f"[PLANNER] Rewritten Search Query: '{plan.rewritten_query}'")
            print(f"[PLANNER] Recall Target: {plan.recall_target} candidates | Temp: {plan.temperature}")
            print(f"{'='*60}")

            # Handle early safety alert
            if plan.is_crisis:
                yield json.dumps({"type": "status", "text": "Safety alert detected"}) + "\n"
                for token in (plan.crisis_message or "").split(" "):
                    yield json.dumps({"type": "token", "text": token + " "}) + "\n"
                yield json.dumps({"type": "done"}) + "\n"
                return

            # Handle out of scope
            if plan.scope_category == "OUT_OF_SCOPE" and plan.scope_message:
                yield json.dumps({"type": "status", "text": "Domain scope evaluation"}) + "\n"
                for token in plan.scope_message.split(" "):
                    yield json.dumps({"type": "token", "text": token + " "}) + "\n"
                yield json.dumps({"type": "done"}) + "\n"
                return

            # ── Step 3: RAG Retrieval (if search required) ───────────────────
            rag_result = RetrievalResult(success=False, context='')

            if plan.requires_search:
                doc_note = f" in {plan.document_names[0]}" if plan.document_names else ""
                yield json.dumps({"type": "status", "text": f"Searching knowledge base{doc_note}..."}) + "\n"

                try:
                    rag_result = retrieve(
                        query=user_message,
                        user_id=user_id,
                        db=db,
                        plan=plan,
                    )
                except Exception as e:
                    logger.error(f"RAG retrieval error: {e}")
                    print(f"[CHAT] RAG ERROR: {e}")
                    rag_result = RetrievalResult(
                        success=False, context='',
                        message="Knowledge base search failed. Answering from general knowledge."
                    )

                try:
                    db.rollback()
                except Exception:
                    pass

            # ── Step 3.5: Continuity Engine Memory Retrieval ────────────────
            continuity_context = ""
            if plan.requires_memory:
                conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
                conv_summary = conv.summary if conv else None

                cont_res: ContinuityResult = retrieve_continuity_context(
                    query=user_message,
                    user_id=user_id,
                    db=db,
                    conversation_summary=conv_summary,
                    top_k=3
                )
                if cont_res.formatted_context:
                    continuity_context = (
                        "\n\n" + "=" * 60 + "\n"
                        + "USER CONTINUITY & PAST MEMORY CONTEXT\n"
                        + "=" * 60 + "\n"
                        + cont_res.formatted_context
                        + "\n" + "=" * 60
                    )

            # ── Step 4: System Prompt & History Assembly ─────────────────────
            if rag_result.success and rag_result.context:
                system_content = (
                    self.system_prompt
                    + continuity_context
                    + "\n\n"
                    + "=" * 60 + "\n"
                    + "RETRIEVED DOCUMENT CONTEXT\n"
                    + "=" * 60 + "\n"
                    + "The following passages were retrieved from uploaded psychiatric documents.\n"
                    + "Base your answer on this content. Cite sources accurately.\n\n"
                    + rag_result.context
                    + "\n" + "=" * 60
                )
                score_pct = f"{rag_result.best_score:.0%}" if rag_result.best_score else "High"
                yield json.dumps({"type": "status", "text": f"Generating grounded response (Relevance: {score_pct})..."}) + "\n"
            else:
                fallback_disclaimer = (
                    "\n\n============================================================\n"
                    "KNOWLEDGE BASE RETRIEVAL NOTICE:\n"
                    "No relevant document sections were found in the uploaded knowledge base for this specific query.\n"
                    "You MUST begin your answer with this explicit single-line italicized disclaimer:\n"
                    "'*Notice: No matching sections were found in your uploaded documents. The following response is based on general knowledge:*'\n"
                    "============================================================"
                )
                system_content = self.system_prompt + continuity_context + fallback_disclaimer
                if rag_result.message:
                    yield json.dumps({"type": "status", "text": f"Notice: {rag_result.message} Answering from general knowledge..."}) + "\n"
                else:
                    yield json.dumps({"type": "status", "text": "Generating response..."}) + "\n"

            formatted_messages = [{"role": "system", "content": system_content}]

            # Append last 3 turns with Deep History Sanitization
            raw_history_len = 0
            sanitized_history_len = 0

            for msg in past_messages[-3:]:
                raw_history_len += len(msg.content)
                clean_content = _sanitize_history_message(msg.content)
                sanitized_history_len += len(clean_content)
                if clean_content:
                    formatted_messages.append({"role": msg.role, "content": clean_content})

            if crisis_res and crisis_res.category == "EDUCATIONAL_INQUIRY":
                academic_prompt = (
                    "[ACADEMIC & EPIDEMIOLOGICAL RESEARCH QUERY — DO NOT GENERATE PERSONAL INTERVENTION TEMPLATE]\n"
                    "The user is a clinical psychology student/researcher analyzing literature regarding adolescent suicide prevention statistics.\n"
                    f"Research Question: {user_message}\n\n"
                    "Instruction: Provide objective WHO/CDC research statistics, evidence-based prevention protocols, and epidemiological literature findings directly."
                )
                formatted_messages.append({"role": "user", "content": academic_prompt})
            else:
                formatted_messages.append({"role": "user", "content": user_message})

            total_prompt_chars = sum(len(m["content"]) for m in formatted_messages)
            approx_prompt_tokens = total_prompt_chars // 4

            # ── Dynamic max_tokens computation ───────────────────────────────
            remaining_budget = OPENROUTER_INPUT_LIMIT - approx_prompt_tokens
            dynamic_max_tokens = max(MIN_OUTPUT_TOKENS, min(remaining_budget, RESERVED_OUTPUT_TOKENS))
            print(f"[TOKEN] Prompt: ~{approx_prompt_tokens} tokens | Remaining budget: {remaining_budget} | max_tokens: {dynamic_max_tokens}", flush=True)

            # ── Step 5: Stream LLM response ──────────────────────────────────────────
            t_llm_start = time.perf_counter()
            full_response = ""
            stream_packet_count = 0
            ttft_ms = 0.0

            async for token in llm_router.stream_chat(
                formatted_messages,
                intent=plan.intent,
                temperature=plan.temperature,
                max_tokens=dynamic_max_tokens,
                prompt_tokens=approx_prompt_tokens,
            ):
                if stream_packet_count == 0:
                    ttft_ms = round((time.perf_counter() - t_llm_start) * 1000, 1)
                    time_ttft = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    print(f"[TIMING {time_ttft}] ⚡ FIRST TOKEN SENT TO USER SCREEN (TTFT: {ttft_ms}ms)", flush=True)

                full_response += token
                stream_packet_count += 1
                yield json.dumps({"type": "token", "text": token}) + "\n"

            # ── Step 6: Output Evaluator Validation ───────────────────────────
            eval_res = output_evaluator.evaluate(
                query=user_message,
                response_text=full_response,
                intent=plan.intent,
                used_rag=rag_result.success,
            )

            # ── Step 7: Telemetry & Decision Log ──────────────────────────────
            llm_duration_s = max(time.perf_counter() - t_llm_start, 0.001)
            approx_completion_tokens = len(full_response) // 4
            tokens_per_sec = round(approx_completion_tokens / llm_duration_s, 1)

            t_total_ms = round((time.perf_counter() - t_start) * 1000, 1)
            telem = rag_result.telemetry or {}

            time_done = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"[TIMING {time_done}] ✅ FULL AGENT RESPONSE COMPLETED (Total Elapsed: {t_total_ms/1000:.2f}s)", flush=True)

            print(f"\n[PROFILE] --------------------------------------------------")
            print(f"[PROFILE] Total Request Time: {t_total_ms}ms | TTFT: {ttft_ms}ms")
            print(f"[PROFILE] Planner: {t_planner_ms}ms | FTS: {telem.get('fts_ms', 0)}ms | Vector: {telem.get('vector_ms', 0)}ms | RRF: {telem.get('rrf_ms', 0)}ms | Rerank: {telem.get('rerank_ms', 0)}ms (Bypassed: {telem.get('rerank_bypassed', False)})")
            print(f"[PROFILE] Prompt Payload: {total_prompt_chars:,} chars (~{approx_prompt_tokens:,} tokens) across {len(formatted_messages)} messages")
            print(f"[PROFILE] History Sanitization: {raw_history_len:,} chars -> {sanitized_history_len:,} chars (Saved {max(raw_history_len - sanitized_history_len, 0):,} chars)")
            print(f"[PROFILE] Completion: {len(full_response):,} chars (~{approx_completion_tokens} tokens) | Stream Speed: {tokens_per_sec} tok/sec")
            print(f"[PROFILE] Evaluator Score: {eval_res.score:.2f} | Passed: {eval_res.passed}")
            print(f"[PROFILE] --------------------------------------------------\n")

            # ── Step 8: Save assistant message + citations ───────────────────
            citations_data = []
            if rag_result.success and rag_result.citations:
                citations_data = [
                    {
                        "document_name": c.document_name,
                        "chapter": c.chapter,
                        "section": c.section,
                        "page_number": c.page_number,
                        "page_range": c.page_range,
                        "document_id": c.document_id,
                        "is_global": c.is_global,
                    }
                    for c in rag_result.citations
                ]

            assistant_msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_response,
                metadata_info={
                    "rag_used": rag_result.success,
                    "rag_score": rag_result.best_score,
                    "citations": citations_data,
                    "eval_score": eval_res.score,
                }
            )
            db.add(assistant_msg)
            db.commit()

            # ── Step 9: Background Memory Consolidation & Summary Update ──────
            try:
                await consolidate_user_memories(user_id, user_message, full_response, conversation_id, db)
                await update_conversation_summary(conversation_id, db)
            except Exception as e:
                logger.error(f"Background memory consolidation trigger error: {e}")

            if citations_data:
                yield json.dumps({"type": "citations", "data": citations_data}) + "\n"

            yield json.dumps({"type": "done"}) + "\n"
        except Exception as e:
            logger.exception(f"Unhandled error in process_chat_message: {e}")
            err_msg = str(e).encode('ascii', errors='ignore').decode()
            yield json.dumps({"type": "token", "text": f"\n\n⚠️ An error occurred: {err_msg}"}) + "\n"
            yield json.dumps({"type": "done"}) + "\n"


orchestrator = AIOrchestrator()
