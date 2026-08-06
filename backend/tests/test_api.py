"""API unit tests for health check, POST /chat, GET /chat/{session_id}, and POST /feedback endpoints.

Tests:
1. GET /health returns 200 with component metadata
2. POST /chat valid in-scope question returns 200 with answer & citations
3. POST /chat out-of-scope question returns 200 with refusal response
4. POST /chat empty question returns HTTP 422
5. POST /chat oversized question returns HTTP 422
6. POST /chat session creation and continuation
7. GET /chat/{session_id} conversation retrieval
8. POST /feedback rating submission
9. GET /chat/{session_id} with invalid UUID format -> 422
10. GET /chat/{session_id} with non-existent session UUID -> 404
11. Persistence DB failure does NOT break /chat generation
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

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
    assert "session_id" in data
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
    assert "This assistant only answers officially indexed" in data["answer"]
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


def test_chat_session_lifecycle_and_history() -> None:
    """Test session creation, continuation, and history retrieval."""
    # 1. First question - create session
    req1 = {"question": "What is the Chief Minister's Health Insurance Scheme?"}
    res1 = client.post("/chat", json=req1)
    assert res1.status_code == 200
    data1 = res1.json()

    session_id = data1["session_id"]
    msg_id1 = data1.get("message_id")
    assert session_id is not None

    # 2. Second question - continue session
    req2 = {
        "question": "What are the benefits under PMEGP?",
        "session_id": session_id,
    }
    res2 = client.post("/chat", json=req2)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["session_id"] == session_id

    # 3. Retrieve conversation history
    res3 = client.get(f"/chat/{session_id}")
    assert res3.status_code == 200
    history = res3.json()

    assert history["session_id"] == session_id
    assert "messages" in history
    messages = history["messages"]
    assert len(messages) >= 4  # 2 user questions + 2 assistant answers

    # 4. Submit feedback for the assistant message
    if msg_id1:
        feedback_req = {
            "message_id": msg_id1,
            "rating": "up",
            "comment": "Very helpful information!",
        }
        res_fb = client.post("/feedback", json=feedback_req)
        assert res_fb.status_code == 200
        assert res_fb.json()["status"] == "success"


def test_chat_history_invalid_and_nonexistent_session() -> None:
    """Test GET /chat/{session_id} with invalid format or non-existent session."""
    # Invalid UUID string -> 422
    res_invalid = client.get("/chat/not-a-valid-uuid")
    assert res_invalid.status_code == 422

    # Non-existent UUID -> 404
    random_uuid = str(uuid.uuid4())
    res_nonexistent = client.get(f"/chat/{random_uuid}")
    assert res_nonexistent.status_code == 404


def test_persistence_failure_resilience() -> None:
    """Test that database failures do NOT prevent answer generation in POST /chat."""
    with patch(
        "app.services.persistence_service.save_user_message",
        side_effect=RuntimeError("Simulated Database Error"),
    ):
        payload = {
            "question": "What is PMEGP?",
        }
        response = client.post("/chat", json=payload)
        # Endpoint should succeed despite DB exception
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0
