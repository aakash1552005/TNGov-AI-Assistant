# Build Prompt: Tamil Nadu Government AI Scheme Assistant (MVP)

## Project Overview

Build a multilingual (English + Tamil) RAG-based assistant that helps citizens discover Tamil Nadu government welfare schemes by asking natural-language questions. The assistant retrieves answers only from official government documents and always cites its source — it never answers from model memory alone.

**Portfolio goal**: demonstrate a production-quality RAG pipeline with retrieval evaluation, not a feature-sprawling demo. Depth over breadth.

---

## Scope for MVP (do NOT expand beyond this without explicit instruction)

- **2 departments only**: Social Welfare and Agriculture (Farmers Welfare)
- **10-15 schemes total**, sourced from official PDFs/pages under `tn.gov.in/schemes.php` (Department Wise section)
- **Text-based Q&A only** — English and Tamil text queries. No voice/speech, no OCR document upload, no eligibility questionnaire flow, no admin dashboard, no WhatsApp/Telegram bots, no Kubernetes, in this phase.
- Every answer must include: the answer text, the source document name, and a link/reference to the source.
- A visible disclaimer that this is not an official government source and citizens should verify with the relevant department.

Explicitly out of scope for MVP (future phases): voice I/O, OCR uploads, eligibility questionnaire engine, admin dashboard, additional departments, knowledge graph, multi-modal RAG, Kubernetes deployment.

---

## Tech Stack (fixed choices — do not substitute without asking)

- **Frontend**: Next.js 15 + TypeScript + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI (Python) + Pydantic
- **Database**: PostgreSQL (schemes metadata, chat history, feedback)
- **Vector DB**: ChromaDB (local/dev-friendly, no external service needed for MVP)
- **Embedding model**: `intfloat/multilingual-e5-large` (needed for Tamil + English semantic search)
- **LLM**: GPT-4.1 via API. Rationale: for this portfolio project, the differentiator is the RAG pipeline (retrieval quality, chunking, embeddings, evaluation, architecture) — not the LLM. GPT-4.1 gives strong multilingual reasoning, reliable citation formatting, fewer hallucinations, and simpler deployment, letting focus stay on retrieval/eval work. Build the LLM call behind a thin interface/abstraction (not hardcoded inline) so it can be swapped for a self-hosted Llama 3.1 8B in a later phase without touching the rest of the architecture.
- **RAG framework**: LangChain
- **Retriever**: Hybrid retrieval — ChromaDB vector search + BM25 keyword search, combined via Reciprocal Rank Fusion. Rationale: government documents contain exact scheme names, GO numbers, department names, and legal terminology that keyword search handles better, while vector search improves natural-language queries. Pure vector search alone is not sufficient here.
- **Retrieval config**: top-k = 5 retrieved, max 4 chunks passed into context, LLM temperature = 0 for deterministic, grounded answers.
- **Translation (if needed for query normalization)**: IndicTrans2
- **Deployment**: Docker Compose locally → Render or Railway for hosting; Vercel for frontend
- **Eval**: RAGAS for retrieval/answer quality scoring — build this in from week 1, not as an afterthought

**Version pinning**:
```
Python 3.12
Node.js 22 LTS
FastAPI >=0.115
LangChain >=0.3
ChromaDB >=0.5
PostgreSQL 16
Docker Compose v2
```

---

## Project Folder Structure

```
tn-gov-ai-assistant/

backend/
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── rag/
│   ├── services/
│   ├── prompts/
│   ├── utils/
│   └── main.py
├── ingestion/
├── evaluation/
├── tests/
├── chroma_db/
└── requirements.txt

frontend/
├── app/
├── components/
├── hooks/
├── lib/
├── services/
└── package.json

data/
├── raw_documents/
├── processed/
└── metadata/

docker/
docs/
```

---

## Data Pipeline

```
Manually collected PDFs/pages (Social Welfare + Agriculture schemes)
  → source metadata log (scheme name, dept, source URL, date fetched, doc type)
  → text extraction / cleaning
  → chunking (with metadata attached per chunk)
  → embeddings (multilingual-e5-large) + BM25 index
  → ChromaDB (vector) + BM25 index (keyword)
  → hybrid retriever (vector + BM25, fused via Reciprocal Rank Fusion)
  → LLM (with strict "answer only from retrieved context, cite source" system prompt)
  → answer + source citation returned to user
```

