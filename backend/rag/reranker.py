from __future__ import annotations

from typing import Protocol

import numpy as np


class BaseReranker(Protocol):
    def rerank(self, query: str, documents: list[tuple[str, str]], *, top_k: int) -> list[tuple[str, float]]:
        ...


class CrossEncoderReranker:
    def __init__(self, *, model_name: str = "BAAI/bge-reranker-v2-m3", local_files_only: bool = True) -> None:
        try:
            from sentence_transformers import CrossEncoder
        except Exception as exc:  # pragma: no cover - optional dependency failure path
            raise RuntimeError("sentence-transformers CrossEncoder is not available") from exc

        self.model = CrossEncoder(
            model_name,
            automodel_args={"local_files_only": local_files_only},
            tokenizer_args={"local_files_only": local_files_only},
        )

    def rerank(self, query: str, documents: list[tuple[str, str]], *, top_k: int) -> list[tuple[str, float]]:
        if not documents:
            return []

        pairs = [[query, text] for _doc_id, text in documents]
        raw_scores = self.model.predict(pairs)
        arr = np.asarray(raw_scores, dtype=np.float32).reshape(-1)

        # Normalize logits to [0,1] for easier downstream scoring/citations.
        probs = 1.0 / (1.0 + np.exp(-arr))
        ranked = sorted(
            zip(documents, probs),
            key=lambda item: float(item[1]),
            reverse=True,
        )

        limited = ranked[: max(1, top_k)]
        return [(doc_id, float(score)) for (doc_id, _text), score in limited]
