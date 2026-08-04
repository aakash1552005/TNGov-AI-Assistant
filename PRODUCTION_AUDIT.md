# Comprehensive Production Audit & System Specification
**TN Gov AI Scheme Assistant**

This document details the system architecture, API specifications, dataset composition, deployment configuration, and verification protocols for the Tamil Nadu Government AI Assistant.

---

## 1. System Architecture

The application is built on a decoupled, modular Retrieval-Augmented Generation (RAG) pipeline designed to deliver grounded answers exclusively from official Tamil Nadu Government welfare scheme documents.

```
                    ┌───────────────────────────────┐
                    │      React/Next.js UI         │
                    └───────────────┬───────────────┘
                                    │ HTTP / HTTPS
                                    ▼
                    ┌───────────────────────────────┐
                    │      FastAPI Backend          │
                    └───────────────┬───────────────┘
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
┌───────────────────────┐                         ┌─────────────────────┐
│  Pre-LLM Topic Guard  │                         │ Hybrid Retrieval    │
│ (Model-independent)   │                         │ (ChromaDB + BM25)   │
└──────────┬────────────┘                         └──────────┬──────────┘
           │ Refusal                                         │
           ▼                                                 ▼
┌───────────────────────┐                         ┌─────────────────────┐
│  Structured Refusal   │                         │  RRF Fusion & Rank  │
│  Response             │                         └──────────┬──────────┘
└───────────────────────┘                                    │
                                                             ▼
                                                  ┌─────────────────────┐
                                                  │ Groq LLM Generation │
                                                  │ (Active Fallbacks)  │
                                                  └─────────────────────┘
```

---

## 2. Dataset Specification & Parity

The official repository contains **37 chunks** covering major welfare schemes:
- Kalaignar Magalir Urimai Thogai Scheme (KMUT)
- Moovalur Ramamirtham Ammiyar Higher Education Assurance Scheme (Pudhumai Penn)
- Chief Minister's Breakfast Scheme
- Tamil Nadu Social Security Pension Schemes (OAP / Destitute Widow Pension)
- Makkalai Thedi Maruthuvam Doorstep Healthcare Scheme
- Free Bus Travel for Women (Vidiyal Payanam Scheme)
- Chief Minister's Comprehensive Health Insurance Scheme (CMCHIS)
- Differently Abled Welfare Schemes & Social Security Welfare Board Schemes

---

## 3. Core API Endpoints

### Public Endpoints
- `POST /chat`: Submit query with optional `session_id`. Returns answer, citations, confidence level, and related schemes.
- `GET /chat/{session_id}`: Retrieve full message history for a conversation session.
- `POST /feedback`: Submit user rating (`up` | `down`) and optional comment.

### Admin & Audit Endpoints
- `GET /health`: Overall system health and active model metadata.
- `GET /admin/stats`: High-level vector store and BM25 chunk counts.
- `GET /admin/version`: Returns git commit hash, build timestamp, and active LLM configuration.
- `GET /admin/dataset`: Full document and chunk manifest.
- `GET /admin/feedback`: Aggregated user feedback metrics from PostgreSQL.

---

## 4. Verification Protocols & Test Suite

Execute the following commands to perform full automated verification:

1. **Unit & Integration Tests**:
   ```bash
   pytest backend/tests/ -v
   ```

2. **Benchmark Evaluation (Target: 8/8 100%)**:
   ```bash
   python backend/evaluation/benchmark_eval.py
   ```

3. **Production Verification Suite**:
   ```bash
   python backend/evaluation/production_verify.py --url https://backend-production-0a73.up.railway.app
   ```
