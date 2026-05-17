from __future__ import annotations

import re
from collections import Counter
from typing import Protocol

import numpy as np


class BaseEmbeddingModel(Protocol):
    dim: int

    def embed_text(self, text: str) -> np.ndarray:
        ...

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        ...


class HashingEmbeddingModel:
    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\w+", text.lower(), flags=re.UNICODE)

    def embed_text(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dim, dtype=np.float32)
        tokens = self._tokenize(text)
        if not tokens:
            return vector

        counts = Counter(tokens)
        for token, freq in counts.items():
            idx = hash(token) % self.dim
            vector[idx] += float(freq)

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm
        return vector

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.vstack([self.embed_text(text) for text in texts])


class SentenceTransformerEmbeddingModel:
    def __init__(
        self,
        *,
        model_name: str = "BAAI/bge-m3",
        normalize_embeddings: bool = True,
        local_files_only: bool = True,
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("sentence-transformers is not available") from exc

        self.model = SentenceTransformer(model_name, local_files_only=local_files_only)
        self.dim = int(self.model.get_sentence_embedding_dimension())
        self.normalize_embeddings = normalize_embeddings

    def _normalize_rows(self, vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        safe_norms = np.where(norms == 0.0, 1.0, norms)
        return vectors / safe_norms

    def embed_text(self, text: str) -> np.ndarray:
        vectors = self.embed_batch([text])
        if vectors.size == 0:
            return np.zeros((self.dim,), dtype=np.float32)
        return vectors[0]

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)

        vectors = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=self.normalize_embeddings,
            show_progress_bar=False,
        )
        arr = np.asarray(vectors, dtype=np.float32)
        if not self.normalize_embeddings:
            arr = self._normalize_rows(arr)
        return arr
