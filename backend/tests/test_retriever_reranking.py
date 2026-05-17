from __future__ import annotations

from types import SimpleNamespace

from backend.rag.retriever import HybridRetriever
from backend.rag.vector_store import VectorDocument


class DummyReranker:
    def __init__(self, score_by_id: dict[str, float]) -> None:
        self.score_by_id = score_by_id

    def rerank(self, query: str, documents: list[tuple[str, str]], *, top_k: int) -> list[tuple[str, float]]:
        _ = query
        ranked = sorted(
            ((doc_id, float(self.score_by_id.get(doc_id, 0.0))) for doc_id, _text in documents),
            key=lambda item: item[1],
            reverse=True,
        )
        return ranked[:top_k]


def test_semantic_search_uses_reranker_order(monkeypatch) -> None:
    fake_settings = SimpleNamespace(
        embedding_backend="hashing",
        embedding_model_name="BAAI/bge-m3",
        allow_remote_model_download=False,
        use_pretrained_reranker=False,
        pretrained_reranker_model_name="BAAI/bge-reranker-v2-m3",
        reranker_candidate_pool=10,
    )
    monkeypatch.setattr("backend.rag.retriever.get_settings", lambda: fake_settings)

    retriever = HybridRetriever()
    retriever.reranker = DummyReranker(
        {
            "product:2": 0.97,
            "product:1": 0.66,
            "product:3": 0.12,
        }
    )
    retriever.reranker_candidate_pool = 10

    retriever.vector_store.add_documents(
        [
            VectorDocument(
                id="product:1",
                text="Cam ngot it hat",
                metadata={"scope": "product", "product_id": 1},
            ),
            VectorDocument(
                id="product:2",
                text="Nho mau don",
                metadata={"scope": "product", "product_id": 2},
            ),
            VectorDocument(
                id="product:3",
                text="Buoi da xanh",
                metadata={"scope": "product", "product_id": 3},
            ),
        ]
    )

    results = retriever.semantic_search("goi y trai cay", top_k=2, scope="product")

    assert len(results) == 2
    assert results[0]["id"] == "product:2"
    assert results[1]["id"] == "product:1"
    assert float(results[0]["metadata"]["rerank_score"]) == 0.97
