# Directory & Codebase Structure

```text
TNGov-AI-Assistant/
├── .env                              # Environment variable configuration
├── .gitignore                        # Git exclusion rules
├── README.md                         # Production repository documentation
├── docker-compose.yml                # Multi-container orchestration specification
├── PROJECT_SPEC.md                   # Core project specification
├── data/                             # Document repository & metadata
│   ├── raw_documents/                # Official Tamil Nadu Government scheme PDFs (31 files)
│   └── metadata/
│       └── source_log.json           # Document registry with verified official portal URLs
├── docs/                             # Engineering documentation
│   ├── api.md                        # REST API reference
│   ├── architecture.md               # System architecture & sequence diagrams
│   ├── database.md                   # Database schema & ER diagram
│   ├── deployment.md                 # Container deployment guide
│   ├── project_structure.md          # Codebase layout
│   ├── retrieval.md                  # Hybrid retrieval & RRF documentation
│   └── testing.md                    # QA & test suite guide
├── backend/                          # FastAPI RAG Backend
│   ├── Dockerfile                    # Backend container definition
│   ├── pyproject.toml                # Dependencies & package configuration
│   ├── app/
│   │   ├── api/                      # REST API Routers
│   │   │   ├── chat.py               # POST /chat, GET /chat/{session_id}
│   │   │   └── feedback.py           # POST /feedback
│   │   ├── core/
│   │   │   └── config.py             # pydantic-settings configuration
│   │   ├── db/
│   │   │   ├── base.py               # SQLAlchemy Base
│   │   │   └── session.py            # AsyncSession factory with NullPool
│   │   ├── models/                   # SQLAlchemy ORM Models
│   │   │   ├── chat.py               # ChatSession and ChatMessage models
│   │   │   └── feedback.py           # Feedback model
│   │   ├── prompts/
│   │   │   └── system_prompt.py      # Grounded RAG system prompt
│   │   ├── rag/                      # Core RAG Retrieval & LLM Layer
│   │   │   ├── bm25_index.py         # BM25 sparse keyword index
│   │   │   ├── llm_client.py         # GroqClient, GeminiClient, OpenAIClient
│   │   │   ├── retrieval_models.py   # Dataclass models (Citation, Chunk, Metadata)
│   │   │   ├── retrieval_service.py  # Hybrid search & RRF ranking
│   │   │   └── vector_store.py       # ChromaDB vector store wrapper
│   │   ├── services/                 # Orchestration Services
│   │   │   ├── generation_service.py # RAG Q&A pipeline & scope guard
│   │   │   └── persistence_service.py# PostgreSQL persistence operations
│   │   └── main.py                   # FastAPI application entrypoint
│   ├── ingestion/                    # PDF Ingestion Pipeline
│   │   ├── cli.py                    # CLI commands (run, stats, clean)
│   │   ├── text_cleaner.py           # Unicode normalization & header/footer removal
│   │   ├── pdf_loader.py             # PyPDF text extractor
│   │   └── chunker.py                # Recursive character splitter
│   └── tests/                        # Backend Test Suite
│       ├── test_api.py               # End-to-end API integration tests
│       ├── test_chunker.py           # Chunking unit tests
│       ├── test_cleaner.py           # Preprocessing unit tests
│       ├── test_health.py            # Health check tests
│       └── test_retrieval.py         # Retrieval & Tamil query tests
└── frontend/                         # Next.js 16 Web Application
    ├── Dockerfile                    # Frontend container definition
    ├── package.json                  # Node.js dependencies
    └── app/
        ├── layout.tsx                # Global HTML root layout & fonts
        ├── page.tsx                  # Interactive Chat UI component
        └── globals.css               # Vanilla CSS design system & tokens
```
