from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Optional, Protocol

import numpy as np

from backend.core.fruit_aliases import FRUIT_ALIASES, fruit_alias_optional_context_pattern, has_fruit_alias
from backend.core.text import normalize_text
from backend.rag.embeddings import SentenceTransformerEmbeddingModel
from backend.schemas import IntentResult

logger = logging.getLogger(__name__)

SUPPORTED_INTENTS: set[str] = {
    "greeting",
    "available_products",
    "price_general",
    "inventory_check",
    "recommendation",
    "order_support",
    "faq_shipping",
    "faq_return",
    "faq_storage",
    "admin_update_stock",
    "out_of_domain",
}

INTENT_SEMANTIC_HINTS: dict[str, tuple[str, ...]] = {
    "greeting": (
        "Xin chao shop",
        "Hello ban oi",
        "Alo shop oi",
        "Chao buoi sang",
        "Hi shop",
    ),
    "available_products": (
        "Hôm nay shop có những trái cây nào?",
        "Danh sách sản phẩm đang bán là gì?",
        "Có những loại quả nào hiện có?",
        "Hôm nay có những sản phẩm nào?",
        "Shop đang bán những loại trái cây nào?",
        "Cho mình xem các mặt hàng đang có.",
        "Có cam, xoài, nho hay bưởi không?",
        "Trong kho đang còn các loại quả gì?",
    ),
    "inventory_check": (
        "Cam còn hàng không?",
        "Kiểm tra tồn kho sản phẩm",
        "Nho Mẫu Đơn còn trong kho không?",
        "Xoài Cát Hòa Lộc còn bao nhiêu?",
        "Mặt hàng này còn hàng không?",
        "Bưởi Da Xanh còn không?",
        "Sản phẩm này đã hết hàng chưa?",
    ),
    "price_general": (
        "Gia bao nhieu?",
        "Bao nhieu tien?",
        "Muc gia hien tai la sao?",
        "Tam bao gia giup minh",
        "Day la gia cho 1 qua hay 1kg?",
    ),
    "recommendation": (
        "Gợi ý giúp tôi trái cây phù hợp",
        "Tư vấn trái cây ít chua và ngọt",
        "Nên mua loại nào theo ngân sách?",
        "Nho hôm nay có ngọt không?",
        "Nho hom nay co ngot khong?",
        "Trái nào ngọt nhất hôm nay?",
        "Trai nao ngot nhat hom nay?",
        "Gợi ý trái ít chua dưới 100 nghìn.",
        "Goi y trai it chua duoi 100k.",
        "Có loại nào ít hạt, dễ ăn không?",
        "Mình nên chọn loại nào để biếu?",
        "Tôi đang ăn kiêng, nên chọn trái cây nào ít đường?",
        "Có trái cây nào mọng nước, nhiều vitamin C không?",
        "Gợi ý trái cây giòn để ăn vặt buổi chiều.",
        "Tư vấn trái cây nhiều chất xơ, hỗ trợ tiêu hóa.",
        "Mình muốn loại thơm, mềm, dễ ăn cho người lớn tuổi.",
    ),
    "faq_shipping": (
        "Shop giao hàng trong bao lâu?",
        "Phí vận chuyển tính như thế nào?",
        "Ship nội thành mất bao nhiêu thời gian?",
        "Ship mất bao lâu?",
        "Nội thành giao trong mấy giờ?",
        "Giao ngoại thành mất mấy ngày?",
        "Có giao nhanh trong ngày không?",
    ),
    "faq_return": (
        "Chính sách đổi trả ra sao?",
        "Nếu sản phẩm lỗi có được hoàn tiền không?",
        "Điều kiện đổi trả của shop là gì?",
        "Hàng lỗi có đổi được không?",
        "Nếu trái cây dập thì hoàn tiền thế nào?",
        "Mình muốn trả hàng thì làm sao?",
        "Shop có hỗ trợ refund không?",
    ),
    "faq_storage": (
        "Bảo quản trái cây như thế nào?",
        "Nên để trái cây trong tủ lạnh bao lâu?",
        "Giữ trái cây tươi lâu bằng cách nào?",
        "Cam, nho nên bảo quản ra sao?",
        "Có nên để xoài ngoài nhiệt độ phòng không?",
        "Nhiệt độ bảo quản phù hợp là bao nhiêu?",
        "Làm sao để trái cây lâu hỏng hơn?",
    ),
    "order_support": (
        "Dat hang nhu the nao?",
        "Huong dan cach dat mua",
        "Toi muon dat don thi lam gi",
        "Mua hang tren chat nay sao day",
        "Chot don va giao hang giup minh",
    ),
    "admin_update_stock": (
        "Admin cập nhật tồn kho",
        "Cách update stock bằng token admin",
        "Tôi muốn chỉnh số lượng hàng trong kho",
        "Hướng dẫn tăng giảm tồn kho sản phẩm",
        "API cập nhật kho cho quản trị viên",
        "Admin muốn cập nhật số lượng hàng",
    ),
    "out_of_domain": (
        "Thời tiết hôm nay như thế nào?",
        "Giúp tôi đặt vé máy bay",
        "Tin tức bóng đá hôm nay",
        "Kể một câu chuyện cười đi.",
        "Giải giúp tôi bài toán đạo hàm.",
        "Viết email xin nghỉ phép.",
        "Gợi ý địa điểm du lịch cuối tuần.",
    ),
}

