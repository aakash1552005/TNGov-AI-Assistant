.PHONY: setup run stop test lint format ingest evaluate clean

# ─── Setup ────────────────────────────────────────────────────
setup: ## Copy .env.example and build Docker images
	@if not exist .env copy .env.example .env
	docker compose build

# ─── Run ──────────────────────────────────────────────────────
run: ## Start all services (backend, frontend, postgres)
	docker compose up -d

run-logs: ## Start all services with logs attached
	docker compose up

# ─── Stop ─────────────────────────────────────────────────────
stop: ## Stop all services
	docker compose down

stop-clean: ## Stop all services and remove volumes
	docker compose down -v

# ─── Test ─────────────────────────────────────────────────────
test: ## Run backend tests
	docker compose exec backend pytest tests/ -v

test-frontend: ## Run frontend tests
	docker compose exec frontend npm test

# ─── Lint & Format ────────────────────────────────────────────
lint: ## Run linters (Ruff for Python, ESLint for frontend)
	docker compose exec backend ruff check app/
	docker compose exec frontend npm run lint

format: ## Format code (Black for Python)
	docker compose exec backend black app/
	docker compose exec backend ruff check --fix app/

format-check: ## Check formatting without modifying files
	docker compose exec backend black --check app/
	docker compose exec backend ruff check app/

# ─── Ingestion (Milestone 2) ──────────────────────────────────
ingest: ## Run document ingestion pipeline
	docker compose exec backend python -m ingestion.cli ingest

ingest-stats: ## Show ChromaDB collection statistics
	docker compose exec backend python -m ingestion.cli stats

ingest-clear: ## Clear ChromaDB collection
	docker compose exec backend python -m ingestion.cli clear

# ─── Evaluation (Milestone 7+) ───────────────────────────────
evaluate: ## Run RAGAS evaluation suite
	@echo "Evaluation pipeline not yet implemented (Milestone 7)"

# ─── Clean ────────────────────────────────────────────────────
clean: ## Remove generated files and caches
	docker compose down -v --rmi local
	@echo "Cleaned up Docker resources"

# ─── Help ─────────────────────────────────────────────────────
help: ## Show this help message
	@echo Available targets:
	@echo   setup        - Copy .env.example and build Docker images
	@echo   run          - Start all services in detached mode
	@echo   run-logs     - Start all services with logs attached
	@echo   stop         - Stop all services
	@echo   stop-clean   - Stop all services and remove volumes
	@echo   test         - Run backend tests
	@echo   test-frontend- Run frontend tests
	@echo   lint         - Run linters
	@echo   format       - Format code
	@echo   format-check - Check formatting without changes
	@echo   ingest       - Run ingestion pipeline (Milestone 2+)
	@echo   evaluate     - Run RAGAS evaluation (Milestone 7+)
	@echo   clean        - Remove generated files and caches
