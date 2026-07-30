# 🧠 MindCare AI — Specialized Psychiatric Knowledge Platform

MindCare AI is a full-stack, clinical-grade **AI-powered Psychiatric and Mental Health Knowledge Assistant**. It is built specifically to assist medical professionals, clinicians, and researchers in retrieving, comparing, and summarizing mental health guidelines, clinical literature, and uploaded documents with absolute precision and zero-hallucination guardrails.

Unlike general-purpose chatbots, MindCare AI coordinates specialized runtime sub-systems—**Query Planner, Retrieval Engine, and Prompt Orchestrator**—working together to guarantee clinically safe, factually grounded answers.

---

## 📌 Table of Contents
1. [MindCare AI vs Generic Chatbots](#-mindcare-ai-vs-generic-chatbots)
2. [How It Works (Runtime Architecture)](#-how-it-works-runtime-architecture)
3. [Core Features](#-core-features)
4. [Technology Stack](#-technology-stack)
5. [Database Schema](#-database-schema)
6. [Local Setup & Installation](#-local-setup--installation)
7. [Clinical Safety & Guardrails](#-clinical-safety--guardrails)
8. [Frequently Asked Questions (FAQ)](#-frequently-asked-questions-faq)

---

## 📊 MindCare AI vs Generic Chatbots

| Capability | Generic Chatbots / Simple RAG | MindCare AI |
| :--- | :---: | :---: |
| **Domain Scope Lock** | ❌ Swallows general prompts | ✅ Underlined clinical scope guard |
| **Interactive Source Citations** | ❌ Arbitrary text outputs | ✅ Page-specific, immutable source cards |
| **Dual-Stage Crisis Safety** | ❌ Generic refusal or standard banner | ✅ Empathic crisis overrides / Academic bypass |
| **Multi-Provider Resilience** | ❌ Single API dependence | ✅ Automatic failover (Cloud API ➔ Local LLM) |
| **Context Query Planning** | ❌ Static raw input sending | ✅ Anaphora query rewriting & multi-query splitting |
| **Dynamic Token Allocation** | ❌ Static prompt chunk count | ✅ Token-based context budgets per intent |
| **Cross-Session Memory Graph** | ❌ Context-blind session history | ✅ Long-term vector memory consolidation |
| **Local Offline Voice Capture** | ❌ Third-party cloud transcription | ✅ Local `faster-whisper` STT model |

---

## 🏛️ How It Works (Runtime Architecture)

Every user query flows through a modular, stage-by-stage profiling pipeline to ensure clinical context and prompt safety:

```
User Query + History
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. QUERY PLANNER                                            │
│ • Scope check: psychiatric intent vs out-of-scope block     │
│ • Anaphora Query Rewriting ("its treatment" ➔ MDD treatment)│
│ • Precision vs. Recall classification (k-candidate rating)  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. RETRIEVAL ENGINE                                         │
│ • Hybrid Search (Vector + Full-Text Search RRF)            │
│ • Calibrated Conditional Reranking (Configurable Threshold)│
│ • Strict Token-Based Context Budgeting (not chunk count)    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. PROMPT ORCHESTRATOR                                      │
│ • Deep History Sanitization (Scrub past RAG & disclaimers)  │
│ • Adaptive LLM Parameter Tuning (temperature: 0.1–0.5)      │
│ • Streaming SSE Response Generation via LLM Router          │
└─────────────────────────────────────────────────────────────┘
```

### 🧩 1. The Query Planner
The **Query Planner** classifies user intent and transforms the query before executing search queries:
*   **Anaphora & Co-reference Resolution**: Rewrites follow-up questions to restore missing subjects. For example, if a user asks *"What are the symptoms of Major Depression?"* and follows up with *"What about its treatment?"*, the Query Planner rewrites the latter to *"What are the treatments for Major Depressive Disorder?"* to retrieve the correct database vectors.
*   **Precision vs. Recall Tuning**: Dynamically adjusts the retrieval candidate pool size:
    *   *High-Precision Queries* (*"What is the starting dose of Escitalopram?"*) target a tight pool ($k=10$).
    *   *High-Recall Queries* (*"Compare exposure-based therapy options across clinical books"*) target a broad candidate pool ($k=35$) with multi-step sub-query splitting.

### ⚡ 2. The Retrieval Engine
The **Retrieval Engine** manages candidate search and relevance filtering:
*   **Hybrid Search & Reciprocal Rank Fusion (RRF)**: Merges semantic dense embeddings (vector cosine similarity) with lexical keyword matching (Full-Text Search) for optimal coverage.
*   **Calibrated Conditional Reranking**: Uses a configurable short-circuit threshold. If a bi-encoder similarity score is above `0.90`, the reranker is bypassed to save ~45ms of CPU latency; otherwise, the candidate set is evaluated by a Cross-Encoder model.
*   **Token-Based Context Budgeting**: Controls prompt size by counting tokens, not arbitrary chunk numbers. Simple intents receive a tight 800-token context window; comparative intents are allocated up to 2,500 context tokens.

### 🎨 3. The Prompt Orchestrator
The **Prompt Orchestrator** manages history length, prompt construction, and server-sent events:
*   **Deep History Sanitization**: Automatically scrubs past retrieved document contexts and repetitive disclaimers from the session log. This reduces prompt payload sizes from **57,000 characters ➔ ~10,000 characters** for fast token generation.
*   **SSE Token Stream**: Outputs tokens under a unified JSON stream format (`{"type": "token", "text": "..."}`) to prevent client-side parsing hangs.

---

## 🌟 Core Features

*   **🏥 Dual-Stage Safety Override**: Directs crisis inputs (*"I feel hopeless and want to end my life"*) immediately to a deterministic **988 Lifeline** banner. Research inquiries (*"I am writing a paper about suicide prevention statistics"*) bypass emergency overrides to deliver empirical CDC/WHO statistics.
*   **🛡️ Injection Guard (6-Attack Taxonomy)**: Screens inputs before the LLM call to defend against Jailbreaks, System Prompt Leaks, Persona Hijacking, Instruction Overrides, Control Sequences, and Context Distractions.
*   **🧠 Multi-Level Memory**: Consolidates short-term session turns with long-term vector graph database memories. Users retain full control and can view or delete memories in the UI.
*   **🔌 Model Context Protocol (MCP)**: Integrates external search tools (like Tavily) and local document search servers using standardized tool definitions.
*   **🎙️ Local Whisper Speech-to-Text**: Captures and transcribes microphone input locally on the server using `faster-whisper` for clinical data privacy.
*   **🎨 Dynamic Markdown Layouts**: Renders glowing horizontal section dividers (`---`), structured header lines, and active capability badges (`📄 Document RAG`, `🌐 Web Search`, `🔌 MCP Tool`, `🧠 Memory Recall`) so responses remain clean and organized.
*   **🗃️ Conversation Management**: Features list pinning, archiving (accessible through a user profile drawer), sharing, and inline title renaming.

---

## 💻 Technology Stack

*   **Frontend**: React (Vite), Zustand state store, `react-markdown` + `remark-gfm` formatting, Lucide icons.
*   **Backend**: Python 3.11+, FastAPI web framework, `sentence-transformers` embeddings, Cross-Encoder rerankers, PyMuPDF, PaddleOCR, `faster-whisper` local model.
*   **Database**: PostgreSQL / SQLite + pgvector extension for high-performance approximate nearest neighbor (HNSW) cosine similarity search.

---

## 🗄️ Database Schema

```sql
-- conversations table representing chat threads
CREATE TABLE conversations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW(),
    summary     TEXT,
    is_archived BOOLEAN DEFAULT FALSE
);

-- document_chunks table with pgvector support
CREATE TABLE document_chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content     TEXT NOT NULL,
    page_number INTEGER,
    section     VARCHAR,
    embedding   vector(1536), -- pgvector vector column
    metadata    JSONB
);
CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);
```

---

## ⚙️ Local Setup & Installation

> [!NOTE]
> To preserve clinical data privacy, automated test suites and evaluation benchmark configurations are maintained in your local environment and excluded from public version control.

### 1. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a local `.env` file from the repository configuration settings:
   ```env
   DATABASE_URL=postgresql://user:pass@localhost:5432/mindcare
   OPENROUTER_API_KEY=your-openrouter-key
   TAVILY_API_KEY=your-tavily-search-key
   ```
5. Seed the database with psychiatric reference books and launch:
   ```bash
   python seed_books.py
   python run.py
   ```

### 2. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
4. Access the web interface at `http://localhost:3000`.

---

## 🏥 Clinical Safety & Guardrails

To prevent medical misinformation, MindCare AI enforces a strict multi-layer defense strategy:
*   **Immutable Metadata Rule**: Prompts prevent rewrite or alteration of source URLs, DOIs, and titles.
*   **LLM Provider Uptime Fallback**: In the event of cloud rate limits (Groq/OpenAI 429), the LLM Router automatically cascades traffic down to local Ollama instances.
*   **Supportive Non-Diagnostic Tone**: Configured with a low LLM temperature (`0.1`) to ensure answers are strictly grounded in clinical evidence rather than diagnostic speculation.

---

## 💬 Frequently Asked Questions (FAQ)

#### How is patient data and conversation history kept secure?
All conversation logs and uploaded documents are bound to your authenticated user ID. They are stored locally on your PostgreSQL database and protected by strict JWT authorization layers.

#### How does the speech-to-text transcribe voice notes locally?
MindCare AI integrates the `faster-whisper` model directly on the server host. Audio files recorded by the browser's `MediaRecorder` API are sent to the local Whisper instance for CPU/GPU transcription, preventing patient voice leaks to external services.

#### What happens if the primary LLM API key hits a rate limit?
The backend router automatically monitors connection status codes. If a cloud API provider returns a `429 Too Many Requests` or `402 Insufficient Balance`, the engine redirects the prompt to a secondary provider or your local Ollama instance without terminating the chat.