IN_DOMAIN_GUARD_KEYWORDS: tuple[str, ...] = (
    "trai",
    "trai cay",
    "qua",
    "shop",
    "san pham",
    "mat hang",
    "goi y",
    "tu van",
    "ngot",
    "it chua",
    "it hat",
    "it duong",
    "an kieng",
    "giam can",
    "chat xo",
    "vitamin c",
    "mong nuoc",
    "gion",
    "thom",
    "ep nuoc",
    "salad",
    "ngan sach",
    "gia",
    "duoi",
    "cam",
    "xoai",
    "nho",
    "buoi",
    "ton kho",
    "con hang",
    "het hang",
    "ship",
    "giao",
    "van chuyen",
    "doi tra",
    "hoan tien",
    "bao quan",
    "tu lanh",
    "co qua gi",
    "co trai gi",
    "hom nay co qua gi",
    "hom nay co loai qua gi",
    "hom nay co trai gi",
    "shop co gi hom nay",
    "cua hang co gi hom nay",
    "co chuoi khong",
    "cherry",
    "gia cho 1 qua",
    "1 kg",
    "1kg",
    "qua do",
    "qua nay",
    "dat hang",
    "doi hang",
)

FRUIT_ENTITY_KEYWORDS: tuple[str, ...] = FRUIT_ALIASES

REFERENTIAL_CONTEXT_KEYWORDS: tuple[str, ...] = (
    "qua do",
    "trai do",
    "san pham do",
    "loai do",
    "mon do",
    "gia do",
    "gia nay",
    "gia kia",
    "loai nay",
    "san pham nay",
    "day la gia",
)

PREFERENCE_GUARD_KEYWORDS: tuple[str, ...] = (
    "ngot",
    "it chua",
    "it hat",
    "it duong",
    "an kieng",
    "chat xo",
    "vitamin c",
    "mong nuoc",
    "gion",
    "thom",
    "goi y",
    "tu van",
    "nen mua",
    "phu hop",
)

INTENT_ZERO_SHOT_LABELS: dict[str, str] = {
    "greeting": "loi chao mo dau hoi tham shop",
    "available_products": "hoi danh sach trai cay dang ban tai shop",
    "price_general": "hoi thong tin gia chung chua ro san pham",
    "inventory_check": "hoi gia hoac ton kho cua san pham cu the",
    "recommendation": "xin goi y va tu van chon trai cay",
    "order_support": "hoi cach dat hang va chot don",
    "faq_shipping": "hoi giao hang va van chuyen",
    "faq_return": "hoi doi tra va hoan tien",
    "faq_storage": "hoi bao quan trai cay",
    "admin_update_stock": "yeu cau cap nhat ton kho boi admin",
    "out_of_domain": "khong lien quan den shop trai cay",
}


