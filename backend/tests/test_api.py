"""API unit tests for health check and POST /chat endpoint.

Tests:
1. GET /health returns 200 with component metadata
2. POST /chat valid in-scope question returns 200 with answer & citations
3. POST /chat out-of-scope question returns 200 with refusal response
4. POST /chat empty question returns HTTP 422
5. POST /chat oversized question returns HTTP 422
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_health_check_endpoint() -> None:
    """Test GET /health returns 200 and complete metadata structure."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert "app" in data
    assert "version" in data
    assert "chroma_db_loaded" in data
    assert "bm25_index_loaded" in data
    assert data["llm_provider"] == settings.llm_provider
    assert "llm_model" in data
    assert data["embedding_model"] == settings.embedding_model


def test_chat_valid_in_scope_question() -> None:
    """Test POST /chat with a valid in-scope question returns HTTP 200."""
    payload = {
        "question": "What are the eligibility criteria for the Chief Minister's Comprehensive Health Insurance Scheme?"
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "answer" in data
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 0
    assert "citations" in data
    assert isinstance(data["citations"], list)
    assert len(data["citations"]) > 0
    assert "retrieval_metadata" in data
    meta = data["retrieval_metadata"]
    assert "total_retrieved" in meta
    assert "llm_called" in meta


def test_chat_out_of_scope_question() -> None:
    """Test POST /chat with an out-of-scope question returns refusal response."""
    payload = {"question": "What is the capital of France?"}
    response = client.post("/chat", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "answer" in data
    assert "No relevant official information found" in data["answer"]
    assert data["retrieval_metadata"]["llm_called"] is False


def test_chat_empty_question() -> None:
    """Test POST /chat with empty question returns HTTP 422."""
    payload = {"question": "   "}
    response = client.post("/chat", json=payload)
    assert response.status_code == 422


def test_chat_oversized_question() -> None:
    """Test POST /chat with oversized question (> max_query_length) returns HTTP 422."""
    payload = {"question": "a" * (settings.max_query_length + 50)}
    response = client.post("/chat", json=payload)
    assert response.status_code == 422
