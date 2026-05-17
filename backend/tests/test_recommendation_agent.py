from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from typing import Generator

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
def db_session() -> Generator[Session, None, None]:
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


def test_parse_preferences_current_sour_query_overrides_saved_sweet_profile() -> None:
    profile = PreferenceProfile(prefers_sweet=True)
    agent = RecommendationAgent()

    constraints = agent.parse_preferences("Trái chua", profile)

    assert constraints["min_sweetness"] is None
    assert constraints["min_sourness"] is not None
    assert constraints["max_sourness"] is None


def test_recommendation_distinguishes_sweetest_and_sourest_queries(db_session: Session) -> None:
    agent = RecommendationAgent()

    sweet_products, sweet_reason = agent.recommend(
        db_session,
        query="Hôm nay có trái nào ngọt nhất không?",
        profile=PreferenceProfile(),
        explicit_budget=None,
        limit=3,
        retriever=None,
        use_deep_learning=False,
    )
    sour_products, sour_reason = agent.recommend(
        db_session,
        query="Hôm nay có trái nào chua nhất không?",
        profile=PreferenceProfile(prefers_sweet=True),
        explicit_budget=None,
        limit=3,
        retriever=None,
        use_deep_learning=False,
    )

    assert sweet_products
    assert sour_products
    assert "độ ngọt cao" in sweet_reason.lower()
    assert "vị chua rõ" in sour_reason.lower()
    assert sour_products[0].sourness_level >= sweet_products[0].sourness_level


@pytest.mark.parametrize(
    ("query", "expect_min_sweet", "expect_max_sweet", "expect_min_sour", "expect_max_sour"),
    [
        ("không quá ngọt", None, 6, None, None),
        ("đừng ngọt quá", None, 6, None, None),
        ("chua nhẹ thôi", None, None, None, 3),
        ("đừng chua quá", None, None, None, 3),
        ("trái chua", None, None, 4, None),
        ("ngọt nhất", 8, None, None, None),
    ],
)
def test_parse_preferences_negation_and_extreme_phrases(
    query: str,
    expect_min_sweet: int | None,
    expect_max_sweet: int | None,
    expect_min_sour: int | None,
    expect_max_sour: int | None,
) -> None:
    agent = RecommendationAgent()
    constraints = agent.parse_preferences(query, PreferenceProfile(prefers_sweet=True))

    assert constraints["min_sweetness"] == expect_min_sweet
    assert constraints["max_sweetness"] == expect_max_sweet
    assert constraints["min_sourness"] == expect_min_sour
    assert constraints["max_sourness"] == expect_max_sour


def test_recommendation_respects_not_too_sweet_request(db_session: Session) -> None:
    agent = RecommendationAgent()

    products, reason = agent.recommend(
        db_session,
        query="không quá ngọt",
        profile=PreferenceProfile(prefers_sweet=True),
        explicit_budget=None,
        limit=4,
        retriever=None,
        use_deep_learning=False,
    )

    assert products
    assert "độ ngọt vừa phải" in reason.lower()
    assert all(product.sweetness_level <= 6 for product in products)


def test_recommendation_respects_do_not_too_sour_request(db_session: Session) -> None:
    agent = RecommendationAgent()

    products, reason = agent.recommend(
        db_session,
        query="đừng chua quá",
        profile=PreferenceProfile(prefers_sweet=True),
        explicit_budget=None,
        limit=4,
        retriever=None,
        use_deep_learning=False,
    )

    assert products
    assert "vị ít chua" in reason.lower()
    assert all(product.sourness_level <= 3 for product in products)
