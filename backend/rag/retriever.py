from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from backend.core.config import get_settings
from backend.database.queries import list_faq_documents, list_products
from backend.rag.embeddings import BaseEmbeddingModel, HashingEmbeddingModel, SentenceTransformerEmbeddingModel
from backend.rag.reranker import BaseReranker, CrossEncoderReranker
from backend.rag.vector_store import InMemoryVectorStore, VectorDocument


class HybridRetriever:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.embedding_model = self._build_embedding_model()
        self.vector_store = InMemoryVectorStore(self.embedding_model)
        self.reranker: Optional[BaseReranker] = None
        self._reranker_attempted = False
        self.reranker_candidate_pool = max(8, int(self.settings.reranker_candidate_pool))

    @property
    def supports_deep_learning(self) -> bool:
        return isinstance(self.embedding_model, SentenceTransformerEmbeddingModel)

    def _build_embedding_model(self) -> BaseEmbeddingModel:
        backend = self.settings.embedding_backend.strip().lower()

        if backend == "sentence_transformers":
            try:
                return SentenceTransformerEmbeddingModel(
                    model_name=self.settings.embedding_model_name,
                    local_files_only=not self.settings.allow_remote_model_download,
                )
            except Exception:
                # Fall back to deterministic hashing embeddings when pretrained model
                # cannot be loaded (missing package, network/model cache issue, etc.).
                return HashingEmbeddingModel(dim=256)

        return HashingEmbeddingModel(dim=256)

    def _build_reranker(self) -> Optional[BaseReranker]:
        if not self.settings.use_pretrained_reranker:
            return None

        try:
            return CrossEncoderReranker(
                model_name=self.settings.pretrained_reranker_model_name,
                local_files_only=not self.settings.allow_remote_model_download,
            )
        except Exception:
            # Keep retrieval online even if reranker model cannot be loaded.
            return None

    def _ensure_reranker_loaded(self) -> Optional[BaseReranker]:
        if self.reranker is not None:
            return self.reranker

        if self._reranker_attempted:
            return None

        self._reranker_attempted = True
        self.reranker = self._build_reranker()
        return self.reranker

    def _rerank_results(self, query: str, results: list[dict], *, top_k: int) -> list[dict]:
        if self.reranker is None or not results:
            return results[:top_k]

        candidate_pool = min(len(results), max(top_k, self.reranker_candidate_pool))
        candidates = results[:candidate_pool]
        docs = [(item["id"], item["text"]) for item in candidates]

        try:
            reranked = self.reranker.rerank(query, docs, top_k=min(top_k, len(candidates)))
        except Exception:
            return results[:top_k]

        if not reranked:
            return results[:top_k]

        by_id = {item["id"]: item for item in candidates}
        ordered: list[dict] = []
        for doc_id, rerank_score in reranked:
            original = by_id.get(doc_id)
            if original is None:
                continue

            metadata = dict(original.get("metadata", {}))
            metadata["rerank_score"] = float(rerank_score)
            ordered.append(
                {
                    "id": original["id"],
                    "text": original["text"],
                    "metadata": metadata,
                    "score": float(rerank_score),
                }
            )

        return ordered if ordered else results[:top_k]

    def rebuild_index(self, db: Session) -> None:
        self.vector_store.reset()

        docs: list[VectorDocument] = []
        products = list_products(db, only_available=False, query=None, limit=500)
        for product in products:
            text = (
                f"{product.name}. {product.description}. "
                f"Màu {product.color}. Kết cấu {product.texture}. "
                f"Vị ngọt {product.sweetness_level}/10, vị chua {product.sourness_level}/10, độ hạt {product.seed_level}/10. "
                f"Mọng nước {product.juiciness_level}/10, thơm {product.aroma_level}/10, giòn {product.crunchiness_level}/10. "
                f"Chất xơ {product.fiber_level}/10, vitamin C {product.vitamin_c_level}/10, đường tự nhiên {product.sugar_content_level}/10. "
                f"Năng lượng {product.calories_per_100g} kcal/100g. Hợp cho {product.best_use}. "
                f"Giá {product.price} VND. Bảo quản tốt trong {product.shelf_life_days} ngày."
            )
            docs.append(
                VectorDocument(
                    id=f"product:{product.id}",
                    text=text,
                    metadata={"scope": "product", "product_id": product.id, "name": product.name},
                )
            )

        faqs = list_faq_documents(db)
        for faq in faqs:
            docs.append(
                VectorDocument(
                    id=f"faq:{faq.id}",
                    text=f"{faq.question} {faq.answer}",
                    metadata={"scope": "faq", "topic": faq.topic},
                )
            )

        self.vector_store.add_documents(docs)

    def semantic_search(self, query: str, *, top_k: int = 5, scope: Optional[str] = None) -> list[dict]:
        reranker = self._ensure_reranker_loaded()
        if reranker is None:
            return self.vector_store.similarity_search(query, top_k=top_k, scope=scope)

        raw_top_k = max(top_k, self.reranker_candidate_pool)
        initial = self.vector_store.similarity_search(query, top_k=raw_top_k, scope=scope)
        return self._rerank_results(query, initial, top_k=top_k)
