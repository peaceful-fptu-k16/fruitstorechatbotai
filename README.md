# FruitStoreChatbotAI

Production-style multi-agent RAG chatbot for a fruit store, built with FastAPI + Next.js.

The system combines deterministic business logic and pretrained semantic models to provide:
- natural product consultation,
- inventory and FAQ support,
- admin stock management with JWT + idempotency,
- resilient fallback behavior when model loading is unavailable.

## 1. Key Features

- Multi-agent orchestration:
	- RouterAgent: intent routing (semantic-first + rule fallback)
	- RecommendationAgent: preference-aware ranking
	- InventoryAgent: stock lookup
	- FAQAgent: retrieval-based Q&A
	- MemoryAgent: session preference accumulation
- RAG pipeline with pretrained models:
	- Embedding model: BAAI/bge-m3
	- Cross-encoder reranker: BAAI/bge-reranker-v2-m3
- Rich product schema:
	- taste, texture, nutrition, usage, shelf-life attributes
- Operational safety:
	- idempotent admin stock updates
	- in-memory rate limiting
	- model fallback strategy for stable runtime
	- automatic user question logging

## 2. Architecture Overview

Runtime request flow (chat/recommend):
1. API receives user query.
2. MemoryAgent updates session preferences.
3. RouterAgent determines intent.
4. For recommendation/FAQ intents, retriever performs semantic search (and reranking if enabled).
5. RecommendationAgent blends semantic relevance with preference constraints.
6. Response is returned with optional product citations.

Startup flow:
1. Create database tables.
2. Seed canonical products/FAQ documents.
3. Auto-patch new product columns in SQLite when needed.
4. Build service container and retrieval index.

## 3. Technology Stack

- Backend:
	- FastAPI 0.116.1
	- SQLAlchemy 2.0.41
	- Pydantic 2.11.7
	- Uvicorn 0.35.0
- ML/RAG:
	- sentence-transformers 3.0.1
	- numpy 2.0.2
- Frontend:
	- Next.js 15.5.18
	- React 19.1.1
	- TailwindCSS 3.4.17
	- Framer Motion 12.38.0

## 4. Rich Product Data Model

Each product includes:

- Basic commerce:
	- `name`, `category`, `price`, `stock`, `origin`, `season`, `description`
- Taste and texture:
	- `sweetness_level`, `sourness_level`, `seed_level`
	- `juiciness_level`, `aroma_level`, `crunchiness_level`, `texture`
- Nutrition:
	- `fiber_level`, `vitamin_c_level`, `sugar_content_level`, `calories_per_100g`
- Usage and freshness:
	- `color`, `best_use`, `shelf_life_days`

This richer schema is directly exposed in product APIs and used by recommendation scoring.

## 5. Project Structure

```text
fruit-chatbot/
├── backend/
│   ├── agents/          # business agents (router, recommendation, memory, etc.)
│   ├── api/             # FastAPI endpoints
│   ├── core/            # config, security, rate-limit, cache, service wiring
│   ├── database/        # SQLAlchemy models/session/queries
│   ├── rag/             # embeddings, vector store, retriever, reranker
│   ├── tests/           # regression/smoke tests
│   └── main.py
├── frontend/
│   └── src/             # Next.js app/components/lib
├── ai_log/              # AI usage and user question logs
└── docker-compose.yml
```

## 6. Prerequisites

- Python 3.11+
- Node.js 18+ (recommended: Node 20+)
- npm
- Optional: Docker + Docker Compose

## 7. Local Setup (Recommended)

### 7.1 Backend

From repository root:

```bash
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

Run API:

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open:
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

### 7.2 Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:
- UI: http://localhost:3000

### 7.3 Quick Offline-Safe Startup (optional)

Useful for fast local validation on machines that should avoid remote model downloads:

```powershell
$env:ALLOW_REMOTE_MODEL_DOWNLOAD='false'
$env:EMBEDDING_BACKEND='hashing'
$env:USE_PRETRAINED_INTENT_ROUTER='false'
$env:USE_PRETRAINED_RERANKER='false'
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## 8. Docker Setup

```bash
docker compose up --build
```

Services:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000

## 9. Configuration