@dataclass
class Rule:
    intent: str
    keywords: tuple[str, ...]
    confidence: float


class SemanticIntentBackend(Protocol):
    def predict_intent(self, message: str) -> Optional[tuple[str, float]]:
        ...


class PretrainedSemanticIntentBackend:
    def __init__(
        self,
        *,
        model_name: str = "BAAI/bge-m3",
        local_files_only: bool = True,
    ) -> None:
        self.embedding_model = SentenceTransformerEmbeddingModel(
            model_name=model_name,
            local_files_only=local_files_only,
        )
        self.intent_labels: list[str] = []
        self.intent_matrix = self._build_intent_matrix()

    def _build_intent_matrix(self) -> np.ndarray:
        vectors: list[np.ndarray] = []
        labels: list[str] = []

        for intent, hints in INTENT_SEMANTIC_HINTS.items():
            hint_vectors = self.embedding_model.embed_batch(list(hints))
            if hint_vectors.size == 0:
                continue

            centroid = np.mean(hint_vectors, axis=0)
            norm = float(np.linalg.norm(centroid))
            if norm > 0.0:
                centroid = centroid / norm

            labels.append(intent)
            vectors.append(centroid.astype(np.float32))

        self.intent_labels = labels
        if not vectors:
            return np.zeros((0, self.embedding_model.dim), dtype=np.float32)
        return np.vstack(vectors)

    def predict_top_k(self, message: str, *, top_k: int = 3) -> list[tuple[str, float]]:
        if self.intent_matrix.size == 0 or not self.intent_labels:
            return []

        query_vector = self.embedding_model.embed_text(message)
        if float(np.linalg.norm(query_vector)) == 0.0:
            return []

        scores = self.intent_matrix @ query_vector
        ordered_indices = np.argsort(scores)[::-1]
        chosen_indices = ordered_indices[: max(1, top_k)]
        return [(self.intent_labels[int(idx)], float(scores[int(idx)])) for idx in chosen_indices]

    def predict_intent(self, message: str) -> Optional[tuple[str, float]]:
        top = self.predict_top_k(message, top_k=1)
        if not top:
            return None
        return top[0]


class ZeroShotIntentBackend:
    def __init__(
        self,
        *,
        model_name: str = "joeddav/xlm-roberta-large-xnli",
        local_files_only: bool = True,
    ) -> None:
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("transformers is not available") from exc

        tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=local_files_only, use_fast=False)
        model = AutoModelForSequenceClassification.from_pretrained(model_name, local_files_only=local_files_only)
        self._classifier = pipeline(
            "zero-shot-classification",
            model=model,
            tokenizer=tokenizer,
        )
        self._candidate_labels = [INTENT_ZERO_SHOT_LABELS[intent] for intent in SUPPORTED_INTENTS]
        self._label_to_intent = {label: intent for intent, label in INTENT_ZERO_SHOT_LABELS.items()}

    def predict_top_k(self, message: str, *, top_k: int = 3) -> list[tuple[str, float]]:
        result = self._classifier(
            message,
            candidate_labels=self._candidate_labels,
            hypothesis_template="Noi dung nay thuoc y dinh: {}.",
            multi_label=False,
        )

        labels = result.get("labels") or []
        scores = result.get("scores") or []
        candidates: list[tuple[str, float]] = []
        for label, score in zip(labels, scores):
            intent = self._label_to_intent.get(str(label))
            if intent is None:
                continue
            candidates.append((intent, float(score)))

        return candidates[: max(1, top_k)]

    def predict_intent(self, message: str) -> Optional[tuple[str, float]]:
        top = self.predict_top_k(message, top_k=1)
        if not top:
            return None
        return top[0]


