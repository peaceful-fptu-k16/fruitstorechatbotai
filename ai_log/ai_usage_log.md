# AI Usage Log

## 2026-05-16
- User request: "hãy update để sử dụng deeplearning, nếu chưa có thì hãy sử dụng model đã có, không nên tự training"
- Assistant action: Updated recommendation flow to use pretrained deep learning first and fallback to existing model when unavailable. No custom training added.
- Scope: backend recommendation agent, chat/recommend APIs, retriever capability flag, tests, README.

## 2026-05-16 (follow-up)
- User request: "bạn hãy tìm kiếm 1 vài mô hình deeplearning mạnh phù hợp cho dự án này"
- Assistant action: Researched strong pretrained embedding/reranker/LLM options suitable for multilingual Vietnamese fruit chatbot and prepared implementation-oriented shortlist (no training).
- Scope: model selection guidance for router, retrieval, reranking, and optional generation.

## 2026-05-16 (stack decision)
- User request: "hãy chọn 1 stack ok nhất để làm dự án demo"
- Assistant action: Chose one production-safe demo stack with strongest quality-to-effort tradeoff for this codebase and clarified deployment profile.
- Scope: embedding, reranking, generation strategy, and practical rollout recommendation.

## 2026-05-16 (stack implementation)
- User request: "Embedding + retrieval: BAAI/bge-m3; Reranking: BAAI/bge-reranker-v2-m3; Chat generation: Qwen/Qwen2.5-7B-Instruct ... hãy làm theo stack này api Qwen tôi sẽ cung cấp sau"
- Assistant action: Implemented stack wiring in backend with bge-m3 defaults, optional bge reranker integration, and plug-and-play Qwen provider service that stays disabled until API credentials are provided.
- Scope: config defaults, retriever/reranker pipeline, chat integration, tests, and README updates.

## 2026-05-16 (bge-m3 confirmation)
- User request: "hãy dùng BAAI/bge-m3 ..."
- Assistant action: Verified that bge-m3 is consistently configured as default embedding model for RAG and semantic intent/router across backend code and README.
- Scope: configuration verification and documentation consistency.

## 2026-05-16 (remove qwen)
- User request: "vậy hãy toàn bộ liên quan đến qwen"
- Assistant action: Removed all Qwen integration from backend config, service wiring, chat rewrite hook, docs, and tests to keep the demo stack fully local and free.
- Scope: cleanup of Qwen-specific code paths and documentation.

## 2026-05-16 (data folder clarification)
- User request: "vậy folder data hiện tại đang để làm gì, toi thấy nó xuất hiện từ đầu mà không có gì được thêm vào"
- Assistant action: Audited runtime/storage references and explained which data folders are active vs placeholder.
- Scope: docker mount paths, sqlite runtime storage, and ML dataset folder usage status.

## 2026-05-16 (cleanup and run)
- User request: "hãy dọn dẹp hết, và chạy project lên"
- Assistant action: Cleaned stale project artifacts/config references and started the project services for local demo run.
- Scope: environment example sync, structure/docs cleanup, runtime startup verification.

## 2026-05-16 (pretrained enforcement and accented Vietnamese)
- User request: "hiện tại đang chưa sử dụng model pretrained hãy sử dụng... từ giờ trở đi hãy sử dụng tiếng việt có dấu"
- Assistant action: Enabled remote model download by default to prioritize pretrained loading, converted user-facing fallback messages to accented Vietnamese, and stabilized tests with offline-safe overrides.
- Scope: config defaults, env example, recommendation messages, and test bootstrap behavior.

## 2026-05-16 (runtime verification and startup)
- User request: Continue from summary state and confirm pretrained usage is active in runtime.
- Assistant action: Verified runtime config points to pretrained bge-m3, confirmed backend chat response reports deep-learning-pretrained ranking, added lazy reranker loading to reduce startup blocking risk, re-ran tests, and restarted backend/frontend.
- Scope: runtime smoke checks, retriever startup behavior improvement, test verification, and service restart.

## 2026-05-16 (response polish for edge cases)
- User request: "có 1 vài trường hợp khác như này" (phản hồi recommendation còn lặp ý, còn cụm kỹ thuật/English và format chưa mượt).
- Assistant action: Refined user-facing recommendation wording in Vietnamese with diacritics, replaced technical phrases (deep learning pretrained, RAG label) by natural phrasing, normalized budget phrasing, and versioned cache keys to avoid serving stale older responses.
- Scope: recommendation agent reasoning text, chat answer formatter, recommend/chat cache keys, related tests.

