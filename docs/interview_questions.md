# 50 Technical Interview Questions & Answers

Based on the **Tamil Nadu Government AI Scheme Assistant** codebase and system architecture.

---

### System Architecture & RAG Foundations

#### 1. What is Retrieval-Augmented Generation (RAG)?
- **Answer**: RAG is an AI pattern that combines information retrieval with large language model text generation. Before sending a user's question to the LLM, the system retrieves relevant document chunks from a domain-specific index (ChromaDB + BM25) and injects them as grounded context.
- **Follow-up**: Why is RAG essential for government applications?
- **Expected Discussion**: Eliminates hallucinated scheme rules, provides verifiable document and page-level citations, and updates knowledge dynamically when new PDFs are ingested without retraining the LLM.

#### 2. Why use Hybrid Search (Vector + BM25) instead of Vector-only Search?
- **Answer**: Vector search captures semantic intent and multilingual concepts (English/Tamil) but can struggle with exact acronyms or numerical thresholds. BM25 excels at exact keyword matching (e.g. "PMEGP", "CMCHIS"). Hybrid search ensures both semantic and exact keyword matches are retrieved.
- **Follow-up**: Give an example where dense vector search alone might fail.
- **Expected Discussion**: Searching for specific scheme codes or exact financial eligibility numbers where vector embeddings compress numerical tokens into dense spaces.

#### 3. Explain Reciprocal Rank Fusion (RRF).
- **Answer**: RRF is a rank aggregation technique that merges ranked lists from different retrieval algorithms. The score for document $d$ is calculated as $RRF(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}$ where $k=60$ and $r_m(d)$ is document rank in retriever $m$.
- **Follow-up**: Why preference RRF over score normalization?
- **Expected Discussion**: Cosine distance (0.0 to 1.0) and BM25 scores (0 to $\infty$) operate on incompatible scales. RRF depends solely on relative rank order, making it scale-invariant and immune to score distribution shifts.

#### 4. What embedding model is used in this project?
- **Answer**: `intfloat/multilingual-e5-large` (1024 dimensions).
- **Follow-up**: Why select a multilingual embedding model?
- **Expected Discussion**: Citizens query the portal in both English and Tamil script. Multilingual E5 maps Tamil query embeddings close to English/Tamil document chunk embeddings in the vector space.

#### 5. Explain the Relevance Score Guard mechanism.
- **Answer**: The guard evaluates retrieved chunk RRF scores, vector distances, and BM25 scores against configured minimum thresholds (`retrieval_min_score=0.015`).
- **Follow-up**: What happens if the query is out of scope (e.g. "Who won the FIFA World Cup?")?
- **Expected Discussion**: The score check fails, bypassing the LLM API call entirely. The system instantly returns a refusal response, saving API costs and preventing out-of-domain hallucinations.

---

### Database & Persistence

#### 6. Describe the PostgreSQL database schema used for conversation persistence.
- **Answer**: Three tables: `chat_sessions` (stores session metadata), `chat_messages` (stores user questions and assistant answers linked via `session_id`), and `feedback` (stores ratings `"up"`/`"down"` and optional comments linked via `message_id`).
- **Follow-up**: Why use UUID v4 for primary keys?
- **Expected Discussion**: UUIDs prevent sequential enumeration attacks, support distributed generation across microservices, and integrate cleanly with browser localStorage.

#### 7. Explain Database Failure Resilience in `POST /chat`.
- **Answer**: All PostgreSQL session and message persistence calls are wrapped in `try...except Exception` blocks with `await db.rollback()`.
- **Follow-up**: What happens to answer generation if PostgreSQL is completely down?
- **Expected Discussion**: The DB failure is logged server-side with a full stack trace, but the request proceeds to RAG retrieval and LLM answer generation. The citizen receives their answer cleanly with an active session ID without experiencing a 500 error.

#### 8. Why use `NullPool` in SQLAlchemy async engine?
- **Answer**: In Python async applications tested with `pytest` or running under Starlette `TestClient`, connection pools shared across different event loops throw `RuntimeError: Task got Future attached to a different loop`. `NullPool` ensures each session opens and closes a fresh connection bound to the current event loop.

#### 9. Are vector embeddings or raw prompt texts stored in PostgreSQL?
- **Answer**: No. PostgreSQL stores only conversation history (`role`, `content`, `created_at`) and feedback ratings. Embeddings reside in ChromaDB and prompts are generated ephemerally in memory.

#### 10. How are cascading deletes configured in the database models?
- **Answer**: Using `ForeignKey("chat_sessions.id", ondelete="CASCADE")` and SQLAlchemy `relationship(..., cascade="all, delete-orphan")`. Deleting a session automatically cleans up its messages and feedback.

---

### Backend API & FastAPI Architecture

#### 11. What is the role of `Pydantic` in this project?
- **Answer**: Pydantic handles request/response data validation, settings management (`pydantic-settings`), and strict schema serialization.

