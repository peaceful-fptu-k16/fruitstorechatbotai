from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from backend.agents.faq_agent import FAQAgent
from backend.agents.inventory_agent import InventoryAgent
from backend.agents.memory_agent import MemoryAgent
from backend.agents.recommendation_agent import RecommendationAgent
from backend.agents.router_agent import RouterAgent
from backend.core.cache import semantic_cache
from backend.core.config import get_settings
from backend.core.response_rewriter import ResponseRewriter
from backend.database.queries import get_latest_inventory_event_id
from backend.rag.retriever import HybridRetriever


@dataclass
class ServiceContainer:
    """Runtime objects that need to be shared across API requests."""
    router_agent: RouterAgent
    inventory_agent: InventoryAgent
    recommendation_agent: RecommendationAgent
    faq_agent: FAQAgent
    memory_agent: MemoryAgent
    retriever: HybridRetriever
    response_rewriter: ResponseRewriter
    inventory_revision: int = 0

    def ai_runtime_status(self, *, probe_lm_studio: bool = True) -> dict[str, Any]:
        """Describe the required AI runtime for health-aware clients."""
        settings = get_settings()
        router_ready = self.router_agent.semantic_backend is not None
        embedding_ready = self.retriever.supports_deep_learning
        reranker_ready = self.retriever.reranker is not None
        lm_studio = self.response_rewriter.runtime_status(probe=probe_lm_studio)
        ready = router_ready and embedding_ready and reranker_ready and bool(lm_studio["ready"])

        router_model = (
            settings.pretrained_intent_zero_shot_model_name
            if settings.pretrained_intent_router_backend.strip().lower().replace("-", "_")
            in {"zero_shot", "zeroshot"}
            else settings.pretrained_intent_model_name
        )

        return {
            "status": "ready" if ready else "unavailable",
            "ready": ready,
            "required": True,
            "router": {
                "ready": router_ready,
                "backend": settings.pretrained_intent_router_backend,
                "model": router_model,
            },
            "embedding": {
                "ready": embedding_ready,
                "backend": settings.embedding_backend,
                "model": settings.embedding_model_name,
            },
            "reranker": {
                "ready": reranker_ready,
                "model": settings.pretrained_reranker_model_name,
            },
            "lm_studio": lm_studio,
        }


class ServiceFactory:
    """Builds the application service graph from settings and database state."""
    @staticmethod
    def build(db: Session) -> ServiceContainer:
        """Instantiate agents and build the first retrieval index from products/FAQ."""
        settings = get_settings()
        if not settings.use_pretrained_intent_router:
            raise RuntimeError("USE_PRETRAINED_INTENT_ROUTER must be true")
        if settings.embedding_backend.strip().lower() != "sentence_transformers":
            raise RuntimeError("EMBEDDING_BACKEND must be sentence_transformers")
        if not settings.use_pretrained_reranker:
            raise RuntimeError("USE_PRETRAINED_RERANKER must be true")
        if not settings.lm_studio_base_url.strip():
            raise RuntimeError("LM_STUDIO_BASE_URL is required")

        response_rewriter = ResponseRewriter(
            lm_studio_base_url=settings.lm_studio_base_url,
            lm_studio_model_name=settings.lm_studio_model_name,
            lm_studio_timeout_seconds=settings.lm_studio_timeout_seconds,
            lm_studio_temperature=settings.lm_studio_temperature,
        )
        response_rewriter.ensure_ready()

        retriever = HybridRetriever()
        retriever.ensure_ready()
        retriever.rebuild_index(db)

        memory_agent = MemoryAgent()
        return ServiceContainer(
            router_agent=RouterAgent(
                use_pretrained_router=settings.use_pretrained_intent_router,
                require_pretrained_router=True,
                router_backend=settings.pretrained_intent_router_backend,
                model_name=settings.pretrained_intent_model_name,
                zero_shot_model_name=settings.pretrained_intent_zero_shot_model_name,
                min_intent_confidence=settings.pretrained_intent_min_confidence,
                local_files_only=not settings.allow_remote_model_download,
            ),
            inventory_agent=InventoryAgent(),
            recommendation_agent=RecommendationAgent(),
            faq_agent=FAQAgent(retriever, delivery_area_resolver=response_rewriter.resolve_delivery_area),
            memory_agent=memory_agent,
            retriever=retriever,
            response_rewriter=response_rewriter,
            inventory_revision=get_latest_inventory_event_id(db),
        )


def sync_services_with_inventory(db: Session, services: ServiceContainer) -> None:
    """Refresh retriever/cache when admin changes advance the inventory revision."""
    latest_revision = get_latest_inventory_event_id(db)
    if latest_revision <= services.inventory_revision:
        return

    services.retriever.rebuild_index(db)
    semantic_cache.invalidate_prefix("chat:")
    semantic_cache.invalidate_prefix("recommend:")
    services.inventory_revision = latest_revision