## 2026-05-16 (auto logging user questions)
- User request: "bạn có thể lưu lại các câu tôi hỏi được không, tức là ghi log"
- Assistant action: Added automatic file-based logging for user questions in both `/chat` and `/recommend`, with env-configurable on/off switch and log path, plus documentation and test-safe toggle.
- Scope: observability logger module, API hooks, settings/env example, README, gitignore, and regression verification.

## 2026-05-17 (enrich fruit data and natural responses)
- User request: "hãy làm giàu data lên và cho thêm nhiều thuộc tính của quả. Tôi muốn chatbot trả lời 1 cách tự nhiên hơn, không bị ràng buộc"
- Assistant action: Expanded product schema with richer taste/nutrition/usage attributes, seeded a broader fruit catalog, upgraded recommendation constraints and scoring to use new attributes, improved semantic indexing text, and rewrote recommendation phrasing to be more conversational and less rigid.
- Scope: product model/schema/mapper, seed data and schema patching, memory + recommendation + router logic, chat/recommend response formatting, frontend product type/card, README, and regression tests.

## 2026-05-17 (run project and publish GitHub)
- User request: "hãy thử chạy dự án và up lên github: https://github.com/peaceful-fptu-k16/fruitstorechatbotai.git"
- Assistant action: Started frontend successfully, started backend in offline-safe mode for quick runtime validation, verified health and frontend HTTP status, initialized git repository, committed project, configured remote origin, and pushed branch `main` to the provided GitHub repository.
- Scope: runtime smoke checks, repository initialization, commit history creation, remote setup, and GitHub push.

## 2026-05-17 (professional README upgrade)
- User request: "hãy chỉnh sửa lại readme cho chi tiết và chuyên nghiệp hơn rồi commit lên git"
- Assistant action: Rewrote README with professional structure including architecture, setup, configuration matrix, API reference, model strategy/fallbacks, observability, testing, troubleshooting, and security guidance; then prepared commit and push.
- Scope: documentation quality uplift and release-ready onboarding instructions.

## 2026-05-17 (run instructions request)
- User request: "cách chạy dự án"
- Assistant action: Provided concise Windows-first run instructions for backend/frontend, plus optional Docker and quick health checks.
- Scope: local startup guidance and operational verification steps.

## 2026-05-17 (fix recommendation intent confusion)
- User request: Chatbot did not distinguish between "ngọt" and "chua/chua nhất" across consecutive queries and asked for more accurate responses.
- Assistant action: Updated recommendation parsing to prioritize current-turn intent over sticky memory, added explicit sour/sour-most constraints, improved ranking tie-break and SQL ordering, bumped recommendation cache keys, and added regression tests for sweet-vs-sour overrides.
- Scope: recommendation agent logic, chat/recommend cache key versioning, and backend regression tests.

## 2026-05-17 (negation phrase understanding + broader tests)
- User request: "Mình tinh chỉnh thêm để bot hiểu tốt hơn các cụm phủ định kiểu 'không quá ngọt', 'chua nhẹ thôi', 'đừng chua quá'. hãy tinh chỉnh thêm nhiều test case khác"
- Assistant action: Added negation-aware parsing for sweet/sour constraints, ensured current-turn sour/low-sour intent overrides remembered sweet preference, added `max_sweetness` handling, updated response criteria text, and expanded recommendation tests with multiple negation/extreme phrase scenarios.
- Scope: recommendation/memory parsing, chat criteria rendering, and extended backend test coverage.

## 2026-05-17 (available response feels hardcoded)
- User request: "Xoài hôm nay có gì ngon không? ... thật sự nó đang trả lời như kiểu được fix cứng không giống model trả lời"
- Assistant action: Reworked available-products chat response from a static template to context-aware natural language, added product-focus detection from user message (including fruit aliases), and prioritized mentioned fruit in answer highlights with richer taste/price/stock details.
- Scope: inventory entity inference, chat answer generation for available-products intent, and regression test for mango-focused query.

## 2026-05-17 (deterministic style layer + Gemini branch)
- User request: "Thêm lớp viết lại câu trả lời theo nhiều phong cách hội thoại (deterministic)... bật nhánh sinh ngôn ngữ bằng LLM khi có API, dùng Gemini api key"
- Assistant action: Added a deterministic multi-style response rewriter service, integrated optional Gemini rewrite branch with automatic fallback to deterministic output on error/timeout/no key, wired it into `/chat` and `/recommend`, added environment configs/docs, and created regression tests for deterministic/fallback/LLM-path behavior.
- Scope: response generation layer, service wiring, API endpoints, environment/readme updates, and test coverage.

## 2026-05-17 (prevent API key from commit)
- User request: "tôi đã thêm api key nhưng commit thì nên tránh commit apikey lên"
- Assistant action: Removed real Gemini API key from tracked `.env.example`, hardened `.gitignore` to ignore all `.env.*` files except `.env.example`, and verified secret-safe git state guidance.
- Scope: environment file hygiene, git ignore safeguards, and secure commit workflow.

