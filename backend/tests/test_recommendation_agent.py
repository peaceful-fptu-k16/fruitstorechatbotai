from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.agents.memory_agent import PreferenceProfile
from backend.agents.recommendation_agent import RecommendationAgent
from backend.database.models import Product
from backend.database.queries import seed_products
from backend.database.session import Base


class DummyRetriever:
    def __init__(self, *, supports_deep_learning: bool, score_by_name: dict[str, float]) -> None:
        self.supports_deep_learning = supports_deep_learning
        self._score_by_name = score_by_name
        self._score_by_id: dict[int, float] = {}

    def bind_products(self, db: Session) -> None:
        for product in db.scalars(select(Product)):
            score = self._score_by_name.get(product.name)
            if score is not None:
                self._score_by_id[product.id] = score

    def semantic_search(self, query: str, *, top_k: int = 5, scope: str | None = None) -> list[dict]:
        _ = query, scope
        ranked = sorted(self._score_by_id.items(), key=lambda item: item[1], reverse=True)[:top_k]
        return [
            {
                "id": f"product:{product_id}",
                "text": "",
                "metadata": {"scope": "product", "product_id": product_id},
                "score": score,
            }
            for product_id, score in ranked
        ]


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        seed_products(db)
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_recommendation_prefers_pretrained_deep_learning_ranking(db_session: Session) -> None:
    retriever = DummyRetriever(
        supports_deep_learning=True,
        score_by_name={
            "Nho Mẫu Đơn": 0.95,
            "Xoài Cát Hòa Lộc": 0.18,
        },
    )
    retriever.bind_products(db_session)

    agent = RecommendationAgent()
    products, reason = agent.recommend(
        db_session,
        query="Mình cần trái cây để biếu",
        profile=PreferenceProfile(),
        explicit_budget=None,
        limit=3,
        retriever=retriever,
    )

    assert products
    assert products[0].name == "Nho Mẫu Đơn"
    assert "khớp ngữ nghĩa" in reason.lower()


def test_recommendation_falls_back_to_existing_model_when_no_dl_model(db_session: Session) -> None:
    retriever = DummyRetriever(
        supports_deep_learning=False,
        score_by_name={
            "Cam Úc": 0.99,
        },
    )
    retriever.bind_products(db_session)

    agent = RecommendationAgent()
    products, reason = agent.recommend(
        db_session,
        query="Gợi ý trái ít hạt",
        profile=PreferenceProfile(),
        explicit_budget=None,
        limit=2,
        retriever=retriever,
    )

    assert products
    assert "khớp khẩu vị" in reason.lower()


def test_recommendation_falls_back_when_dl_has_no_semantic_score(db_session: Session) -> None:
    retriever = DummyRetriever(supports_deep_learning=True, score_by_name={})
    retriever.bind_products(db_session)

    agent = RecommendationAgent()
    products, reason = agent.recommend(
        db_session,
        query="Gợi ý trái ít hạt",
        profile=PreferenceProfile(),
        explicit_budget=None,
        limit=2,
        retriever=retriever,
    )

    assert products
    assert "chấm điểm ổn định" in reason.lower()
    assert "khớp khẩu vị" in reason.lower()
