# REST API Documentation

Base URL: `http://localhost:8000`

All request and response bodies use standard JSON with UTF-8 encoding.

---

## Endpoints

### 1. Health Check
Returns the operational status of system components, active LLM provider, and vector database state.

- **Method**: `GET`
- **Path**: `/health`
- **Authentication**: None

#### Response (HTTP 200 OK)
```json
{
  "status": "healthy",
  "app": "TN Gov AI Scheme Assistant",
  "version": "0.1.0",
  "chroma_db_loaded": true,
  "bm25_index_loaded": true,
  "llm_provider": "groq",
  "llm_model": "llama-3.3-70b-versatile",
  "embedding_model": "intfloat/multilingual-e5-large"
}
```

---

### 2. Chat Q&A Endpoint
Executes hybrid retrieval, relevance score filtering, and LLM answer generation. Automatically creates or updates conversation sessions in PostgreSQL.

- **Method**: `POST`
- **Path**: `/chat`
- **Headers**: `Content-Type: application/json`

#### Request Body
```json
{
  "question": "What are the eligibility criteria for the Chief Minister's Comprehensive Health Insurance Scheme?",
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```
*`session_id` is optional. If omitted, a new UUID session is initialized.*

#### Response (HTTP 200 OK)
```json
{
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "message_id": "7b9e2a14-8842-470a-a921-6571fa0c2d3b",
  "answer": "The eligibility criteria for the Chief Minister's Comprehensive Health Insurance Scheme are...",
  "citations": [
    {
      "scheme_name": "Chief Minister's Comprehensive Health Insurance Scheme",
      "department": "Social Security",
      "document_name": "chief_ministers_comprehensive_health_insurance_scheme.pdf",
      "page_number": 1,
      "source_url": "https://cmchistn.com",
      "excerpt": "69. CHIEF MINISTER’S COMPREHENSIVE HEALTH INSURANCE SCHEME..."
    }
  ],
  "retrieval_metadata": {
    "total_retrieved": 4,
    "top_rrf_score": 0.03252247488101534,
    "vector_results_count": 3,
    "bm25_results_count": 2,
    "llm_called": true
  }
}
```

#### Error Responses
- `HTTP 422 Unprocessable Entity`: Question empty or exceeds `settings.max_query_length` (500 chars).
  ```json
  {
    "detail": "Question exceeds maximum query length of 500 characters."
  }
  ```

---

### 3. Conversation History Endpoint
Retrieves all historical user and assistant messages for a session ordered by creation timestamp.

- **Method**: `GET`
- **Path**: `/chat/{session_id}`

#### Response (HTTP 200 OK)
```json
{
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "messages": [
    {
      "id": "1a2b3c4d-5678-90ab-cdef-1234567890ab",
      "role": "user",
      "content": "What is CMCHIS?",
      "created_at": "2026-07-29T12:00:00.000000+00:00"
    },
    {
      "id": "7b9e2a14-8842-470a-a921-6571fa0c2d3b",
      "role": "assistant",
      "content": "The Chief Minister's Comprehensive Health Insurance Scheme is...",
      "created_at": "2026-07-29T12:00:02.000000+00:00"
    }
  ]
}
```

#### Error Responses
- `HTTP 404 Not Found`: Session ID does not exist in PostgreSQL.
- `HTTP 422 Unprocessable Entity`: Invalid UUID format string.

---

### 4. User Feedback Endpoint
Records thumbs up (`"up"`) or thumbs down (`"down"`) ratings and optional user comments for an assistant message.

- **Method**: `POST`
- **Path**: `/feedback`
- **Headers**: `Content-Type: application/json`

#### Request Body
```json
{
  "message_id": "7b9e2a14-8842-470a-a921-6571fa0c2d3b",
  "rating": "up",
  "comment": "Accurate eligibility details."
}
```

#### Response (HTTP 200 OK)
```json
{
  "status": "success",
  "message": "Feedback submitted successfully."
}
```

#### Error Responses
- `HTTP 422 Unprocessable Entity`: Rating is not `"up"` or `"down"`.
- `HTTP 404 Not Found`: `message_id` does not exist in `chat_messages` table.
