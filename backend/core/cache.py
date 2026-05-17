from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Any, Optional


@dataclass
class CacheItem:
    value: Any
    expires_at: float


class SemanticCache:
    """Simple in-memory cache with TTL for low-latency repeated queries."""

    def __init__(self) -> None:
        self._store: dict[str, CacheItem] = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        now = monotonic()
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            if item.expires_at < now:
                self._store.pop(key, None)
                return None
            return item.value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        with self._lock:
            self._store[key] = CacheItem(value=value, expires_at=monotonic() + ttl_seconds)

    def invalidate_prefix(self, prefix: str) -> None:
        with self._lock:
            keys_to_remove = [key for key in self._store if key.startswith(prefix)]
            for key in keys_to_remove:
                self._store.pop(key, None)


semantic_cache = SemanticCache()
