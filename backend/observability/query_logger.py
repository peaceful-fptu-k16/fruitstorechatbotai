from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from backend.core.config import get_settings

_LOG_WRITE_LOCK = Lock()


def _resolve_log_path(raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path

    project_root = Path(__file__).resolve().parents[2]
    return (project_root / path).resolve()


def _append_jsonl(raw_path: str, payload: dict[str, Any]) -> None:
    log_path = _resolve_log_path(raw_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False)

    with _LOG_WRITE_LOCK:
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(serialized + "\n")


def log_user_question(
    *,
    source: str,
    question: str,
    user_id: str,
    session_id: str,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    if not question.strip():
        return

    settings = get_settings()
    if not settings.enable_user_query_logging:
        return

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "session_id": session_id,
        "user_id": user_id,
        "question": question,
        "metadata": metadata or {},
    }

    try:
        _append_jsonl(settings.user_query_log_path, payload)
    except Exception:
        # Logging is best-effort and must not break request handling.
        return


def log_qa_pair(
    *,
    source: str,
    question: str,
    answer: str,
    user_id: str,
    session_id: str,
    intent: str,
    confidence: Optional[float] = None,
    metadata: Optional[dict[str, Any]] = None,
    review: Optional[dict[str, Any]] = None,
) -> None:
    if not question.strip() or not answer.strip():
        return

    settings = get_settings()
    if not settings.enable_qa_pair_logging:
        return

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "session_id": session_id,
        "user_id": user_id,
        "intent": intent,
        "confidence": confidence,
        "question": question,
        "answer": answer,
        "review": review or {},
        "metadata": metadata or {},
    }

    try:
        _append_jsonl(settings.qa_pair_log_path, payload)
    except Exception:
        return
