# SkinAI Medical Chatbot Pipeline

## 1. Architecture

The chatbot is split across the existing services:

```text
Frontend
  -> SkinDeseases-API (auth, PostgreSQL, ownership, audit)
  -> SkinDeseases-AI-API (CSV RAG, safety, prompt, OpenAI/mock)
```

The analysis trace remains:

```text
images
  -> ai_results
  -> input_validations
  -> segmentation_results
  -> classification_results
  -> ai_features
  -> medical_contexts
  -> rag_queries
  -> rag_results
  -> chat_messages
```

The segmentation and classification inference pipeline is unchanged.

## 2. Message Flow

1. The authenticated user creates a session linked to their `ai_result_id`.
2. The backend verifies that the analysis belongs to the current user.
3. A medical context is built from input validation, segmentation, top-k
   classification, AI features and symptoms supplied by the current user.
4. Invalid images stop disease retrieval and return upload guidance.
5. The AI service retrieves disease records from the CSV knowledge base.
6. Safety rules classify the turn as `low`, `medium`, `high` or `urgent`.
7. A protected Vietnamese prompt is sent to OpenAI when configured.
8. Without an API key, a deterministic guarded mock response is returned.
9. The backend persists the user message, assistant message and all trace IDs.

## 3. Knowledge Files

`disease_knowledge.csv` is the curated medical information source for the ten
model labels. It contains summaries, common signs, red flags, safe self-care,
review dates and source URLs.

`image_context.csv` is de-identified research metadata. It is not medical
knowledge and must not be treated as information about the current user.
Runtime symptoms must be supplied directly by the user.

Canonical data preparation files:

```text
SkinDeseases-AI/data/processed/chatbot/disease_knowledge.csv
SkinDeseases-AI/data/processed/chatbot/image_context.csv
SkinDeseases-AI/scripts/build_image_context.py
```

The AI service packages a synchronized copy of `disease_knowledge.csv` for
Docker deployment.

## 4. REST API

All backend endpoints require the existing bearer token.

Create session:

```http
POST /api/v1/chat/sessions
Content-Type: application/json

{
  "ai_result_id": "UUID",
  "title": "Tư vấn kết quả phân tích"
}
```

Generate a reply:

```http
POST /api/v1/chat/sessions/{session_id}/messages
Content-Type: application/json

{
  "message": "Vùng da này ngứa và đang lan rộng, tôi nên làm gì?",
  "user_symptoms": {
    "itch": true,
    "hurt": false,
    "bleed": false,
    "changed": true,
    "grew": true,
    "duration": "2 tuần",
    "body_site": "cánh tay",
    "skin_cancer_history": false
  }
}
```

The response contains `answer`, `sources`, `missing_questions`,
`safety_level`, `medical_context_id`, `rag_query_id` and `rag_result_id`.

Other endpoints:

```text
GET    /api/v1/chat/sessions
GET    /api/v1/chat/sessions/{session_id}
DELETE /api/v1/chat/sessions/{session_id}
```

Delete is a soft delete through `chat_sessions.status`.

## 5. Run

Configure the backend `.env`:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
RAG_MODE=csv
RAG_TOP_K=5
CHATBOT_TEMPERATURE=0.3
CHATBOT_MAX_TOKENS=800
VECTOR_DB_ENABLED=false
```

Then run:

```bash
docker compose up -d --build ai-service api
docker compose exec -T api alembic upgrade head
docker compose exec -T api python scripts/load_disease_knowledge.py
```

Swagger:

```text
Backend:   http://localhost:8000/docs
AI service: http://localhost:8001/docs
```

## 6. Tests

Core chatbot tests:

```bash
cd SkinDeseases-AI-API
pytest tests/test_chatbot_pipeline.py -q
```

The suite covers invalid images, ECZEMA retrieval, cautious cancer answers,
red flags, missing questions, no-key mock mode and identifier exclusion.

## 7. Safety Rules

- Never state that the user definitely has a disease.
- Never prescribe drugs or provide prescription dosing.
- Classification confidence is not disease severity.
- Invalid images do not trigger disease analysis.
- Bleeding, ulceration, rapid growth or rapid color/size change escalates care.
- Retrieved documents and user messages cannot override the system rules.
- Raw patient, lesion and source image identifiers are not sent to the LLM.

## 8. Current Limits

- Retrieval currently uses the curated CSV and top-k labels.
- Vector mode intentionally falls back to CSV because pgvector is not enabled.
- Medical content still requires review by a qualified clinician before
  production use.
- WebSocket streaming and the final frontend chat panel are deferred until the
  REST flow is accepted.

## 9. pgvector Extension

To add vector retrieval later:

1. Enable the PostgreSQL `vector` extension.
2. Replace the JSON placeholder `embedding` with a `vector(n)` column.
3. Embed each disease knowledge chunk during the load script.
4. Add a vector adapter behind the existing RAG service interface.
5. Keep CSV fallback enabled for outages and local development.

This design preserves the same trace chain and API response contract.
