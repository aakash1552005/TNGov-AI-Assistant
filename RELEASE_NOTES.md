# Release Notes — Version 1.0.0
## Tamil Nadu Government AI Scheme Assistant

**Release Date**: July 31, 2026  
**Status**: Production Release Candidate (v1.0.0)

---

### Overview

Version 1.0.0 marks the initial major production release of the **Tamil Nadu Government AI Scheme Assistant**, a multilingual Retrieval-Augmented Generation (RAG) system providing grounded answers for 31 Tamil Nadu welfare schemes.

---

### Key System Capabilities

- **Hybrid Search Engine**: ChromaDB dense vector search combined with Okapi BM25 sparse keyword matching via Reciprocal Rank Fusion (RRF).
- **Grounded Answer Generation**: Multi-turn prompt construction with strict citation enforcement (`[PDF Name, Page X]`).
- **Out-of-Scope Refusal Guardrails**: Automatic refusal (`llm_called = False`) for non-scheme queries.
- **Multi-Provider Architecture**: Dynamic switching between Groq (`llama-3.3-70b-versatile`), OpenAI (`gpt-4o-mini`), and Gemini (`gemini-2.0-flash`).
- **Production DevOps Packaging**: Docker, Docker Compose, GitHub Actions CI/CD pipeline, and healthcheck endpoints.
- **Evaluation & Benchmarking Suite**: Complete testing pipeline with Hit@K, MRR, latency percentile profiling, and RAGAS integration.

---

### Quality & Verification Metrics

- **Unit Test Coverage**: 46 / 46 passed ($100\%$ pass rate).
- **Retrieval Precision**: $\text{Hit}@1 = 93.8\%$, $\text{Hit}@3 = 100.0\%$, $\text{MRR} = 0.9583$.
- **Latency Performance**: Local CPU retrieval avg $\approx 275\text{ ms}$, E2E pipeline $P_{50} = 1.007\text{ s}$.
- **Frozen Production Files**: 0 lines diff on `generation_service.py`, `retrieval_service.py`, and `llm_client.py`.
