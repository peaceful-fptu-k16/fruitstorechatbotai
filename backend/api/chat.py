from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.api.mappers import to_product_out
from backend.core.cache import semantic_cache
from backend.core.text import normalize_text
from backend.database.models import Product
from backend.database.queries import save_message
from backend.database.session import get_db
from backend.observability.query_logger import log_user_question
from backend.schemas import ChatRequest, ChatResponse, CitationOut

router = APIRouter(tags=["chat"])


def _citations_from_results(results: list[dict], source_type: str) -> list[CitationOut]:
    citations: list[CitationOut] = []
    for item in results:
        citations.append(
            CitationOut(
                source_id=item["id"],
                source_type=source_type,
                snippet=item["text"][:180],
                score=float(item["score"]),
            )
        )
    return citations


def _format_vnd(price: int) -> str:
    return f"{price:,.0f}".replace(",", ".") + "đ"


def _join_human_list(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f" và {items[-1]}"


def _build_recommendation_answer(
    *,
    products: list[Product],
    reason: str,
    constraints: dict,
    rag_ranked: list[tuple[Product, float]],
) -> str:
    if not products:
        return "Mình chưa tìm được sản phẩm phù hợp. Bạn thử mở rộng tiêu chí nhé."

    criteria: list[str] = []
    if constraints.get("min_sweetness") is not None:
        criteria.append("độ ngọt cao")
    if constraints.get("max_sweetness") is not None:
        criteria.append("độ ngọt vừa phải")
    if constraints.get("max_sourness") is not None:
        criteria.append("vị ít chua")
    if constraints.get("min_sourness") is not None:
        criteria.append("vị chua rõ")
    if constraints.get("max_seed") is not None:
        criteria.append("ít hạt")
    if constraints.get("min_juiciness") is not None:
        criteria.append("trái mọng nước")
    if constraints.get("min_aroma") is not None:
        criteria.append("mùi thơm tự nhiên")
    if constraints.get("min_crunchiness") is not None:
        criteria.append("độ giòn")
    if constraints.get("min_fiber") is not None:
        criteria.append("nhiều chất xơ")
    if constraints.get("min_vitamin_c") is not None:
        criteria.append("trái giàu vitamin C")
    if constraints.get("max_sugar") is not None:
        criteria.append("trái ít đường")

    budget = constraints.get("budget")
    if budget is not None:
        criteria.append(f"ngân sách không vượt quá {_format_vnd(int(budget))}")

    style_idx = (sum(ord(ch) for ch in products[0].name) + len(criteria)) % 3
    intros = (
        "Mình lọc nhanh theo nhu cầu của bạn và thấy vài lựa chọn khá hợp nè.",
        "Mình vừa so khớp theo khẩu vị bạn mô tả, kết quả khá ổn.",
        "Dựa trên tiêu chí bạn đưa, mình chọn được những trái cây phù hợp nhất lúc này.",
    )

    if criteria:
        intro = f"{intros[style_idx]} Mình ưu tiên {_join_human_list(criteria)}."
    else:
        intro = intros[style_idx]

    score_by_id = {product.id: float(score) for product, score in rag_ranked}
    highlights: list[str] = []
    for product in products[:3]:
        evidence = [f"giá {_format_vnd(product.price)}", f"ngọt {product.sweetness_level}/10", f"chua {product.sourness_level}/10"]

        if constraints.get("min_juiciness") is not None:
            evidence.append(f"mọng nước {product.juiciness_level}/10")
        if constraints.get("min_crunchiness") is not None:
            evidence.append(f"độ giòn {product.crunchiness_level}/10")
        if constraints.get("max_sugar") is not None:
            evidence.append(f"đường tự nhiên {product.sugar_content_level}/10")
        if constraints.get("min_fiber") is not None:
            evidence.append(f"chất xơ {product.fiber_level}/10")
        if constraints.get("min_vitamin_c") is not None:
            evidence.append(f"vitamin C {product.vitamin_c_level}/10")

        # Keep a few rich attributes even when user does not specify them.
        if len(evidence) < 6:
            evidence.append(f"thơm {product.aroma_level}/10")
            evidence.append(f"phù hợp: {product.best_use.lower()}")

        rag_score = score_by_id.get(product.id)
        if rag_score is not None and rag_score > 0.0:
            evidence.append(f"điểm phù hợp {rag_score:.2f}")

        highlights.append(f"{product.name} ({', '.join(evidence[:7])})")

    closings = (
        "Nếu bạn muốn, mình có thể chốt thêm 1-2 lựa chọn đúng gu hơn theo mục đích sử dụng.",
        "Bạn muốn mình thu hẹp tiếp theo kiểu ăn kiêng, ăn vặt hay ép nước không?",
        "Nếu thích, mình sẽ lọc thêm bản tiết kiệm hơn hoặc bản cao cấp hơn cho bạn.",
    )
    more = ""
    if len(products) > 3:
        more = f" Mình còn {len(products) - 3} lựa chọn tương tự nữa."

    return f"{intro} {reason} Gợi ý nổi bật: {'; '.join(highlights)}.{more} {closings[style_idx]}"


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request, db: Session = Depends(get_db)) -> ChatResponse:
    services = request.app.state.services
    trace_id = str(uuid4())

    log_user_question(
        source="/chat",
        question=payload.message,
        user_id=payload.user_id,
        session_id=payload.session_id,
        metadata={"language": payload.language, "trace_id": trace_id},
    )

    services.memory_agent.update_from_message(payload.session_id, payload.message)
    route = services.router_agent.route(payload.message)

    products = []
    citations: list[CitationOut] = []
    fallback = False

    if route.intent == "available_products":
        products = services.inventory_agent.list_available(db, limit=8)
        if products:
            names = ", ".join(product.name for product in products[:4])
            answer = f"Hôm nay shop đang có: {names}. Bạn muốn lọc theo vị ngọt, ít chua hay ngân sách không?"
        else:
            answer = "Hiện tại kho tạm hết sản phẩm. Bạn quay lại sau ít phút nhé."

    elif route.intent == "inventory_check":
        candidate_name = services.inventory_agent.extract_candidate_name(payload.message)
        matches = services.inventory_agent.check_inventory_by_name(db, candidate_name)
        if matches:
            products = matches
            top = matches[0]
            answer = f"{top.name} đang còn {top.stock} sản phẩm trong kho."
        else:
            answer = "Mình chưa tìm thấy sản phẩm bạn hỏi hoặc sản phẩm đang tạm hết hàng."

    elif route.intent == "recommendation":
        cache_key = f"chat:rec:v4:{normalize_text(payload.message)}"
        cached = semantic_cache.get(cache_key)

        if cached:
            answer = cached["answer"]
            products = [db.get(Product, product_id) for product_id in cached["product_ids"]]
            products = [product for product in products if product is not None and product.stock > 0]
            citations = [CitationOut(**citation) for citation in cached["citations"]]
        else:
            profile = services.memory_agent.get_profile(payload.session_id)
            constraints = services.recommendation_agent.parse_preferences(payload.message, profile)
            products, reason = services.recommendation_agent.recommend(
                db,
                query=payload.message,
                profile=profile,
                explicit_budget=None,
                limit=4,
                retriever=services.retriever,
            )

            rag_ranked = services.retriever.hybrid_product_search(
                db,
                query=payload.message,
                top_k=max(4, len(products) * 2),
            )
            semantic = services.retriever.semantic_search(payload.message, top_k=2, scope="product")
            citations = _citations_from_results(semantic, source_type="product")

            if products:
                answer = _build_recommendation_answer(
                    products=products,
                    reason=reason,
                    constraints=constraints,
                    rag_ranked=rag_ranked,
                )
            else:
                answer = "Mình chưa tìm được sản phẩm phù hợp. Bạn thử mở rộng tiêu chí nhé."

            semantic_cache.set(
                cache_key,
                {
                    "answer": answer,
                    "product_ids": [product.id for product in products],
                    "citations": [citation.model_dump() for citation in citations],
                },
                ttl_seconds=120,
            )

    elif route.intent in {"faq_shipping", "faq_return", "faq_storage"}:
        cache_key = f"chat:faq:{normalize_text(payload.message)}"
        cached = semantic_cache.get(cache_key)
        if cached:
            answer = cached["answer"]
            citations = [CitationOut(**citation) for citation in cached["citations"]]
        else:
            answer, faq_citations = services.faq_agent.answer(db, payload.message)
            citations = [CitationOut(**citation) for citation in faq_citations]
            semantic_cache.set(
                cache_key,
                {
                    "answer": answer,
                    "citations": [citation.model_dump() for citation in citations],
                },
                ttl_seconds=300,
            )

    elif route.intent == "admin_update_stock":
        answer = "Yêu cầu cập nhật kho cần dùng endpoint /admin/update-stock với token admin."

    else:
        fallback = True
        answer = (
            "Mình tập trung hỗ trợ mua trái cây và thông tin của shop. "
            "Bạn có thể hỏi về sản phẩm, tồn kho, gợi ý theo vị, giao hàng hoặc đổi trả."
        )

    save_message(
        db,
        session_id=payload.session_id,
        user_id=payload.user_id,
        role="user",
        content=payload.message,
        metadata_json={"trace_id": trace_id, "intent": route.intent},
    )
    save_message(
        db,
        session_id=payload.session_id,
        user_id=payload.user_id,
        role="assistant",
        content=answer,
        metadata_json={"trace_id": trace_id, "intent": route.intent, "fallback": fallback},
    )

    return ChatResponse(
        trace_id=trace_id,
        intent=route.intent,
        confidence=route.confidence,
        answer=answer,
        products=[to_product_out(product) for product in products],
        citations=citations,
        fallback=fallback,
    )
