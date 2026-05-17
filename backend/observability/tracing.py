from __future__ import annotations

from uuid import uuid4


def generate_trace_id() -> str:
    return str(uuid4())


def structured_event(event: str, **fields) -> dict:
    payload = {"event": event}
    payload.update(fields)
    return payload
