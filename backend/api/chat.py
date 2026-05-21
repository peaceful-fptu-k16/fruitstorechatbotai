from __future__ import annotations

import re
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.api.mappers import to_product_out
from backend.core.cache import semantic_cache
from backend.core.config import get_settings
from backend.core.services import sync_services_with_inventory
from backend.core.text import normalize_text
from backend.database.models import Product
from backend.database.queries import save_message
from backend.database.session import get_db
from backend.observability.query_logger import log_qa_pair, log_user_question
from backend.schemas import ChatRequest, ChatResponse, CitationOut

router = APIRouter(tags=["chat"])
settings = get_settings()


FRUIT_ENTITY_ALIASES: tuple[str, ...] = (
    "thanh long",
    "viet quat",
    "xoai",
    "cam",
    "nho",
    "buoi",
    "tao",
    "dua",
    "chuoi",
    "oi",
    "kiwi",
    "le",
    "man",
    "dau",
)


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


def _extract_question_entities(user_message: str) -> list[str]:
    normalized = normalize_text(user_message)
    entities: list[str] = []
    seen: set[str] = set()

    for alias in sorted(FRUIT_ENTITY_ALIASES, key=len, reverse=True):
        pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"
        if re.search(pattern, normalized) is None:
            continue
        if alias in seen:
            continue
        seen.add(alias)
        entities.append(alias)

    return entities


def _extract_answer_prices(answer: str) -> list[int]:
    prices: list[int] = []
    for match in re.finditer(r"(\d{1,3}(?:[\.\s]\d{3})+|\d+)\s*(đ|d|vnd|k)", answer.lower()):
        raw_value = re.sub(r"[^\d]", "", match.group(1))
        if not raw_value:
            continue
        value = int(raw_value)
        if match.group(2) == "k" and value < 1000:
            value *= 1000
        prices.append(value)
    return prices


def _price_within_bounds(price: int, min_price: int | None, max_price: int | None) -> bool:
    if min_price is not None and price < min_price:
        return False
    if max_price is not None and price > max_price:
        return False
    return True


def _sanitize_answer_output(answer: str) -> str:
    cleaned = re.sub(r"(\d+)\s*/\s*-\s*10", r"\1/10", answer)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _build_safe_recommendation_answer(*, products: list[Product], constraints: dict) -> str:
    if not products:
        return "Mình chưa tìm được sản phẩm khớp đúng tiêu chí hiện tại của bạn."

    min_price = constraints.get("min_price")
    max_price = constraints.get("max_price") or constraints.get("budget")
    if min_price is not None and max_price is not None:
        budget_text = f" trong khoảng {_format_vnd(int(min_price))} đến {_format_vnd(int(max_price))}"
    elif min_price is not None:
        budget_text = f" từ {_format_vnd(int(min_price))} trở lên"
    elif max_price is not None:
        budget_text = f" dưới {_format_vnd(int(max_price))}"
    else:
        budget_text = ""

    picks = products[:2]
    details = "; ".join(
        f"{product.name} (giá {_format_vnd(product.price)}, ngọt {product.sweetness_level}/10, chua {product.sourness_level}/10)"
        for product in picks
    )
    return f"Mình đã lọc theo tiêu chí của bạn{budget_text}: {details}."


def _validate_and_repair_answer(
    *,
    intent: str,
    user_message: str,
    answer: str,
    products: list[Product],
    constraints: dict,
) -> tuple[str, list[Product], bool]:
    repaired = False
    fixed_answer = _sanitize_answer_output(answer)
    normalized_answer = normalize_text(fixed_answer)

    requested_entities = _extract_question_entities(user_message)
    if requested_entities and not any(entity in normalized_answer for entity in requested_entities):
        matched_products = [
            product
            for product in products
            if any(entity in normalize_text(product.name) for entity in requested_entities)
        ]
        if matched_products:
            repaired = True
            if intent == "recommendation":
                matched_ids = {product.id for product in matched_products}
                products = matched_products + [product for product in products if product.id not in matched_ids]
                fixed_answer = _build_safe_recommendation_answer(products=products, constraints=constraints)
            else:
                products = matched_products

            if intent == "inventory_check":
                top = products[0]
                fixed_answer = f"{top.name} đang còn {top.stock} sản phẩm trong kho."
            elif intent == "available_products":
                top = products[0]
                fixed_answer = (
                    f"Hôm nay {top.name} đang khá ổn: {_product_taste_brief(top)}, "
                    f"giá {_format_vnd(top.price)}, còn {top.stock}."
                )

    if intent == "recommendation":
        min_price = constraints.get("min_price")
        max_price = constraints.get("max_price") or constraints.get("budget")

        if min_price is not None or max_price is not None:
            filtered_products = [
                product for product in products if _price_within_bounds(product.price, min_price=min_price, max_price=max_price)
            ]
            if len(filtered_products) != len(products):
                products = filtered_products
                repaired = True

            answer_prices = _extract_answer_prices(fixed_answer)
            if answer_prices and any(
                not _price_within_bounds(price, min_price=min_price, max_price=max_price) for price in answer_prices
            ):
                repaired = True

            if repaired:
                fixed_answer = _build_safe_recommendation_answer(products=products, constraints=constraints)

    return fixed_answer, products, repaired


