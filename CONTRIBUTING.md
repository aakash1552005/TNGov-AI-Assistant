# Developer & Contribution Guide
## Tamil Nadu Government AI Scheme Assistant

Thank you for contributing! This guide outlines setup, code style, testing, and contribution workflows.

---

## 1. Local Development Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/aakash1552005/TNGov-AI-Assistant.git
   cd TNGov-AI-Assistant
   ```

2. **Create Virtual Environment & Install Dependencies**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install ruff
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and set `GROQ_API_KEY`.

---

## 2. Running Unit & Integration Tests

Run the complete 46-test unit suite:

```bash
cd backend
python -m pytest tests/ -v
```

---

## 3. Code Style & Quality Standards

- **Formatting & Linting**: We use **Ruff** for linting and formatting.
- **Rules**: Run `ruff check backend/app` before submitting a Pull Request.
- **Frozen Files Directive**:
  - Do NOT modify `backend/app/services/generation_service.py`
  - Do NOT modify `backend/app/rag/retrieval_service.py`
  - Do NOT modify `backend/app/rag/llm_client.py`
  unless fixing an authorized production bug.

---

## 4. Running the Evaluation Suite

To run the complete quality evaluation pipeline:

```bash
cd backend
python -m evaluation.cli all
```

Outputs will be generated in `backend/evaluation/results/`.
