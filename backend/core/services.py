from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.agents.faq_agent import FAQAgent
from backend.agents.inventory_agent import InventoryAgent
from backend.agents.memory_agent import MemoryAgent
from backend.agents.recommendation_agent import RecommendationAgent
from backend.agents.router_agent import RouterAgent
from backend.core.config import get_settings
from backend.rag.retriever import HybridRetriever


@dataclass
class ServiceContainer:
    router_agent: RouterAgent
    inventory_agent: InventoryAgent
    recommendation_agent: RecommendationAgent
    faq_agent: FAQAgent
    memory_agent: MemoryAgent
    retriever: HybridRetriever


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
        )