def _join_human_list(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + f" và {items[-1]}"


def _build_rag_context_for_rewrite(*, citations: list[CitationOut], products: list[Product]) -> list[str]:
    raw_lines: list[str] = []

    for citation in citations[:4]:
        snippet = " ".join(citation.snippet.strip().split())
        if not snippet:
            continue
        raw_lines.append(f"{citation.source_id}: {snippet}")

    for product in products[:4]:
        raw_lines.append(
            f"{product.name}: giá {_format_vnd(product.price)}, còn {product.stock}, "
            f"ngọt {product.sweetness_level}/10, chua {product.sourness_level}/10, "
            f"mọng nước {product.juiciness_level}/10, thơm {product.aroma_level}/10"
        )

    deduped: list[str] = []
    seen: set[str] = set()
    for line in raw_lines:
        key = normalize_text(line)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(line)
        if len(deduped) >= 8:
            break

    return deduped


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

    min_price = constraints.get("min_price")
    max_price = constraints.get("max_price") or constraints.get("budget")
    if min_price is not None and max_price is not None:
        criteria.append(f"ngân sách từ {_format_vnd(int(min_price))} đến {_format_vnd(int(max_price))}")
    elif min_price is not None:
        criteria.append(f"ngân sách từ {_format_vnd(int(min_price))} trở lên")
    elif max_price is not None:
        criteria.append(f"ngân sách không vượt quá {_format_vnd(int(max_price))}")

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

    return f"{intro} {reason} Gợi ý nổi bật: {'; '.join(highlights)}."


def _product_taste_brief(product: Product) -> str:
    notes: list[str] = []

    if product.sweetness_level >= 8:
        notes.append("ngọt đậm")
    elif product.sweetness_level >= 6:
        notes.append("ngọt vừa")
    else:
        notes.append("ngọt nhẹ")

    if product.sourness_level <= 2:
        notes.append("ít chua")
    elif product.sourness_level >= 5:
        notes.append("chua rõ")
    else:
        notes.append("chua nhẹ")

    if product.juiciness_level >= 8:
        notes.append("mọng nước")
    if product.aroma_level >= 7:
        notes.append("thơm")

    return ", ".join(notes[:4])


def _showcase_score(product: Product, user_message: str) -> float:
    normalized = normalize_text(user_message)

    score = (
        product.sweetness_level * 0.34
        + product.aroma_level * 0.24
        + product.juiciness_level * 0.20
        + (10 - product.sourness_level) * 0.16
        + (10 - product.seed_level) * 0.06
    )

    if "ngot" in normalized:
        score += product.sweetness_level * 0.45
    if any(keyword in normalized for keyword in ("it chua", "chua nhe", "dung chua qua")):
        score += (10 - product.sourness_level) * 0.45
    if any(keyword in normalized for keyword in ("ngan sach", "gia", "duoi", "re")):
        score += max(0, 120000 - product.price) / 20000

    return score


def _build_available_products_answer(
    *,
    user_message: str,
    products: list[Product],
    focus_products: list[Product],
) -> str:
    if not products:
        return "Hiện tại kho tạm hết sản phẩm. Bạn quay lại sau ít phút nhé."

    normalized = normalize_text(user_message)
    style_idx = (sum(ord(ch) for ch in normalized) + len(products)) % 3

    if focus_products:
        top = focus_products[0]
        alternatives = [product for product in sorted(products, key=lambda item: _showcase_score(item, user_message), reverse=True) if product.id != top.id][:2]
        ask_more = any(keyword in normalized for keyword in ("them", "goi y", "tham khao", "loai khac", "so sanh"))

        answer = (
            f"Có nhé. Hôm nay {top.name} đang khá ổn: {_product_taste_brief(top)}, "
            f"giá {_format_vnd(top.price)}, còn {top.stock}."
        )

        if ask_more and alternatives:
            alt_names = _join_human_list([product.name for product in alternatives])
            answer += f" Nếu muốn đổi vị, bạn có thể tham khảo thêm {alt_names}."

        if ask_more:
            followups = (
                "Bạn muốn mình chọn thêm bản ngọt hơn hay bản ít chua hơn từ nhóm này không?",
                "Nếu bạn thích, mình lọc tiếp theo ngân sách để chốt nhanh hơn.",
                "Mình có thể chốt luôn 1-2 lựa chọn cùng gu để bạn dễ chọn.",
            )
            return f"{answer} {followups[style_idx]}"

        return answer

    ranked = sorted(products, key=lambda product: _showcase_score(product, user_message), reverse=True)
    highlights = ranked[:4]
    names = _join_human_list([product.name for product in highlights])
    intros = (
        "Mình vừa rà nhanh các mặt hàng đang có và chọn ra nhóm dễ ăn nhất.",
        "Shop đang có vài lựa chọn ngon khá rõ theo tiêu chí bạn hỏi.",
        "Mình lọc nhanh danh sách hôm nay và thấy các lựa chọn sau khá ổn.",
    )

    reasoning = ""
    if "ngon" in normalized:
        reasoning = " Mình ưu tiên nhóm có điểm ngọt-thơm-mọng nước cao hơn."
    elif any(keyword in normalized for keyword in ("gia", "ngan sach", "duoi", "re")):
        reasoning = " Mình ưu tiên các lựa chọn dễ vào ngân sách."

    top = highlights[0]
    detail = f"Gợi ý nổi bật nhất lúc này là {top.name} ({_product_taste_brief(top)}, giá {_format_vnd(top.price)})."

    return (
        f"{intros[style_idx]}{reasoning} Hiện đáng thử: {names}. "
        f"{detail} Bạn muốn mình lọc tiếp theo vị ngọt, độ chua hay mức giá?"
    )


def handle_chat_request(
    payload: ChatRequest,
    *,
    app_state: object,
    db: Session,
    source: str = "/chat",
) -> ChatResponse:
    services = app_state.services
    sync_services_with_inventory(db, services)
    trace_id = str(uuid4())

    log_user_question(
        source=source,
        question=payload.message,
        user_id=payload.user_id,
        session_id=payload.session_id,
        metadata={"language": payload.language, "trace_id": trace_id},
    )

    services.memory_agent.update_from_message(payload.session_id, payload.message)
    route = services.router_agent.route(payload.message)

    products: list[Product] = []
    citations: list[CitationOut] = []
    fallback = False
    recommendation_constraints: dict = {}

    if route.intent == "available_products":
        products = services.inventory_agent.list_available(db, limit=24)
        focus_products = services.inventory_agent.infer_focus_products(db, payload.message, limit=3)

        if not focus_products:
            candidate_name = services.inventory_agent.extract_candidate_name(payload.message)
            if candidate_name:
                focus_products = services.inventory_agent.list_available(db, query=candidate_name, limit=3)

        answer = _build_available_products_answer(
            user_message=payload.message,
            products=products,
            focus_products=focus_products,
        )

        if focus_products:
            focus_ids = {product.id for product in focus_products}
            products = focus_products + [product for product in products if product.id not in focus_ids]
            products = products[:8]

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
        cache_key = f"chat:rec:v5:{normalize_text(payload.message)}"
        cached = semantic_cache.get(cache_key)
        profile = services.memory_agent.get_profile(payload.session_id)
        recommendation_constraints = services.recommendation_agent.parse_preferences(payload.message, profile)

        if cached:
            answer = cached["answer"]
            products = [db.get(Product, product_id) for product_id in cached["product_ids"]]
            products = [product for product in products if product is not None and product.stock > 0]
            citations = [CitationOut(**citation) for citation in cached["citations"]]
        else:
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
                    constraints=recommendation_constraints,
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

    rag_context = _build_rag_context_for_rewrite(citations=citations, products=products)
    allow_follow_up = route.intent not in {"inventory_check"}

    try:
        answer, rewrite_mode = services.response_rewriter.rewrite(
            base_answer=answer,
            user_message=payload.message,
            intent=route.intent,
            session_id=payload.session_id,
            language=payload.language,
            allow_follow_up=allow_follow_up,
            rag_context=rag_context,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    answer, products, repaired = _validate_and_repair_answer(
        intent=route.intent,
        user_message=payload.message,
        answer=answer,
        products=products,
        constraints=recommendation_constraints,
    )
    if repaired:
        rewrite_mode = f"{rewrite_mode}_guard"

    quality_review = {}
    if settings.enable_answer_quality_review:
        quality_review = services.response_rewriter.review_answer_quality(
            question=payload.message,
            answer=answer,
            intent=route.intent,
        )

    log_qa_pair(
        source=source,
        question=payload.message,
        answer=answer,
        user_id=payload.user_id,
        session_id=payload.session_id,
        intent=route.intent,
        confidence=route.confidence,
        metadata={"trace_id": trace_id, "rewrite_mode": rewrite_mode},
        review=quality_review,
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
        metadata_json={
            "trace_id": trace_id,
            "intent": route.intent,
            "fallback": fallback,
            "rewrite_mode": rewrite_mode,
            "quality_score": quality_review.get("score") if isinstance(quality_review, dict) else None,
        },
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


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request, db: Session = Depends(get_db)) -> ChatResponse:
    return handle_chat_request(payload, app_state=request.app.state, db=db)