Primary environment variables (`.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./backend/data/fruit_chatbot.db` | database connection |
| `ADMIN_JWT_SECRET` | `change-me` | JWT signing secret |
| `ADMIN_USERNAME` | `admin` | admin login username |
| `ADMIN_PASSWORD` | `admin123` | admin login password |
| `RATE_LIMIT_REQUESTS` | `30` | max requests in window for admin update |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | rate-limit window |
| `CORS_ORIGINS` | `["*"]` | allowed origins |
| `ALLOW_REMOTE_MODEL_DOWNLOAD` | `true` | allow downloading pretrained models |
| `USE_PRETRAINED_INTENT_ROUTER` | `true` | semantic intent routing toggle |
| `PRETRAINED_INTENT_MODEL_NAME` | `BAAI/bge-m3` | intent embedding model |
| `PRETRAINED_INTENT_MIN_CONFIDENCE` | `0.55` | semantic route confidence threshold |
| `EMBEDDING_BACKEND` | `sentence_transformers` | embedding backend (`sentence_transformers` or fallback hashing) |
| `EMBEDDING_MODEL_NAME` | `BAAI/bge-m3` | retrieval embedding model |
| `USE_PRETRAINED_RERANKER` | `true` | cross-encoder reranker toggle |
| `PRETRAINED_RERANKER_MODEL_NAME` | `BAAI/bge-reranker-v2-m3` | reranker model |
| `RERANKER_CANDIDATE_POOL` | `30` | candidates before rerank |
| `RESPONSE_GENERATION_MODE` | `llm_only` | response mode: `llm_only`, `hybrid`, or `deterministic` |
| `ENABLE_LLM_RESPONSE_REWRITE` | `true` | enable Gemini response generation/rewrite |
| `GEMINI_API_KEY` | `` | Gemini API key (required for `llm_only`) |
| `GEMINI_MODEL_NAME` | `gemini-1.5-flash` | Gemini model for response generation |
| `GEMINI_TIMEOUT_SECONDS` | `6.0` | timeout for Gemini calls |
| `GEMINI_TEMPERATURE` | `0.2` | low temperature for stable Gemini outputs |
| `ENABLE_USER_QUERY_LOGGING` | `true` | write user queries to log |
| `USER_QUERY_LOG_PATH` | `ai_log/user_questions.jsonl` | query log file path |
| `ENABLE_QA_PAIR_LOGGING` | `true` | log each question-answer pair |
| `QA_PAIR_LOG_PATH` | `ai_log/qa_pairs.jsonl` | question-answer log file path |
| `ENABLE_ANSWER_QUALITY_REVIEW` | `true` | let Gemini self-review each answer quality |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | frontend API base URL |

## 10. Model Strategy and Fallbacks

Default strategy:
- semantic intent routing and retrieval with pretrained models,
- reranking with cross-encoder,
- preference-aware recommendation blending semantic score + constraints.

Fallback guarantees:
- if embeddings fail to load -> hashing embeddings are used,
- if reranker fails -> embedding order is used,
- if semantic routing is unavailable -> keyword rules are used.

Response generation strategy:
- `llm_only`: Gemini must generate the final answer; no deterministic fallback is used.
- `hybrid`: deterministic draft + Gemini rewrite when available.
- `deterministic`: no external LLM call.

For strict LLM behavior (no fallback), keep `RESPONSE_GENERATION_MODE=llm_only` and provide `GEMINI_API_KEY`.

Answer quality self-review:
- Each Q/A pair can be logged to `ai_log/qa_pairs.jsonl`.
- Gemini can score and comment on each answer (strengths/issues/lessons) for iterative improvement.

Gemini quick setup:

```powershell
$env:ENABLE_LLM_RESPONSE_REWRITE='true'
$env:RESPONSE_GENERATION_MODE='llm_only'
$env:GEMINI_API_KEY='your_real_key_here'
$env:GEMINI_MODEL_NAME='gemini-1.5-flash'
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## 11. API Reference (Core)

### `GET /health`
Returns service health.

### `POST /chat`
Natural chat endpoint with intent routing.

Request:

```json
{
	"user_id": "demo-user",
	"session_id": "session-1",
	"message": "Gợi ý trái cây ít đường, nhiều chất xơ",
	"language": "vi"
}
```

Response includes:
- `intent`, `confidence`, `answer`, `products`, `citations`, `fallback`.

### `GET /products`
Query params:
- `query` (optional)
- `available_only` (optional, bool)
- `limit` (default 20, max 200)

### `GET /inventory`
Query params:
- `product_id` or `name`

### `POST /recommend`
Structured recommendation endpoint.

Request:

```json
{
	"query": "Mình muốn trái mọng nước để ép",
	"user_id": "demo-user",
	"session_id": "session-1",
	"budget": 100000,
	"limit": 4
}
```

### Admin endpoints

#### `POST /admin/login`
Get bearer token.

#### `POST /admin/update-stock`
Requires:
- `Authorization: Bearer <token>`
- `Idempotency-Key: <unique-key>`

Supported stock operations:
- `set`
- `inc`
- `dec`

## 12. Logging and Observability

- User query logging:
	- source endpoints: `POST /chat`, `POST /recommend`
	- default file: `ai_log/user_questions.jsonl`
	- format: one JSON object per line (timestamp, source, session_id, user_id, question, metadata)
- AI operation history:
	- file: `ai_log/ai_usage_log.md`

## 13. Testing

Run smoke tests:

```bash
python -m pytest backend/tests/test_smoke.py -q
```

Run main regression set:

```bash
python -m pytest backend/tests/test_recommendation_agent.py backend/tests/test_retriever_reranking.py backend/tests/test_router_agent.py backend/tests/test_smoke.py -q
```

Notes:
- Tests bootstrap an offline-safe environment using `backend/tests/conftest.py`.

## 14. Troubleshooting

- Backend startup is slow on first run:
	- pretrained model weights may need downloading.
- Windows cache/symlink warnings from Hugging Face:
	- expected on some setups; functionality still works.
- Frontend cannot reach backend:
	- check `NEXT_PUBLIC_API_BASE_URL`
	- verify backend at `http://localhost:8000/health`.
- Database schema mismatch after adding new fields:
	- app startup runs schema patching for product columns in SQLite,
	- restart backend to trigger patch + reseed.

## 15. Security Notes

- Change `ADMIN_JWT_SECRET` for real deployments.
- Replace default admin credentials before exposing services.
- Restrict `CORS_ORIGINS` outside development.

## 16. License and Usage

This repository is intended for educational/demo use unless your organization defines a separate license policy.
