from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.api.mappers import to_product_out
from backend.core.cache import semantic_cache
from backend.core.config import get_settings
from backend.core.services import sync_services_with_inventory
from backend.core.text import normalize_text
from backend.database.models import Product
from backend.database.session import get_db
from backend.observability.query_logger import log_qa_pair, log_user_question
from backend.schemas import RecommendRequest, RecommendResponse

router = APIRouter(tags=["recommend"])
settings = get_settings()


def _format_vnd(price: int) -> str:
    return f"{price:,.0f}".replace(",", ".") + "đ"


def _build_recommend_rag_context(*, query: str, products: list[Product], retriever: object) -> list[str]:
    raw_lines: list[str] = []

    try:
        semantic_results = retriever.semantic_search(query, top_k=3, scope="product")
    except Exception:
        semantic_results = []

    for item in semantic_results:
        if not isinstance(item, dict):
            continue

        snippet = " ".join(str(item.get("text", "")).split())
        if not snippet:
            continue

        metadata = item.get("metadata")
        name = metadata.get("name") if isinstance(metadata, dict) else ""
        score = float(item.get("score", 0.0))

        if isinstance(name, str) and name.strip():
            raw_lines.append(f"RAG {name.strip()}: {snippet} (score {score:.2f})")
        else:
            raw_lines.append(f"RAG: {snippet} (score {score:.2f})")

    for product in products[:4]:
        raw_lines.append(
            f"{product.name}: giá {_format_vnd(product.price)}, còn {product.stock}, "
            f"ngọt {product.sweetness_level}/10, chua {product.sourness_level}/10, "
            f"chất xơ {product.fiber_level}/10, đường {product.sugar_content_level}/10"
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


@router.post("/recommend", response_model=RecommendResponse)
def recommend_products(
    payload: RecommendRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> RecommendResponse:
    services = request.app.state.services
    sync_services_with_inventory(db, services)

    log_user_question(
        source="/recommend",
        question=payload.query,
        user_id=payload.user_id,
        session_id=payload.session_id,
        metadata={"budget": payload.budget, "limit": payload.limit},
    )

    cache_key = f"recommend:v5:{normalize_text(payload.query)}:{payload.budget}:{payload.limit}"
    cached = semantic_cache.get(cache_key)
    if cached:
        products = [db.get(Product, product_id) for product_id in cached["product_ids"]]
        products = [product for product in products if product is not None and product.stock > 0]
        if products:
            rag_context = _build_recommend_rag_context(
                query=payload.query,
                products=products,
                retriever=services.retriever,
            )
            try:
                reasoning, rewrite_mode = services.response_rewriter.rewrite(
                    base_answer=cached["reasoning"],
                    user_message=payload.query,
                    intent="recommendation",
                    session_id=payload.session_id,
                    language="vi",
                    allow_follow_up=False,
                    rag_context=rag_context,
                )
            except RuntimeError as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc

            quality_review = {}
            if settings.enable_answer_quality_review:
                quality_review = services.response_rewriter.review_answer_quality(
                    question=payload.query,
                    answer=reasoning,
                    intent="recommendation",
                )

            log_qa_pair(
                source="/recommend",
                question=payload.query,
                answer=reasoning,
                user_id=payload.user_id,
                session_id=payload.session_id,
                intent="recommendation",
                confidence=None,
                metadata={"cache": True, "rewrite_mode": rewrite_mode},
                review=quality_review,
            )

            return RecommendResponse(
                reasoning=reasoning,
                recommendations=[to_product_out(product) for product in products],
            )

    services.memory_agent.update_from_message(payload.session_id, payload.query)
    profile = services.memory_agent.get_profile(payload.session_id)

    products, reason = services.recommendation_agent.recommend(
        db,
        query=payload.query,
        profile=profile,
        explicit_budget=payload.budget,
        limit=payload.limit,
        retriever=services.retriever,
    )

    semantic_cache.set(
        cache_key,
        {"reasoning": reason, "product_ids": [product.id for product in products]},
        ttl_seconds=120,
    )

    rag_context = _build_recommend_rag_context(
        query=payload.query,
        products=products,
        retriever=services.retriever,
    )

    try:
        reasoning, rewrite_mode = services.response_rewriter.rewrite(
            base_answer=reason,
            user_message=payload.query,
            intent="recommendation",
            session_id=payload.session_id,
            language="vi",
            allow_follow_up=False,
            rag_context=rag_context,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    quality_review = {}
    if settings.enable_answer_quality_review:
        quality_review = services.response_rewriter.review_answer_quality(
            question=payload.query,
            answer=reasoning,
            intent="recommendation",
        )

    log_qa_pair(
        source="/recommend",
        question=payload.query,
        answer=reasoning,
        user_id=payload.user_id,
        session_id=payload.session_id,
        intent="recommendation",
        confidence=None,
        metadata={"cache": False, "rewrite_mode": rewrite_mode},
        review=quality_review,
    )

    return RecommendResponse(
        reasoning=reasoning,
        recommendations=[to_product_out(product) for product in products],
    )
