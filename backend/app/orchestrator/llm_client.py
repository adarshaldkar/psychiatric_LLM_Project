"""
Multi-Provider LLM Router — Phase 4 Intelligence Layer

Routing Strategy:
  SIMPLE queries (greeting, definition, fact_lookup, general):
    Primary:   Google Gemini (free, fast, Google AI Studio)
    Fallback1: Ollama       (local, free, offline)
    Fallback2: OpenRouter   (credits, last resort)

  COMPLEX queries (comparison, summary, broad):
    Primary:   Claude        (best reasoning, structured output)
    Fallback1: Google Gemini (free)
    Fallback2: Ollama        (local)

  LARGE PROMPT (prompt_tokens > 4500):
    Stage 1:   Ollama compresses RAG context to ~400 tokens
    Stage 2:   Claude generates final answer with compressed context
"""
import re
import json
import httpx
import logging
from typing import AsyncGenerator, List, Dict

from app.core.config import settings

logger = logging.getLogger(__name__)

SIMPLE_INTENTS = {"greeting", "definition", "fact_lookup", "general"}
COMPLEX_INTENTS = {"comparison", "summary", "broad"}
LARGE_PROMPT_THRESHOLD = 4500   # tokens


# ══════════════════════════════════════════════════════════════════════════════
# Token Sanitizer (shared by all providers)
# ══════════════════════════════════════════════════════════════════════════════
CONTROL_TOKEN_REGEX = re.compile(r'<\|(?:start_header_id|end_header_id|eot_id|python_tag|finetune_right_pad_id)\|.*?>|<\|.*?\|>')

def _sanitize_token(content: str) -> str:
    if not content:
        return ""
    if "<|" in content:
        content = CONTROL_TOKEN_REGEX.sub("", content)
    if "   " in content:
        content = re.sub(r" {3,}", " ", content)
    return content


# ══════════════════════════════════════════════════════════════════════════════
# Provider 1: Google Gemini (AI Studio) — Free tier
# ══════════════════════════════════════════════════════════════════════════════
class GeminiClient:
    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        self.model = "gemini-3.6-flash"
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:streamGenerateContent"

    def _messages_to_gemini(self, messages: List[Dict]) -> tuple:
        system_instruction = None
        contents = []
        for msg in messages:
            role, content = msg["role"], msg["content"]
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})
        return system_instruction, contents

    async def stream_chat(
        self,
        messages: List[Dict],
        temperature: float = 0.3,
        max_tokens: int = 650
    ) -> AsyncGenerator[str, None]:
        if not self.api_key or not self.api_key.startswith("AIza"):
            raise ValueError("GOOGLE_API_KEY must start with 'AIza'. Obtain a valid key from https://aistudio.google.com/app/apikey")

        system_instruction, contents = self._messages_to_gemini(messages)
        payload = {
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        url = f"{self.base_url}?key={self.api_key}&alt=sse"

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise RuntimeError(f"Gemini {response.status_code}: {error_text.decode()[:200]}")

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:].strip()
                        if not data or data == "[DONE]":
                            continue
                        try:
                            chunk = json.loads(data)
                            candidates = chunk.get("candidates", [])
                            if candidates:
                                for part in candidates[0].get("content", {}).get("parts", []):
                                    text = part.get("text", "")
                                    if text:
                                        yield _sanitize_token(text)
                        except (json.JSONDecodeError, KeyError):
                            continue


# ══════════════════════════════════════════════════════════════════════════════
# Provider 2: Claude (Anthropic) — Best quality
# ══════════════════════════════════════════════════════════════════════════════
class ClaudeClient:
    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        self.model = "claude-3-5-haiku-20241022"
        self.base_url = "https://api.anthropic.com/v1/messages"

    async def stream_chat(
        self,
        messages: List[Dict],
        temperature: float = 0.3,
        max_tokens: int = 650
    ) -> AsyncGenerator[str, None]:
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        system_content = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                chat_messages.append({"role": msg["role"], "content": msg["content"]})

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            "messages": chat_messages,
        }
        if system_content:
            payload["system"] = system_content

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", self.base_url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise RuntimeError(f"Claude {response.status_code}: {error_text.decode()[:200]}")

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:].strip()
                        if not data:
                            continue
                        try:
                            event = json.loads(data)
                            if event.get("type") == "content_block_delta":
                                text = event.get("delta", {}).get("text", "")
                                if text:
                                    yield _sanitize_token(text)
                        except (json.JSONDecodeError, KeyError):
                            continue