**Important**: `tn.gov.in` disallows automated scraping (robots.txt). Documents must be collected manually for this MVP and logged in a source-tracking sheet (scheme name, department, source URL, date fetched, doc type). Do not write a scraper that ignores robots.txt.

### Chunking Strategy

- Chunk size: 600–800 tokens
- Overlap: 100–150 tokens
- Splitter: `RecursiveCharacterTextSplitter` (LangChain)

### Chunk Metadata Requirements

Every chunk stored in ChromaDB must carry the following metadata fields, so that citations remain traceable and precise:

- `scheme_name`
- `department`
- `document_name`
- `page_number`
- `source_url`
- `language`
- `last_updated`

Citations returned to the user should be built from this metadata (e.g., scheme name + document name + page number + source URL), not just a generic "source" label.

---

## Database Schema (MVP)

**schemes**
- scheme_id, scheme_name, department, eligibility_text, benefits, income_limit, age_limit, gender, required_documents, application_link, district, last_updated, source_url

**users**
- user_id, name (optional), language_pref, district (optional)

**chat_history**
- id, user_id (optional/anonymous ok), question, answer, source_cited, timestamp

**feedback**
- id, chat_id, helpful (bool), rating, comment

---

## Core Features (in build order)

1. Ingestion pipeline: load manually-collected PDFs → clean → chunk (RecursiveCharacterTextSplitter, 600–800 tokens, 100–150 overlap) → embed → store in ChromaDB, with full metadata (scheme_name, department, document_name, page_number, source_url, language, last_updated) attached to every chunk. Also build a BM25 keyword index over the same chunks.
2. Retrieval + generation: FastAPI endpoint that takes a question (English or Tamil), retrieves top-k chunks via hybrid retrieval (vector + BM25, fused with Reciprocal Rank Fusion), generates an answer strictly grounded in retrieved context, and returns answer + citations (built from chunk metadata: scheme name, document, page, source URL). Refuse to answer if no relevant context is retrieved — do not hallucinate a scheme. Wrap the GPT-4.1 call behind this interface so the model backend can be swapped later without changing the retrieval or API layers:

```python
class LLMClient(Protocol):
    def generate(self, prompt: str, context: list[str]) -> str:
        ...

# Phase 1: OpenAIClient(LLMClient)
# Phase 2 (future): LlamaClient(LLMClient) — no other code changes needed
```
3. Chat UI: simple Next.js chat interface, language toggle (English/Tamil), displays source citation under each answer.
4. Eval pipeline: RAGAS-based scoring on a hand-built set of 20-30 test questions with known-correct answers/sources. Track faithfulness and context relevance.
5. Chat history + feedback logging to Postgres.
6. Dockerize frontend + backend + Postgres for local dev; deploy to Render/Railway + Vercel.

---

## System Prompt Requirements (for the RAG generation step)

The system prompt given to GPT-4.1 must enforce, non-negotiably:
- Answer only from retrieved context — never from general model knowledge.
- Never infer or guess missing facts (e.g., don't assume an income limit that wasn't retrieved).
- Never fabricate eligibility criteria.
- Never fabricate benefits or amounts.
- Cite every factual statement with its source document/scheme.
- If retrieved evidence is insufficient to answer confidently, refuse politely and say so — do not fill gaps.

---

## API Structure

- `POST /chat` — submit a question, returns answer + citations
- `POST /feedback` — submit helpful/rating/comment for a chat response
- `GET /history` — retrieve chat history (per user/session)
- `POST /evaluate` — trigger/run the RAGAS evaluation suite against the test question set

---

## Error Handling

Fail gracefully — this is a citizen-facing service, not a demo that can crash on bad input.

- OpenAI API failure → return `{"status": "error", "message": "Unable to generate a response at the moment."}`, do not crash the request.
- ChromaDB unavailable → return HTTP 503, not a stack trace.
- Postgres unavailable → retry with backoff before failing.
- Retrieval returns nothing relevant → return a clear "No relevant official information found." message, not a fabricated answer.

## Security

- Validate and sanitize all input; enforce a maximum query length.
- Rate limiting on `/chat` and other public endpoints.
- Basic prompt injection protection — the system prompt must not be overridable by user input, and retrieved document content should not be treated as instructions.
- Escape/sanitize any HTML rendered in the frontend.
- API keys and secrets only via environment variables — never hardcoded, never logged, never committed to the repo.

