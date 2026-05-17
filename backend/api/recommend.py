from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.api.mappers import to_product_out
from backend.core.cache import semantic_cache
from backend.core.text import normalize_text
from backend.database.models import Product
from backend.database.session import get_db
from backend.observability.query_logger import log_user_question
from backend.schemas import RecommendRequest, RecommendResponse

router = APIRouter(tags=["recommend"])


@router.post("/recommend", response_model=RecommendResponse)
def recommend_products(
    payload: RecommendRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> RecommendResponse:
    services = request.app.state.services

    log_user_question(
        source="/recommend",
        question=payload.query,
        user_id=payload.user_id,
        session_id=payload.session_id,
        metadata={"budget": payload.budget, "limit": payload.limit},
    )

    cache_key = f"recommend:v4:{normalize_text(payload.query)}:{payload.budget}:{payload.limit}"
    cached = semantic_cache.get(cache_key)
    if cached:
        products = [db.get(Product, product_id) for product_id in cached["product_ids"]]
        products = [product for product in products if product is not None and product.stock > 0]
        if products:
            return RecommendResponse(
                reasoning=cached["reasoning"],
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

    return RecommendResponse(
        reasoning=reason,
        recommendations=[to_product_out(product) for product in products],
    )
