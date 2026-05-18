from backend.agents.router_agent import RouterAgent
from typing import Optional


class DummySemanticBackend:
    def __init__(
        self,
        intent: str,
        confidence: float,
        *,
        candidates: Optional[list[tuple[str, float]]] = None,
    ):
        self.intent = intent
        self.confidence = confidence
        self.candidates = candidates

    def predict_intent(self, message: str):
        return self.intent, self.confidence

    def predict_top_k(self, message: str, *, top_k: int = 3):
        if self.candidates is None:
            return [(self.intent, self.confidence)]
        return self.candidates[:top_k]


def test_router_uses_pretrained_semantic_prediction_when_confident() -> None:
    router = RouterAgent(
        use_pretrained_router=False,
        semantic_backend=DummySemanticBackend(intent="recommendation", confidence=0.88),
        min_intent_confidence=0.55,
    )

    result = router.route("Xin chào")

    assert result.intent == "recommendation"
    assert result.reason == "pretrained_semantic_router"
    assert result.confidence == 0.88


def test_router_falls_back_to_rules_when_semantic_confidence_low() -> None:
    router = RouterAgent(
        use_pretrained_router=False,
        semantic_backend=DummySemanticBackend(intent="faq_shipping", confidence=0.20),
        min_intent_confidence=0.55,
    )

    result = router.route("Shop giao hàng trong bao lâu?")

    assert result.intent == "faq_shipping"
    assert result.reason == "keyword_match"


def test_router_guard_avoids_out_of_domain_for_in_domain_query() -> None:
    router = RouterAgent(
        use_pretrained_router=False,
        semantic_backend=DummySemanticBackend(
            intent="out_of_domain",
            confidence=0.84,
            candidates=[
                ("out_of_domain", 0.84),
                ("recommendation", 0.63),
                ("available_products", 0.59),
            ],
        ),
        min_intent_confidence=0.55,
    )

    result = router.route("Nho hôm nay có ngọt không?")

    assert result.intent == "recommendation"
    assert result.reason == "pretrained_semantic_router_guard"
    assert result.confidence == 0.63


def test_router_keeps_out_of_domain_when_query_is_truly_unrelated() -> None:
    router = RouterAgent(
        use_pretrained_router=False,
        semantic_backend=DummySemanticBackend(
            intent="out_of_domain",
            confidence=0.78,
            candidates=[
                ("out_of_domain", 0.78),
                ("recommendation", 0.44),
            ],
        ),
        min_intent_confidence=0.55,
    )

    result = router.route("Giải phương trình bậc hai giúp mình")

    assert result.intent == "out_of_domain"
    assert result.reason == "pretrained_semantic_router"
    assert result.confidence == 0.78


def test_router_maps_generic_fruit_catalog_question_to_available_products() -> None:
    router = RouterAgent(
        use_pretrained_router=False,
        semantic_backend=DummySemanticBackend(intent="out_of_domain", confidence=0.88, candidates=[("out_of_domain", 0.88)]),
        min_intent_confidence=0.55,
    )

    result = router.route("Hôm nay có quả gì?")

    assert result.intent == "available_products"
    assert result.reason in {"catalog_heuristic", "pretrained_semantic_router_guard"}


def test_router_maps_fruit_availability_question_to_inventory_check() -> None:
    router = RouterAgent(
        use_pretrained_router=False,
        semantic_backend=DummySemanticBackend(intent="out_of_domain", confidence=0.9, candidates=[("out_of_domain", 0.9)]),
        min_intent_confidence=0.55,
    )

    result = router.route("Cửa hàng mình có chuối không?")

    assert result.intent == "inventory_check"
    assert result.reason == "entity_inventory_heuristic"
