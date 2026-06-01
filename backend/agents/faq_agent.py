from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from backend.core.delivery_eta import (
    DELIVERY_AREA_NAMES,
    build_delivery_eta_answer,
    should_try_llm_delivery_area,
)
from backend.core.text import normalize_text
from backend.database.queries import list_faq_documents
from backend.rag.retriever import HybridRetriever

DeliveryAreaResolver = Callable[..., dict[str, Any] | None]


class FAQAgent:
    def __init__(
        self,
        retriever: HybridRetriever,
        delivery_area_resolver: DeliveryAreaResolver | None = None,
    ) -> None:
        self.retriever = retriever
        self.delivery_area_resolver = delivery_area_resolver

    def answer(self, db: Session, query: str) -> tuple[str, list[dict]]:
        normalized = normalize_text(query)
        topic = None
        if any(token in normalized for token in ("ship", "giao", "delivery", "bao lau")):
            topic = "shipping"
        elif any(token in normalized for token in ("doi", "tra", "refund")):
            topic = "return"
        elif any(token in normalized for token in ("bao quan", "tu lanh", "giu tuoi")):
            topic = "storage"

        if topic == "shipping":
            delivery_eta_answer = build_delivery_eta_answer(query)
            source_id = "delivery_eta:nam_tu_liem"
            source_score = 1.0
            if (
                not delivery_eta_answer
                and self.delivery_area_resolver
                and should_try_llm_delivery_area(query)
            ):
                resolved_area = self.delivery_area_resolver(query=query, allowed_areas=DELIVERY_AREA_NAMES)
                if resolved_area:
                    delivery_eta_answer = build_delivery_eta_answer(
                        query,
                        area_hint=str(resolved_area.get("area") or ""),
                        matched_text=str(resolved_area.get("matched_text") or ""),
                        source="llm",
                    )
                    provider = str(resolved_area.get("provider") or "llm")
                    source_id = f"delivery_eta:{provider}"
                    try:
                        source_score = float(resolved_area.get("confidence") or 1.0)
                    except (TypeError, ValueError):
                        source_score = 1.0

            if delivery_eta_answer:
                citation = {
                    "source_id": source_id,
                    "source_type": "faq",
                    "snippet": delivery_eta_answer,
                    "score": source_score,
                }
                return delivery_eta_answer, [citation]

        faq_docs = list_faq_documents(db)
        if not faq_docs:
            return "Shop chưa có dữ liệu FAQ. Vui lòng liên hệ CSKH.", []

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