## 2026-05-17 (strict llm-only answers + qa review logging)
- User request: "hãy xóa hết phần sử dụng rule based để trả lời câu hỏi và không cần fallback", đồng thời log từng câu hỏi/câu trả lời và tự rút kinh nghiệm chất lượng trả lời.
- Assistant action: Added strict `llm_only` response mode (no deterministic fallback), raised explicit 503 when Gemini is unavailable in strict mode, logged each Q/A pair to JSONL, and added Gemini-based per-answer quality review fields (score/issues/lessons) for continuous tuning.
- Scope: response generation mode, chat/recommend endpoint flow, observability logs, environment config, and regression tests.

## 2026-05-17 (verify qa log after local key)
- User request: "chạy thử một vòng hội thoại sau khi nạp key local để xác nhận log Q/A + quality review đã ghi đúng vào qa_pairs.jsonl"
- Assistant action: Executed end-to-end check and confirmed backend was in `llm_only` while Gemini key was not loaded, resulting in 503 responses and no `qa_pairs.jsonl`; then re-sanitized tracked `.env.example` to avoid leaking secrets and provided strict local-key loading steps.
- Scope: runtime verification, secure env handling, and QA logging readiness check.

## 2026-05-17 (create local env file)
- User request: "hãy làm cho tôi" (create local `.env` setup for Gemini runtime).
- Assistant action: Created local `.env` file with `GEMINI_API_KEY=` placeholder and `RESPONSE_GENERATION_MODE=llm_only`, then verified file existence and git-safe status.
- Scope: local runtime env bootstrap and secret-safe workflow.

## 2026-05-17 (rerun after user added api key)
- User request: "tôi đã thêm api key hãy chạy lại"
- Assistant action: Re-ran runtime verification, identified hidden BOM in `.env` key name causing `gemini_key_configured=false`, rewrote `.env` to UTF-8 without BOM, set valid model `gemini-2.5-flash`, and re-ran chat checks.
- Result: `/chat` returned 200 for test queries and `qa_pairs.jsonl` was created with records; answer-quality review entries were present but currently in `review_mode=error` due non-JSON review payload parsing.
- Scope: runtime env parsing fix, Gemini model compatibility check, and QA log verification.

## 2026-05-17 (stabilize Gemini quality-review JSON)
- User request: Tune prompt/config so Gemini review returns stable JSON and verify `review_mode=gemini` with score/issues/lessons.
- Assistant action: Updated Gemini call config for review with higher output budget and disabled thinking budget to prevent `MAX_TOKENS` empty outputs, added JSON-like normalization parser fallback, and reran end-to-end session checks.
- Result: New `qa_pairs.jsonl` entries for session `qa-check-session-6` show `review_mode=gemini` with populated `score`, `issues`, and `lessons`.
- Scope: response rewriter review pipeline and QA log validation.

## 2026-05-18 (LM migration + RAG re-integration)
- User request: "tôi đã chuyển sang sử dụng LM làm LLM và hãy tích hợp lại RAG cho project"
- Assistant action: Integrated RAG-grounded context into LLM rewrite prompts, wired chat/recommend endpoints to pass retrieval evidence (citations + product facts), added strict `llm_only` LM Studio compatibility path, updated LM-first env/docs defaults, and expanded regression tests for LM strict mode + RAG prompt grounding.
- Result: Backend regression tests passed (`test_response_rewriter`, `test_smoke`, `test_recommendation_agent`, `test_router_agent`, `test_retriever_reranking`).
- Scope: `backend/core/response_rewriter.py`, `backend/api/chat.py`, `backend/api/recommend.py`, `backend/core/config.py`, `backend/tests/test_response_rewriter.py`, `.env.example`, `README.md`.

## 2026-05-18 (load config from .env.secret)
- User request: Received runtime error `Chế độ LLM-only đang bật nhưng LLM không trả về nội dung hợp lệ...` and asked to load configuration from `.env.secret`.
- Assistant action: Updated settings loader to prioritize `.env.secret` when present (fallback `.env`), set explicit `RESPONSE_GENERATION_MODE=lm_studio` in `.env.secret`, and validated effective runtime config values.
- Result: Effective settings now read LM endpoint from `.env.secret` with `response_generation_mode=lm_studio`; smoke tests passed.
- Scope: `backend/core/config.py`, `.env.secret`.

