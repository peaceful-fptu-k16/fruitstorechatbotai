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
