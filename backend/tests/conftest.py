from __future__ import annotations

import os

# Keep tests deterministic and offline-friendly on CI/Windows by disabling
# remote model downloads and heavy pretrained loading during test startup.
os.environ.setdefault("ALLOW_REMOTE_MODEL_DOWNLOAD", "false")
os.environ.setdefault("EMBEDDING_BACKEND", "hashing")
os.environ.setdefault("USE_PRETRAINED_INTENT_ROUTER", "false")
os.environ.setdefault("USE_PRETRAINED_RERANKER", "false")
os.environ.setdefault("ENABLE_LLM_RESPONSE_REWRITE", "false")
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("ENABLE_USER_QUERY_LOGGING", "false")