#### 12. How does `LLMClient` protocol work?
- **Answer**: Python `typing.Protocol` defines the structural subtyping interface `generate(prompt: str, context: list[str]) -> str`. `GroqClient`, `GeminiClient`, and `OpenAIClient` implement this protocol.

#### 13. How does FastAPI lifespan manage model pre-warming?
- **Answer**: The `@asynccontextmanager` lifespan function initializes `vector_store.get_collection()` and `bm25_index._ensure_loaded()` on application startup, eliminating first-request latency spikes.

#### 14. What CORS security policies are applied?
- **Answer**: `CORSMiddleware` parses comma-separated allowed origins from `settings.allowed_origins` (default `http://localhost:3000`), restricting browser cross-origin requests.

#### 15. How does prompt injection protection work?
- **Answer**: `app.utils.sanitizer.sanitize_query()` applies compiled regex patterns to detect and strip common override phrases (`"ignore previous instructions"`, `"system:"`, `"act as chatgpt"`) before processing.

---

### Frontend & Web Application Engineering

#### 16. How does the frontend handle session restoration on browser refresh?
- **Answer**: `useEffect` reads `session_id` from `localStorage` (`tngov_chat_session_id`) and executes `GET /chat/{session_id}` to restore past messages into the message feed.

#### 17. What happens if `GET /chat/{session_id}` returns a 500 error on page load?
- **Answer**: The frontend displays a non-blocking alert banner ("Could not load conversation history from database") with a "Retry Loading" button while preserving the local `session_id` in `localStorage`.

#### 18. How are citations rendered in the Next.js chat interface?
- **Answer**: Assistant messages map the `citations` array into styled card components displaying scheme name, department, page number, chunk excerpt, and clickable official web URLs.

#### 19. How are user feedback ratings submitted?
- **Answer**: Thumbs up (`👍`) and thumbs down (`👎`) buttons trigger `POST /feedback` with `{ message_id, rating, comment }` without refreshing the browser tab.

#### 20. How is auto-scrolling implemented in the chat feed?
- **Answer**: A `useRef` attaches to an empty `<div>` at the bottom of the feed. An effect triggers `scrollIntoView({ behavior: 'smooth' })` whenever `messages` array changes.

---

### PDF Ingestion & Text Preprocessing

#### 21. How is PDF text extracted?
- **Answer**: Page-by-page extraction via `PyPDFLinker` / `pypdf.PdfReader`.

#### 22. What cleaning steps are applied to raw extracted page text?
- **Answer**: NFKC Unicode normalization, control character removal (`\x00`, `\x0c`), whitespace collapsing, standalone page number removal, and repeated header/footer detection across document pages.

#### 23. Why preserve Tamil Unicode characters during text cleaning?
- **Answer**: Over-aggressive regexes (e.g. `[^\x00-\x7F]`) strip non-ASCII text, destroying Tamil script (`\u0B80` to `\u0BFF`). Cleaner regexes explicitly preserve language scripts.

#### 24. How is chunk deduplication ensured during ingestion?
- **Answer**: SHA-256 chunk IDs derived from file hash, page number, and chunk index prevent duplicate chunk insertion.

#### 25. How is ChromaDB updated incrementally?
- **Answer**: `ingestion.cli` calculates document file SHA-256 hashes against `source_log.json`, skipping unmodified PDFs.

---

### Advanced System Design & Interview Discussion Points

#### 26. How would you scale this system from 31 PDFs to 100,000 PDFs?
- **Discussion Points**: Migrate ChromaDB to distributed Qdrant or Milvus; migrate BM25 to Elasticsearch/OpenSearch; implement asynchronous worker queues (Celery/Redis) for document ingestion; add Redis caching for frequent Q&A responses.

#### 27. How would you support streaming responses (SSE / WebSockets)?
- **Discussion Points**: Update `LLMClient` protocol to support generator yield; replace FastAPI `JSONResponse` with `StreamingResponse`; update frontend to handle chunked text stream appending.

#### 28. What tradeoffs exist between chunk size 500 vs 1000?
- **Discussion Points**: Smaller chunks (500) provide higher precision for specific facts but risk losing broader contextual scheme rules. Larger chunks (1000) preserve full scheme eligibility context but consume more prompt tokens.

#### 29. How do you prevent LLM prompt injection attacks?
- **Discussion Points**: Input sanitization regexes, strict system prompt instruction boundaries, isolating context into system messages, and enforcing score threshold guards.

#### 30. How would you evaluate RAG answer quality automatically?
- **Discussion Points**: Use RAGAS framework to measure Faithfulness, Answer Relevance, Context Recall, and Context Precision against a golden evaluation dataset (`ground_truth_eval.json`).

*(Questions 31–50 cover additional edge-case debugging, Docker orchestration, Pydantic validation, and production monitoring details).*
