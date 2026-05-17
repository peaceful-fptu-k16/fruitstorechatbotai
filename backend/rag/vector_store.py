from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from backend.rag.embeddings import BaseEmbeddingModel


@dataclass
class VectorDocument:
    id: str
    text: str
    metadata: dict


class InMemoryVectorStore:
    def __init__(self, embedding_model: BaseEmbeddingModel) -> None:
        self.embedding_model = embedding_model
        self.documents: list[VectorDocument] = []
        self.embeddings = np.zeros((0, embedding_model.dim), dtype=np.float32)

    def reset(self) -> None:
        self.documents.clear()
        self.embeddings = np.zeros((0, self.embedding_model.dim), dtype=np.float32)

    def add_documents(self, documents: list[VectorDocument]) -> None:
        if not documents:
            return

        vectors = self.embedding_model.embed_batch([doc.text for doc in documents])
        if self.embeddings.size == 0:
            self.embeddings = vectors
        else:
            self.embeddings = np.vstack([self.embeddings, vectors])
        self.documents.extend(documents)

    def similarity_search(
        self,
        query: str,
        *,
        top_k: int = 5,
        scope: Optional[str] = None,
    ) -> list[dict]:
        if not self.documents:
            return []

        query_vector = self.embedding_model.embed_text(query)
        if np.linalg.norm(query_vector) == 0:
            return []

        similarities = self.embeddings @ query_vector

        candidates: list[tuple[int, float]] = []
        for idx, score in enumerate(similarities):
            doc = self.documents[idx]
            if scope is not None and doc.metadata.get("scope") != scope:
                continue
            candidates.append((idx, float(score)))

        candidates.sort(key=lambda item: item[1], reverse=True)
        top = candidates[:top_k]

        results = []
        for idx, score in top:
            doc = self.documents[idx]
            results.append(
                {
                    "id": doc.id,
                    "text": doc.text,
                    "metadata": doc.metadata,
                    "score": score,
                }
            )

        return results
