# Multi-Agent RAG Chatbot for Online Fruit Store

## Stack
- Backend: FastAPI + SQLAlchemy
- Agent layer: Router, Inventory, Recommendation, FAQ, Memory (session)
- Retrieval: Hybrid SQL + vector (BAAI/bge-m3) + reranking (BAAI/bge-reranker-v2-m3)
- Frontend: Next.js + React + TailwindCSS
- Security: JWT admin role, idempotent stock updates, in-memory rate limit

## Quick Start (Local)

### 1) Backend
```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
cd ..
uvicorn backend.main:app --reload --port 8000
```

### 2) Frontend
```bash
cd frontend
npm install
npm run dev
```

Open:
- Frontend: http://localhost:3000
- Backend docs: http://localhost:8000/docs

## Quick Start (Docker)
```bash
docker compose up --build
```

## Smoke Tests
```bash
python -m pytest backend/tests/test_smoke.py -q
```

## Pretrained Model + RAG

Project now uses pretrained models and RAG only (no custom training pipeline in codebase):
- Intent routing: semantic matching with pretrained BAAI/bge-m3 embeddings + safe rule-based fallback.
- Retrieval (RAG): Hybrid SQL + semantic retrieval using pretrained BAAI/bge-m3 embeddings, fallback to hashing embeddings if model cannot load.
- Reranking: BAAI/bge-reranker-v2-m3 cross-encoder reranking on retrieved candidates, fallback to embedding-only ranking if reranker cannot load.
- Recommendation: deep-learning-first semantic re-ranking with pretrained embeddings; if unavailable, automatically fallback to the existing rule/constraint model (no self-training).

Configure in `.env`:
```bash
USE_PRETRAINED_INTENT_ROUTER=true
PRETRAINED_INTENT_MODEL_NAME=BAAI/bge-m3
PRETRAINED_INTENT_MIN_CONFIDENCE=0.55
EMBEDDING_BACKEND=sentence_transformers
EMBEDDING_MODEL_NAME=BAAI/bge-m3
USE_PRETRAINED_RERANKER=true
PRETRAINED_RERANKER_MODEL_NAME=BAAI/bge-reranker-v2-m3
RERANKER_CANDIDATE_POOL=30
ALLOW_REMOTE_MODEL_DOWNLOAD=true
ENABLE_USER_QUERY_LOGGING=true
USER_QUERY_LOG_PATH=ai_log/user_questions.jsonl
```

## User Question Logging

User questions are logged automatically from `POST /chat` and `POST /recommend`.
- Default file: `ai_log/user_questions.jsonl`
- Each line is a JSON object with timestamp, endpoint source, session_id, user_id, question, and metadata.

You can disable it by setting:
```bash
ENABLE_USER_QUERY_LOGGING=false
```

If pretrained dependencies are unavailable at runtime, system degrades gracefully:
- Router falls back to keyword rules.
- RAG falls back to deterministic hashing embeddings.
- Reranker falls back to embedding-only retrieval order.
- Recommendation falls back to the existing deterministic preference model.

## Rich Product Data

Product data now includes richer attributes for better personalization:
- Taste + texture profile: sweetness, sourness, seed level, juiciness, aroma, crunchiness.
- Nutrition profile: fiber level, vitamin C level, sugar-content level, calories per 100g.
- Usage profile: color, best use, and shelf-life days.

Recommendation responses are now less rigid and more conversational:
- Chatbot uses a flexible natural-language answer style with varied intros and follow-up prompts.
- Ranking considers broader user intents such as low sugar, high fiber, high vitamin C, juicy/crunchy/aromatic preference, and purpose (juice/salad/snack).

## Core Endpoints
- `POST /chat`
- `GET /products`
- `GET /inventory`
- `POST /recommend`
- `POST /admin/login`
- `POST /admin/update-stock`

## Admin Flow
1. Call `POST /admin/login` with username/password.
2. Use returned Bearer token (HS256 signed) for `POST /admin/update-stock`.
3. Add `Idempotency-Key` header for safe retries.

## Project Structure
```text
fruit-chatbot/
├── backend/
│   ├── agents/
│   ├── api/
│   ├── core/
│   ├── data/
│   ├── database/
│   ├── rag/
│   └── main.py
├── frontend/
│   └── src/
└── docker-compose.yml
```