# ══════════════════════════════════════════════════════════════════════════════
# Provider 3: Ollama (Local) — Free, offline, no limits
# ══════════════════════════════════════════════════════════════════════════════
class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def stream_chat(
        self,
        messages: List[Dict],
        temperature: float = 0.3,
        max_tokens: int = 650
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise RuntimeError(f"Ollama {response.status_code}: {error_text.decode()[:200]}")

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        text = chunk.get("message", {}).get("content", "")
                        if text:
                            yield _sanitize_token(text)
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

    async def compress_context(self, context: str, query: str) -> str:
        """Compress large RAG context to ~400 words using local Ollama model."""
        prompt = (
            f"Extract only the key facts from the context relevant to this question.\n\n"
            f"QUESTION: {query}\n\n"
            f"CONTEXT:\n{context[:8000]}\n\n"
            f"OUTPUT: Bullet-point summary, max 400 words, facts only."
        )
        messages = [{"role": "user", "content": prompt}]
        compressed = ""
        async for token in self.stream_chat(messages, temperature=0.1, max_tokens=500):
            compressed += token
        return compressed.strip() or context[:2000]


# ══════════════════════════════════════════════════════════════════════════════
# Provider 4: OpenRouter — Backup
# ══════════════════════════════════════════════════════════════════════════════
class OpenRouterClient:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.default_model = settings.DEFAULT_MODEL
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    async def stream_chat(
        self,
        messages: List[Dict],
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 650
    ) -> AsyncGenerator[str, None]:
        chosen_model = model or self.default_model
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "MindCare AI Assistant",
            "Content-Type": "application/json"
        }

        for attempt, tokens in enumerate([max_tokens, max(150, max_tokens // 2)]):
            payload = {
                "model": chosen_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": tokens,
                "repetition_penalty": 1.15,
                "frequency_penalty": 0.3,
                "presence_penalty": 0.2,
                "stream": True
            }
            got_402 = False

            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", self.base_url, headers=headers, json=payload) as response:
                    if response.status_code == 402:
                        if attempt == 0:
                            print(f"[ROUTER] OpenRouter 402, retrying with {tokens // 2} tokens...")
                            got_402 = True
                            break
                        else:
                            raise RuntimeError("OpenRouter credit exhausted")

                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise RuntimeError(f"OpenRouter {response.status_code}: {error_text.decode()[:200]}")

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            line_data = line[6:].strip()
                            if line_data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(line_data)
                                content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content:
                                    yield _sanitize_token(content)
                            except json.JSONDecodeError:
                                continue

            if not got_402:
                return


# ══════════════════════════════════════════════════════════════════════════════
# Provider 5: OpenAI — (gpt-4o-mini / gpt-4o)
# ══════════════════════════════════════════════════════════════════════════════
class OpenAIClient:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = "gpt-4o-mini"
        self.base_url = "https://api.openai.com/v1/chat/completions"

    async def stream_chat(
        self,
        messages: List[Dict],
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 650
    ) -> AsyncGenerator[str, None]:
        if not self.api_key or not self.api_key.startswith("sk-"):
            raise ValueError("OPENAI_API_KEY must start with 'sk-'.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", self.base_url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise RuntimeError(f"OpenAI {response.status_code}: {error_text.decode()[:200]}")

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        line_data = line[6:].strip()
                        if line_data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(line_data)
                            content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                yield _sanitize_token(content)
                        except json.JSONDecodeError:
                            continue


# ══════════════════════════════════════════════════════════════════════════════
# Provider 6: Groq — Ultra High Speed (openai/gpt-oss-120b & qwen3.6)
# ══════════════════════════════════════════════════════════════════════════════
class GroqClient:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = "openai/gpt-oss-120b"
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    async def stream_chat(
        self,
        messages: List[Dict],
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 650
    ) -> AsyncGenerator[str, None]:
        if not self.api_key or not self.api_key.startswith("gsk_"):
            raise ValueError("GROQ_API_KEY must start with 'gsk_'.")

        models_to_try = [model] if model else [self.model, "openai/gpt-oss-20b", "qwen/qwen3.6-27b"]
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        last_err = None
        for m in models_to_try:
            try:
                payload = {
                    "model": m,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": True
                }
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream("POST", self.base_url, headers=headers, json=payload) as response:
                        if response.status_code != 200:
                            error_text = await response.aread()
                            last_err = f"Groq {m} ({response.status_code}): {error_text.decode()[:200]}"
                            continue

                        in_think = False
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                line_data = line[6:].strip()
                                if line_data == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(line_data)
                                    content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if content:
                                        if "<think>" in content:
                                            in_think = True
                                            continue
                                        if "</think>" in content:
                                            in_think = False
                                            continue
                                        if not in_think:
                                            yield _sanitize_token(content)
                                except json.JSONDecodeError:
                                    continue
                        return  # Successfully finished streaming
            except Exception as e:
                last_err = str(e)
                continue

        raise RuntimeError(f"All Groq models failed. Last error: {last_err}")


# ══════════════════════════════════════════════════════════════════════════════
# Provider 7: SambaNova Systems — High-Capacity Qwen2.5-72B & DeepSeek-R1
# ══════════════════════════════════════════════════════════════════════════════
class SambaNovaClient:
    def __init__(self):
        self.api_key = settings.SAMBANOVA_API_KEY
        self.model = "Meta-Llama-3.3-70B-Instruct"
        self.base_url = "https://api.sambanova.ai/v1/chat/completions"

    async def stream_chat(
        self,
        messages: List[Dict],
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 650
    ) -> AsyncGenerator[str, None]:
        if not self.api_key:
            raise ValueError("SAMBANOVA_API_KEY is missing.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", self.base_url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise RuntimeError(f"SambaNova {response.status_code}: {error_text.decode()[:200]}")

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        line_data = line[6:].strip()
                        if line_data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(line_data)
                            choices = chunk.get("choices", [])
                            if choices and len(choices) > 0:
                                content = choices[0].get("delta", {}).get("content", "")
                                if content:
                                    yield _sanitize_token(content)
                        except (json.JSONDecodeError, IndexError, AttributeError):
                            continue


# ══════════════════════════════════════════════════════════════════════════════
# LLM Router — Main Entry Point
# ══════════════════════════════════════════════════════════════════════════════
class LLMRouter:
    def __init__(self):
        self.groq = GroqClient()
        self.sambanova = SambaNovaClient()
        self.openai = OpenAIClient()
        self.gemini = GeminiClient()
        self.claude = ClaudeClient()
        self.ollama = OllamaClient()
        self.openrouter = OpenRouterClient()

    async def stream_chat(
        self,
        messages: List[Dict],
        intent: str = "general",
        temperature: float = 0.3,
        max_tokens: int = 650,
        prompt_tokens: int = 0,
    ) -> AsyncGenerator[str, None]:

        # Direct cloud LLM provider routing (Groq 128k context window support)

        # ── Provider chains by intent ──────────────────────────────────────
        if intent in SIMPLE_INTENTS:
            chain = [
                ("Groq",       self.groq.stream_chat),
                ("SambaNova",  self.sambanova.stream_chat),
                ("OpenAI",     self.openai.stream_chat),
                ("Claude",     self.claude.stream_chat),
                ("Gemini",     self.gemini.stream_chat),
                ("Ollama",     self._ollama_guarded),
                ("OpenRouter", self.openrouter.stream_chat),
            ]
        else:
            chain = [
                ("Groq",       self.groq.stream_chat),
                ("SambaNova",  self.sambanova.stream_chat),
                ("OpenAI",     self.openai.stream_chat),
                ("Claude",     self.claude.stream_chat),
                ("Gemini",     self.gemini.stream_chat),
                ("Ollama",     self._ollama_guarded),
                ("OpenRouter", self.openrouter.stream_chat),
            ]

        # ── Try each provider with fallback ───────────────────────────────
        for provider_name, stream_fn in chain:
            try:
                print(f"[ROUTER] Intent={intent} | Provider: {provider_name}", flush=True)
                async for token in stream_fn(messages, temperature=temperature, max_tokens=max_tokens):
                    yield token
                print(f"[ROUTER] {provider_name} [OK]", flush=True)
                return
            except Exception as e:
                # Clean ASCII log for Windows terminal
                err_msg = str(e).encode('ascii', errors='ignore').decode()
                print(f"[ROUTER] {provider_name} [FAILED] ({err_msg}) - trying next...", flush=True)
                continue

        yield "[All AI providers unavailable. Check API keys and try again.]"

    async def _ollama_guarded(
        self,
        messages: List[Dict],
        temperature: float = 0.3,
        max_tokens: int = 650
    ) -> AsyncGenerator[str, None]:
        if not await self.ollama.is_available():
            raise RuntimeError("Ollama not running")
        async for token in self.ollama.stream_chat(messages, temperature, max_tokens):
            yield token


# Singleton instances
llm_router = LLMRouter()
openrouter_client = llm_router.openrouter  # backward-compat alias
