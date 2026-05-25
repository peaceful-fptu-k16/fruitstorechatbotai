from __future__ import annotations

from sqlalchemy.orm import Session

from backend.core.text import normalize_text
from backend.database.queries import list_faq_documents
from backend.rag.retriever import HybridRetriever


class FAQAgent:
    def __init__(self, retriever: HybridRetriever) -> None:
        self.retriever = retriever

    def answer(self, db: Session, query: str) -> tuple[str, list[dict]]:
        faq_docs = list_faq_documents(db)
        if not faq_docs:
            return "Shop chưa có dữ liệu FAQ. Vui lòng liên hệ CSKH.", []

        normalized = normalize_text(query)
        topic = None
        if any(token in normalized for token in ("ship", "giao", "delivery", "bao lau")):
            topic = "shipping"
        elif any(token in normalized for token in ("doi", "tra", "refund")):
            topic = "return"
        elif any(token in normalized for token in ("bao quan", "tu lanh", "giu tuoi")):
            topic = "storage"

        if topic:
            for doc in faq_docs:
                if doc.topic == topic:
                    citation = {
                        "source_id": f"faq:{doc.id}",
                        "source_type": "faq",
                        "snippet": doc.answer,
                        "score": 1.0,
                    }
                    return doc.answer, [citation]

        ranked = self.retriever.semantic_search(query, top_k=1, scope="faq")
        if ranked:
            top = ranked[0]
            citation = {
                "source_id": top["id"],
                "source_type": "faq",
                "snippet": top["text"][:180],
                "score": float(top["score"]),
            }
            return top["text"], [citation]

        fallback = faq_docs[0]
        return fallback.answer, [
            {
                "source_id": f"faq:{fallback.id}",
                "source_type": "faq",
                "snippet": fallback.answer,
                "score": 0.5,
            }
        ]