---

## Testing

- Unit tests for chunking, retrieval, and API request/response handling
- Integration tests covering the full ingest → retrieve → generate → cite flow
- RAG evaluation tests via RAGAS on the 20-30 question test set (see Success Metrics below)

---

## Environment Variables

```
OPENAI_API_KEY=
DATABASE_URL=
CHROMA_DB_PATH=
MODEL_NAME=gpt-4.1
EMBEDDING_MODEL=intfloat/multilingual-e5-large
```

---

## Logging

Log for every query, to support debugging and later analysis:
- Question asked
- Retrieved chunks (and their source metadata)
- Similarity/relevance scores
- Final LLM response
- End-to-end latency
- Any errors

---

## Success Metrics (Target — not just "it works")

- Faithfulness > 0.90 (RAGAS)
- Context Precision > 0.85 (RAGAS)
- Context Recall > 0.85 (RAGAS)
- Average response time < 3 seconds
- Citation coverage = 100% (every factual claim in an answer has a cited source)

---

## Acceptance Criteria — MVP is complete when

- All 10-15 official schemes (Social Welfare + Agriculture) are ingested with full metadata.
- English and Tamil queries both return grounded, cited answers.
- Every answer includes at least one citation.
- Unsupported/out-of-scope questions are politely refused, not guessed at.
- Docker Compose starts the full stack (frontend, backend, Postgres, ChromaDB) successfully from a clean clone.
- RAGAS metrics meet or exceed the targets defined in Success Metrics.
- README allows another developer to set up and run the project from scratch, with no undocumented steps.

---

## Deliverables

- Source code (public repo)
- README with setup instructions
- `.env.example` (so anyone cloning the repo can set up without guessing required variables)
- `docker-compose.yml`
- Makefile (common commands: setup, run, test, ingest, evaluate)
- Architecture diagram
- API documentation
- Evaluation report with RAGAS results
- Deployment guide

---

## Repository Standards

- Clean Architecture principles (clear separation between ingestion, retrieval, API, and presentation layers)
- SOLID principles
- Type hints throughout (Python) and TypeScript strict mode (frontend)
- Docstrings on all public functions/classes
- Black formatter + Ruff linter for Python
- Conventional Commits for git history

---

## Non-negotiable behavioral rules for the assistant itself

- Never answer from LLM general knowledge — only from retrieved government documents.
- Always cite the source document/scheme for every factual claim.
- If retrieval returns nothing relevant, say so clearly instead of guessing.
- Always show the disclaimer: this is an AI assistant, not an official government source; verify with the concerned department before acting.

---

## Explicit non-goals reminder for the coding agent

Do not add speech/voice, OCR, eligibility questionnaires, admin dashboards, additional departments, or Kubernetes manifests unless the user explicitly asks in a later phase. If a request seems to expand scope, flag it and ask for confirmation before building it.

---

## How to Feed This to the Coding Agent

Do not ask for the entire project in one shot — break it into milestones and review each before moving on:

1. Project scaffolding + Docker Compose + PostgreSQL
2. Ingestion pipeline + ChromaDB (vector-only first — validate retrieval on the real 10-15 schemes before adding BM25/hybrid fusion)
3. Add BM25 + Reciprocal Rank Fusion once vector-only retrieval is confirmed working
4. GPT-4.1 integration via the `LLMClient` interface, with system prompt grounding rules
5. FastAPI endpoints (`/chat`, `/feedback`, `/history`, `/evaluate`) + error handling + security
6. Next.js chat UI
7. RAGAS evaluation + test suite
8. Deployment + documentation

Smaller milestones mean smaller review cycles and much easier debugging than one massive generation request.

---

## License

MIT License (or Apache 2.0) — pick one and include the LICENSE file in the repo root so it's immediately usable/forkable by others.

---

## Looking Ahead: Version 2 (not part of MVP)

Because ingestion, retrieval, LLM, and presentation are kept as separate layers in this architecture, the following can be added later without a redesign:

- Additional Tamil Nadu government departments
- Eligibility recommendation engine
- Voice input/output (Tamil and English)
- OCR for scanned government documents
- Self-hosted Llama 3.1/3.3 in place of GPT-4.1 (via the existing `LLMClient` interface)
- Mobile app
- Analytics dashboard

None of this belongs in the MVP build — listed here only so the coding agent understands why the architecture is layered the way it is.