## 2026-05-18 (LM Studio invalid response diagnostics)
- User request: Reported error `LM Studio không trả về nội dung hợp lệ.`.
- Assistant action: Improved LM Studio client handling to surface concrete provider errors (HTTP status/body, timeout, connect error), removed non-standard `thinking` payload for better compatibility, and added runtime propagation of detailed LM Studio error instead of generic message.
- Result: Runtime now reports actionable root cause (e.g., timeout to `http://100.124.21.49:1234/v1/chat/completions`) and existing rewriter tests remain green.
- Scope: `backend/core/response_rewriter.py`.

## 2026-05-18 (LM payload no choices)
- User request: Reported error `LM Studio trả payload không có choices...`.
- Assistant action: Added LM Studio URL normalization/fallback (`/chat/completions` and `/v1/chat/completions`), parsed explicit `error` payloads even on HTTP 200, supported alternative payload text extraction (`output_text`/`output`), and updated `.env.secret` base URL to `/v1`.
- Result: Generic `no choices` error is eliminated; runtime now reports precise provider state: HTTP 400 `No models loaded` for chat completions.
- Scope: `backend/core/response_rewriter.py`, `.env.secret`.

## 2026-05-18 (LM Studio only embedding model loaded)
- User request: Shared LM Studio logs showing `/chat/completions` mismatch and `No models loaded` while `/v1/models` returned only `text-embedding-nomic-embed-text-v1.5`.
- Assistant action: Added LM model autodetection from `/v1/models`, relaxed strict requirement for explicit `LM_STUDIO_MODEL_NAME`, and added explicit runtime error when only embedding models are available.
- Result: Runtime now reports a direct actionable error: `LM Studio hiện chỉ có model embedding, chưa có model chat...` instead of generic invalid payload errors.
- Scope: `backend/core/response_rewriter.py`.

## 2026-05-18 (verify updated LM base URL)
- User request: "tôi cập nhật lại base_url mới"
- Assistant action: Read updated `.env.secret`, then verified `/v1/models`, `/v1/chat/completions`, and internal `ResponseRewriter.rewrite()` against the new endpoint.
- Result: New base URL works; models endpoint returns chat model (`qwen/qwen3-4b-2507`), chat completions return 200 with content, and rewrite mode succeeds in `lm_studio`.
- Scope: runtime verification only (no additional config/code changes required).

## 2026-05-18 (precision hardening from QA review)
- User request: Improve system precision based on QA log findings (entity hard constraint, two-sided budget parser, stronger in-domain routing, output validator, reduced over-suggestion, KPI tracking).
- Assistant action: Implemented entity hard-filter and min/max/range budget parsing in recommendation pipeline; strengthened router heuristics for fruit in-domain queries; added answer validator/repair guard before returning chat responses (fix malformed score token and enforce entity/budget consistency); reduced over-suggestion behavior in available/recommendation phrasing; added KPI report utility from `qa_pairs.jsonl`.
- Result: Regression tests passed (`31 passed`) and KPI script runs with current metrics output.
- Scope: `backend/agents/recommendation_agent.py`, `backend/agents/router_agent.py`, `backend/api/chat.py`, `backend/evaluation/qa_kpi_report.py`, `backend/tests/test_recommendation_agent.py`, `backend/tests/test_router_agent.py`, `backend/tests/test_smoke.py`, `README.md`.

## 2026-05-18 (requested fruit first + similar alternatives)
- User request: "hệ thống gợi ý sản phẩm chạy chưa chuẩn, khi người dùng hỏi về 1 loại quả thì nên gợi ý loại quả đó đầu danh sách, có thể hiển thị thêm 1 vài loại quả có thuộc tính tương tự"
- Assistant action: Updated recommendation ranking to always prioritize products matching requested fruit entities at the top, then fill remaining slots with non-matching products that are most similar by taste/nutrition attributes; adjusted recommendation reason text to explain this behavior; updated chat output guard to keep requested-entity products first without dropping similar alternatives.
- Result: Targeted regression tests passed (`25 passed`) for recommendation + smoke flows.
- Scope: `backend/agents/recommendation_agent.py`, `backend/api/chat.py`, `backend/tests/test_recommendation_agent.py`, `backend/tests/test_smoke.py`.

## 2026-05-18 (frontend UX grouping for recommendations)
- User request: "oke hãy chỉnh sửa UX"
- Assistant action: Updated chat product panel UX to clearly separate recommendation results into two sections when a fruit entity is detected (requested fruit first, similar alternatives after), added contextual explainer text, and added visual badges on product cards (`Ưu tiên đúng loại`, `Gần giống khẩu vị`) to improve scanning and decision speed.
- Result: Frontend TypeScript validation passed (`npx tsc --noEmit` with no diagnostics) and editor diagnostics show no errors in modified frontend files.
- Scope: `frontend/src/components/chat-panel.tsx`, `frontend/src/components/product-card.tsx`.
