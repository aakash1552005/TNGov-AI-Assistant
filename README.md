# Tamil Nadu Government AI Scheme Assistant

Production-quality multilingual (English + Tamil) RAG-based assistant that helps citizens discover Tamil Nadu government welfare schemes. Every answer is grounded exclusively in official government documents with full source citations.

> ⚠️ **Disclaimer**: This is an AI assistant, not an official government source. Always verify information with the concerned department before acting.

## Tech Stack

| Layer      | Technology                                       |
| ---------- | ------------------------------------------------ |
| Frontend   | Next.js 15 · TypeScript · Tailwind CSS · Shadcn  |
| Backend    | FastAPI · Python 3.12 · Pydantic                 |
| Database   | PostgreSQL 16                                    |
| Vector DB  | ChromaDB _(Milestone 2)_                         |
| Embeddings | `intfloat/multilingual-e5-large` _(Milestone 2)_ |
| LLM        | GPT-4.1 via API _(Milestone 4)_                  |
| RAG        | LangChain + Hybrid Retrieval _(Milestone 2-3)_   |
| Eval       | RAGAS _(Milestone 7)_                            |
| Deployment | Docker Compose                                   |

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2
- [Git](https://git-scm.com/)

## Quick Start

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd tn-gov-ai-assistant

# 2. Copy environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY (required for Milestone 4+)

# 3. Build and start all services
docker compose up -d

# 4. Verify everything is running
# Backend:  http://localhost:8000/health
# Frontend: http://localhost:3000
```

## Available Commands

| Command           | Description                            |
| ----------------- | -------------------------------------- |
| `make setup`      | Copy .env.example and build images     |
| `make run`        | Start all services (detached)          |
| `make run-logs`   | Start all services with logs           |
| `make stop`       | Stop all services                      |
| `make stop-clean` | Stop services and remove volumes       |
| `make test`       | Run backend tests                      |
| `make lint`       | Run linters (Ruff + ESLint)            |
| `make format`     | Format code (Black + Ruff)             |
| `make ingest`     | Run ingestion pipeline _(Milestone 2)_ |
| `make evaluate`   | Run RAGAS evaluation _(Milestone 7)_   |

## Project Structure

```
tn-gov-ai-assistant/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI route handlers
│   │   ├── core/          # Configuration and settings
│   │   ├── db/            # Database engine and session
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── rag/           # RAG pipeline (retrieval + generation)
│   │   ├── services/      # Business logic layer
│   │   ├── prompts/       # LLM prompt templates
│   │   ├── utils/         # Shared utilities
│   │   └── main.py        # FastAPI app entry point
│   ├── ingestion/         # Document ingestion pipeline
│   ├── evaluation/        # RAGAS evaluation suite
│   ├── tests/             # Backend test suite
│   ├── chroma_db/         # ChromaDB storage (gitignored)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── app/               # Next.js App Router pages
│   ├── components/        # Reusable UI components
│   ├── hooks/             # Custom React hooks
│   ├── lib/               # Utilities and API client
│   ├── services/          # Backend communication layer
│   ├── Dockerfile
│   ├── package.json
│   └── tsconfig.json
├── data/
│   ├── raw_documents/     # Original PDFs/pages (manual collection)
│   ├── processed/         # Cleaned and chunked documents
│   └── metadata/          # Source tracking metadata
├── docker/                # Additional Docker configs
├── docs/                  # Architecture diagrams, API docs
├── .env.example           # Environment variable template
├── docker-compose.yml     # Docker Compose configuration
├── Makefile               # Common development commands
├── LICENSE                # MIT License
├── PROJECT_SPEC.md        # Full project specification
└── README.md              # This file
```

## Development Milestones

- [x] **Milestone 1**: Project scaffolding + Docker Compose + PostgreSQL
- [ ] **Milestone 2**: Ingestion pipeline + ChromaDB (vector-only retrieval)
- [ ] **Milestone 3**: BM25 + Reciprocal Rank Fusion (hybrid retrieval)
- [ ] **Milestone 4**: GPT-4.1 integration via `LLMClient` interface
- [ ] **Milestone 5**: FastAPI endpoints + error handling + security
- [ ] **Milestone 6**: Next.js chat UI
- [ ] **Milestone 7**: RAGAS evaluation + test suite
- [ ] **Milestone 8**: Deployment + documentation

## License

[MIT](LICENSE)