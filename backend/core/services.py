from dataclasses import dataclass

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
    router_agent: RouterAgent
    inventory_agent: InventoryAgent
    recommendation_agent: RecommendationAgent
    faq_agent: FAQAgent
    memory_agent: MemoryAgent
    retriever: HybridRetriever
    response_rewriter: ResponseRewriter
    inventory_revision: int = 0


class ServiceFactory:
    @staticmethod
    def build(db: Session) -> ServiceContainer:
        settings = get_settings()
        retriever = HybridRetriever()
        retriever.rebuild_index(db)

        memory_agent = MemoryAgent()
        return ServiceContainer(
            router_agent=RouterAgent(
                use_pretrained_router=settings.use_pretrained_intent_router,
                model_name=settings.pretrained_intent_model_name,
                min_intent_confidence=settings.pretrained_intent_min_confidence,
                local_files_only=not settings.allow_remote_model_download,
            ),
            inventory_agent=InventoryAgent(),
            recommendation_agent=RecommendationAgent(),
            faq_agent=FAQAgent(retriever),
            memory_agent=memory_agent,
            retriever=retriever,
            response_rewriter=ResponseRewriter(
                generation_mode=settings.response_generation_mode,
                llm_enabled=settings.enable_llm_response_rewrite,
                gemini_api_key=settings.gemini_api_key,
                gemini_model_name=settings.gemini_model_name,
                gemini_timeout_seconds=settings.gemini_timeout_seconds,
                gemini_temperature=settings.gemini_temperature,
                lm_studio_base_url=settings.lm_studio_base_url,
                lm_studio_model_name=settings.lm_studio_model_name,
                lm_studio_timeout_seconds=settings.lm_studio_timeout_seconds,
                lm_studio_temperature=settings.lm_studio_temperature,
            ),
            inventory_revision=get_latest_inventory_event_id(db),
        )


def sync_services_with_inventory(db: Session, services: ServiceContainer) -> None:
    latest_revision = get_latest_inventory_event_id(db)
    if latest_revision <= services.inventory_revision:
        return

    services.retriever.rebuild_index(db)
    semantic_cache.invalidate_prefix("chat:")
    semantic_cache.invalidate_prefix("recommend:")
    services.inventory_revision = latest_revision