class RouterAgent:
    @staticmethod
    def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _has_fruit_entity(text: str) -> bool:
        return has_fruit_alias(text, aliases=FRUIT_ENTITY_KEYWORDS)

    @staticmethod
    def _has_direct_entity_stock_question(text: str) -> bool:
        return any(
            re.search(rf"\bco\s+{fruit_alias_optional_context_pattern(entity)}\s+khong\b", text) is not None
            for entity in FRUIT_ENTITY_KEYWORDS
        )

    def __init__(
        self,
        *,
        use_pretrained_router: bool = True,
        model_name: str = "BAAI/bge-m3",
        router_backend: str = "zero_shot",
        zero_shot_model_name: str = "joeddav/xlm-roberta-large-xnli",
        min_intent_confidence: float = 0.55,
        local_files_only: bool = True,
        semantic_backend: Optional[SemanticIntentBackend] = None,
    ) -> None:
        self.semantic_backend: Optional[SemanticIntentBackend] = semantic_backend
        self.router_backend = router_backend
        self.zero_shot_model_name = zero_shot_model_name
        self.min_intent_confidence = min_intent_confidence
        self.local_files_only = local_files_only

        self.rules: tuple[Rule, ...] = (
            Rule(
                intent="order_support",
                keywords=(
                    "dat hang",
                    "dat don",
                    "chot don",
                    "mua hang",
                    "cach mua",
                    "huong dan dat",
                ),
                confidence=0.92,
            ),
            Rule(
                intent="faq_shipping",
                keywords=(
                    "ship",
                    "giao",
                    "delivery",
                    "van chuyen",
                    "bao lau",
                    "phi ship",
                    "mien phi ship",
                    "cod",
                    "noi thanh",
                    "ngoai thanh",
                ),
                confidence=0.93,
            ),
            Rule(
                intent="faq_return",
                keywords=(
                    "doi tra",
                    "doi hang",
                    "refund",
                    "hoan tien",
                    "bao hanh",
                    "hang dap",
                    "bi dap",
                    "hang hong",
                    "sai don",
                ),
                confidence=0.92,
            ),
            Rule(
                intent="faq_storage",
                keywords=("bao quan", "de tu lanh", "storage", "giu tuoi", "de ngoai", "nhiet do", "bao lau thi hong"),
                confidence=0.92,
            ),
            Rule(
                intent="admin_update_stock",
                keywords=("admin", "update stock", "cap nhat kho", "restock"),
                confidence=0.90,
            ),
            Rule(
                intent="inventory_check",
                keywords=("con hang", "con", "stock", "ton", "het hang"),
                confidence=0.86,
            ),
            Rule(
                intent="recommendation",
                keywords=(
                    "goi y",
                    "ngot",
                    "it chua",
                    "nen mua",
                    "recommend",
                    "de xuat",
                    "phu hop",
                    "budget",
                    "it duong",
                    "an kieng",
                    "chat xo",
                    "vitamin c",
                    "mong nuoc",
                    "gion",
                    "thom",
                    "so sanh",
                    "khac nhau",
                    "nen chon",
                    "loai nao",
                    "cho be",
                    "tre em",
                    "nguoi lon tuoi",
                    "nguoi gia",
                    "tieu duong",
                    "gia re",
                    "tam gia",
                    "duoi",
                    "bieu",
                    "qua tang",
                ),
                confidence=0.89,
            ),
            Rule(
                intent="available_products",
                keywords=("hom nay co gi", "co gi", "san pham", "danh sach", "available"),
                confidence=0.80,
            ),
        )

        if self.semantic_backend is None and use_pretrained_router:
            self.semantic_backend = self._build_pretrained_backend(
                model_name=model_name,
                router_backend=router_backend,
                zero_shot_model_name=zero_shot_model_name,
            )

    def _build_pretrained_backend(
        self,
        *,
        model_name: str,
        router_backend: str,
        zero_shot_model_name: str,
    ) -> Optional[SemanticIntentBackend]:
        normalized_backend = normalize_text(router_backend).replace("-", "_")
        try:
            if normalized_backend in {"zero_shot", "zeroshot"}:
                return ZeroShotIntentBackend(
                    model_name=zero_shot_model_name,
                    local_files_only=self.local_files_only,
                )
            return PretrainedSemanticIntentBackend(model_name=model_name, local_files_only=self.local_files_only)
        except Exception as exc:
            # Fall back to deterministic rules if pretrained model cannot be loaded.
            logger.warning("Pretrained router (%s) disabled due to load failure: %s", normalized_backend, exc)
            return None

    def _has_in_domain_signal(self, normalized_message: str) -> bool:
        tokens = set(re.findall(r"\w+", normalized_message))
        for keyword in IN_DOMAIN_GUARD_KEYWORDS:
            if " " in keyword:
                if keyword in normalized_message:
                    return True
                continue

            if keyword in tokens:
                return True

        return False

    def _predict_semantic_candidates(self, message: str, *, top_k: int = 3) -> list[tuple[str, float]]:
        if self.semantic_backend is None:
            return []

        predict_top_k = getattr(self.semantic_backend, "predict_top_k", None)
        if callable(predict_top_k):
            try:
                raw_candidates = predict_top_k(message, top_k=top_k)
            except TypeError:
                raw_candidates = predict_top_k(message)
            except Exception:
                raw_candidates = []

            candidates: list[tuple[str, float]] = []
            for item in raw_candidates:
                if not isinstance(item, tuple) or len(item) != 2:
                    continue
                intent, score = item
                intent = str(intent)
                if intent in SUPPORTED_INTENTS:
                    candidates.append((intent, float(score)))

            if candidates:
                return candidates[:top_k]

        try:
            prediction = self.semantic_backend.predict_intent(message)
        except Exception:
            return []

        if prediction is None:
            return []

        predicted_intent, confidence = prediction
        if predicted_intent not in SUPPORTED_INTENTS:
            return []

        return [(predicted_intent, float(confidence))]

    def _route_with_pretrained_router(self, message: str) -> Optional[IntentResult]:
        candidates = self._predict_semantic_candidates(message, top_k=5)
        if not candidates:
            return None

        predicted_intent, confidence = candidates[0]
        normalized_message = normalize_text(message)

        if self._has_direct_entity_stock_question(normalized_message):
            return IntentResult(intent="inventory_check", confidence=0.82, reason="pretrained_entity_stock_guard")

        if predicted_intent == "out_of_domain":
            if self._has_in_domain_signal(normalized_message):
                guard_floor = max(0.45, self.min_intent_confidence - 0.08)

                if any(keyword in normalized_message for keyword in PREFERENCE_GUARD_KEYWORDS):
                    for alt_intent, alt_score in candidates[1:]:
                        if alt_intent == "recommendation" and alt_score >= max(0.34, guard_floor - 0.16):
                            return IntentResult(
                                intent="recommendation",
                                confidence=float(alt_score),
                                reason="pretrained_semantic_router_guard",
                            )

                for alt_intent, alt_score in candidates[1:]:
                    if alt_intent == "out_of_domain":
                        continue
                    if alt_score >= guard_floor:
                        return IntentResult(
                            intent=alt_intent,
                            confidence=float(alt_score),
                            reason="pretrained_semantic_router_guard",
                        )
                return None

        if confidence < self.min_intent_confidence:
            return None

        return IntentResult(
            intent=predicted_intent,
            confidence=float(confidence),
            reason="pretrained_semantic_router",
        )

    def route(self, user_message: str) -> IntentResult:
        pretrained_result = self._route_with_pretrained_router(user_message)
        if pretrained_result is not None:
            return pretrained_result

        message = normalize_text(user_message)
        has_fruit_entity = self._has_fruit_entity(message)

        greeting_patterns = ("hello", "xin chao", "chao shop", "alo", "helo")
        if self._contains_any(message, greeting_patterns):
            return IntentResult(intent="greeting", confidence=0.88, reason="greeting_in_domain")

        price_question_patterns = (
            "gia bao nhieu",
            "bao nhieu tien",
            "bao nhieu",
            "nhieu tien",
            "may tien",
            "gia cua",
            "gia 1kg",
            "bao nhieu 1kg",
            "bao nhieu mot kg",
        )
        budget_filter_patterns = ("duoi", "tren", "ngan sach", "tam gia", "gia re", "khong qua", "toi da")
        asks_product_price = self._contains_any(message, price_question_patterns) or (
            "gia" in message and not self._contains_any(message, budget_filter_patterns)
        )
        if asks_product_price and self._contains_any(message, REFERENTIAL_CONTEXT_KEYWORDS):
            return IntentResult(intent="inventory_check", confidence=0.72, reason="referential_price_heuristic")

        if asks_product_price and not has_fruit_entity:
            return IntentResult(intent="price_general", confidence=0.84, reason="generic_price_heuristic")

        if self._contains_any(message, ("dat hang", "dat don", "chot don", "mua hang", "cach dat")):
            return IntentResult(intent="order_support", confidence=0.90, reason="order_support_heuristic")

        unit_clarification_patterns = (
            "gia cho 1 qua",
            "gia cho 1 kg",
            "gia cho 1kg",
            "1 qua hay 1 kg",
            "1 qua hay 1kg",
            "1kg hay 1 qua",
            "1 kg hay 1 qua",
        )
        if self._contains_any(message, unit_clarification_patterns):
            return IntentResult(intent="inventory_check", confidence=0.80, reason="price_unit_heuristic")

        if has_fruit_entity and asks_product_price:
            return IntentResult(intent="inventory_check", confidence=0.86, reason="entity_price_heuristic")

        comparison_patterns = ("so sanh", "khac nhau", "nen chon", "loai nao ngon hon", "loai nao hop hon")
        if self._contains_any(message, comparison_patterns):
            return IntentResult(intent="recommendation", confidence=0.86, reason="comparison_heuristic")

        advisory_patterns = (
            "goi y",
            "tu van",
            "nen mua",
            "phu hop",
            "duoi",
            "tren",
            "ngan sach",
            "tam gia",
            "gia re",
            "it duong",
            "an kieng",
            "giam can",
            "tieu duong",
            "cho be",
            "tre em",
            "nguoi lon tuoi",
            "nguoi gia",
            "bieu",
            "qua tang",
            "ngon",
        )
        if self._contains_any(message, advisory_patterns):
            return IntentResult(intent="recommendation", confidence=0.84, reason="advisory_heuristic")

        if has_fruit_entity and self._contains_any(message, ("ngon", "ngot", "chua", "thom", "gion", "de an")):
            return IntentResult(intent="recommendation", confidence=0.82, reason="entity_taste_heuristic")

        if any(
            phrase in message
            for phrase in (
                "hom nay co qua gi",
                "hom nay co loai qua gi",
                "hom nay co trai gi",
                "shop co gi hom nay",
                "cua hang co gi hom nay",
                "co qua gi",
                "co trai gi",
                "dang co gi",
                "menu",
                "danh sach",
                "con loai nao",
                "dang ban gi",
            )
        ):
            return IntentResult(intent="available_products", confidence=0.78, reason="catalog_heuristic")

        explicit_inventory_patterns = (
            "con hang",
            "con khong",
            "het hang",
            "ton kho",
            "con bao nhieu",
            "co ban khong",
        )
        has_direct_entity_stock_question = self._has_direct_entity_stock_question(message)
        if has_direct_entity_stock_question or any(pattern in message for pattern in explicit_inventory_patterns):
            return IntentResult(intent="inventory_check", confidence=0.82, reason="entity_inventory_heuristic")

        for rule in self.rules:
            if any(keyword in message for keyword in rule.keywords):
                return IntentResult(intent=rule.intent, confidence=rule.confidence, reason="keyword_match")

        if has_fruit_entity and any(
            keyword in message for keyword in ("mua", "goi y", "tu van", "nen mua")
        ):
            return IntentResult(intent="recommendation", confidence=0.74, reason="entity_recommend_heuristic")

        if any(token in message for token in ("ngot", "chua", "mem", "hat", "mua")):
            return IntentResult(intent="recommendation", confidence=0.68, reason="preference_heuristic")

        return IntentResult(intent="out_of_domain", confidence=0.42, reason="no_match")
