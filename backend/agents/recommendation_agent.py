from __future__ import annotations

import re
from typing import Any, Optional

from sqlalchemy import asc, select
from sqlalchemy.orm import Session

from backend.agents.memory_agent import PreferenceProfile
from backend.core.text import normalize_text
from backend.database.models import Product
from backend.rag.embeddings import SentenceTransformerEmbeddingModel


class RecommendationAgent:
    @staticmethod
    def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in text for keyword in keywords)

    def _extract_budget(self, normalized_query: str) -> Optional[int]:
        matches = re.findall(r"(\d+)\s*(k|nghin|ngan|trieu)?", normalized_query)
        for number_text, suffix in matches:
            value = int(number_text)
            if suffix in {"k", "nghin", "ngan"}:
                value *= 1000
            elif suffix == "trieu":
                value *= 1_000_000

            if value >= 1000:
                return value
        return None

    def parse_preferences(self, query: str, profile: PreferenceProfile) -> dict:
        normalized = normalize_text(query)

        prefers_low_sugar = self._contains_any(normalized, ("it duong", "an kieng", "giam can", "keto")) or bool(
            profile.prefers_low_sugar
        )
        prefers_high_fiber = self._contains_any(normalized, ("chat xo", "tieu hoa", "no lau")) or bool(
            profile.prefers_high_fiber
        )
        prefers_high_vitamin_c = self._contains_any(normalized, ("vitamin c", "de khang", "dep da")) or bool(
            profile.prefers_high_vitamin_c
        )

        preferred_texture = profile.preferred_texture
        if self._contains_any(normalized, ("gion", "gion rum", "do gion")):
            preferred_texture = "giòn"
        elif self._contains_any(normalized, ("mem", "de an", "de nhai")):
            preferred_texture = "mềm"

        preferred_use = None
        if self._contains_any(normalized, ("ep nuoc", "nuoc ep", "sinh to", "smoothie")):
            preferred_use = "Ép nước"
        elif self._contains_any(normalized, ("salad", "detox", "an kieng")):
            preferred_use = "Ăn kiêng"
        elif self._contains_any(normalized, ("an vat", "trang mieng", "bieu")):
            preferred_use = "Ăn tươi"

        constraints: dict = {
            "min_sweetness": 7 if ("ngot" in normalized or profile.prefers_sweet) else None,
            "max_sourness": 3 if ("it chua" in normalized or profile.prefers_low_sour) else None,
            "max_seed": 3 if ("it hat" in normalized or profile.prefers_low_seed) else None,
            "min_juiciness": 7
            if (self._contains_any(normalized, ("mong nuoc", "nhieu nuoc", "giai nhiet", "ep nuoc")) or profile.prefers_juicy)
            else None,
            "min_aroma": 7 if (self._contains_any(normalized, ("thom", "mui thom")) or profile.prefers_aromatic) else None,
            "min_crunchiness": 7
            if (self._contains_any(normalized, ("gion", "gion rum", "do gion")) or profile.prefers_crunchy)
            else None,
            "min_fiber": 7 if prefers_high_fiber else None,
            "min_vitamin_c": 7 if prefers_high_vitamin_c else None,
            "max_sugar": 5 if prefers_low_sugar else None,
            "max_calories": 60 if prefers_low_sugar else None,
            "preferred_texture": preferred_texture,
            "preferred_use": preferred_use,
        }

        budget = self._extract_budget(normalized)
        constraints["budget"] = budget or profile.budget_hint
        return constraints

    def _parse_preferences(self, query: str, profile: PreferenceProfile) -> dict:
        return self.parse_preferences(query, profile)

    def _supports_deep_learning(self, retriever: Any) -> bool:
        if retriever is None:
            return False

        if bool(getattr(retriever, "supports_deep_learning", False)):
            return True

        embedding_model = getattr(retriever, "embedding_model", None)
        return isinstance(embedding_model, SentenceTransformerEmbeddingModel)

    def _preference_score(self, product: Product, *, constraints: dict, budget: Optional[int]) -> float:
        score_parts: list[float] = []

        if constraints["min_sweetness"] is not None:
            score_parts.append(float(product.sweetness_level) / 10.0)

        if constraints["max_sourness"] is not None:
            score_parts.append((10.0 - float(product.sourness_level)) / 10.0)

        if constraints["max_seed"] is not None:
            score_parts.append((10.0 - float(product.seed_level)) / 10.0)

        if constraints["min_juiciness"] is not None:
            score_parts.append(float(product.juiciness_level) / 10.0)

        if constraints["min_aroma"] is not None:
            score_parts.append(float(product.aroma_level) / 10.0)

        if constraints["min_crunchiness"] is not None:
            score_parts.append(float(product.crunchiness_level) / 10.0)

        if constraints["min_fiber"] is not None:
            score_parts.append(float(product.fiber_level) / 10.0)

        if constraints["min_vitamin_c"] is not None:
            score_parts.append(float(product.vitamin_c_level) / 10.0)

        if constraints["max_sugar"] is not None:
            score_parts.append((10.0 - float(product.sugar_content_level)) / 10.0)

        max_calories = constraints.get("max_calories")
        if max_calories is not None and max_calories > 0:
            if product.calories_per_100g <= max_calories:
                calories_score = max(0.3, 1.0 - (float(product.calories_per_100g) / float(max_calories)) * 0.2)
            else:
                overshoot = float(product.calories_per_100g - max_calories) / float(max_calories)
                calories_score = max(0.0, 1.0 - overshoot)
            score_parts.append(calories_score)

        preferred_texture = constraints.get("preferred_texture")
        if preferred_texture:
            texture_score = 1.0 if normalize_text(preferred_texture) in normalize_text(product.texture) else 0.35
            score_parts.append(texture_score)

        preferred_use = constraints.get("preferred_use")
        if preferred_use:
            use_score = 1.0 if normalize_text(preferred_use) in normalize_text(product.best_use) else 0.40
            score_parts.append(use_score)

        if budget is not None and budget > 0:
            if product.price <= budget:
                budget_score = max(0.2, 1.0 - (float(product.price) / float(budget)) * 0.25)
            else:
                overshoot = float(product.price - budget) / float(budget)
                budget_score = max(0.0, 1.0 - overshoot)
            score_parts.append(budget_score)

        if not score_parts:
            return max(0.0, float(product.sweetness_level - product.sourness_level) / 10.0)

        return sum(score_parts) / float(len(score_parts))

    def _rank_with_deep_learning(
        self,
        retriever: Any,
        *,
        query: str,
        candidates: list[Product],
        constraints: dict,
        budget: Optional[int],
    ) -> list[Product]:
        if not candidates:
            return []

        top_k = max(len(candidates) * 3, 30)

        try:
            semantic_results = retriever.semantic_search(query, top_k=top_k, scope="product")
        except Exception:
            return []

        score_by_id: dict[int, float] = {}
        for item in semantic_results:
            metadata = item.get("metadata") if isinstance(item, dict) else None
            if not isinstance(metadata, dict):
                continue

            product_id = metadata.get("product_id")
            if not isinstance(product_id, int):
                continue

            raw_score = float(item.get("score", 0.0))
            semantic_score = max(0.0, raw_score)
            score_by_id[product_id] = max(score_by_id.get(product_id, 0.0), semantic_score)

        if not score_by_id:
            return []

        if all(score_by_id.get(product.id, 0.0) <= 0.0 for product in candidates):
            return []

        ranked = sorted(
            candidates,
            key=lambda product: (
                score_by_id.get(product.id, 0.0) * 0.78
                + self._preference_score(product, constraints=constraints, budget=budget) * 0.22,
                score_by_id.get(product.id, 0.0),
                product.sweetness_level - product.sourness_level,
                -product.price,
            ),
            reverse=True,
        )
        return ranked

    def _build_reason(self, *, constraints: dict, used_deep_learning: bool, fallback_note: Optional[str] = None) -> str:
        traits: list[str] = []
        if constraints.get("min_sweetness") is not None:
            traits.append("độ ngọt cao")
        if constraints.get("max_sourness") is not None:
            traits.append("vị ít chua")
        if constraints.get("max_seed") is not None:
            traits.append("ít hạt")
        if constraints.get("min_juiciness") is not None:
            traits.append("mọng nước")
        if constraints.get("min_aroma") is not None:
            traits.append("mùi thơm rõ")
        if constraints.get("min_crunchiness") is not None:
            traits.append("độ giòn tốt")
        if constraints.get("min_fiber") is not None:
            traits.append("nhiều chất xơ")
        if constraints.get("min_vitamin_c") is not None:
            traits.append("giàu vitamin C")
        if constraints.get("max_sugar") is not None:
            traits.append("đường tự nhiên thấp")
        if constraints.get("budget") is not None:
            traits.append(f"ngân sách dưới {int(constraints['budget']):,}đ".replace(",", "."))

        if traits:
            reason = f"Tiêu chí xếp hạng chính: {', '.join(traits)}."
        else:
            reason = "Mình ưu tiên mức độ phù hợp tổng thể theo khẩu vị và mục đích dùng của bạn."

        if used_deep_learning:
            reason += " Mình ưu tiên độ khớp ngữ nghĩa để câu trả lời tự nhiên hơn."
        else:
            reason += " Mình ưu tiên độ khớp khẩu vị và bối cảnh sử dụng của bạn."

        if fallback_note:
            reason += f" {fallback_note}"

        return reason

    def recommend(
        self,
        db: Session,
        *,
        query: str,
        profile: PreferenceProfile,
        explicit_budget: Optional[int],
        limit: int = 4,
        retriever: Optional[Any] = None,
        use_deep_learning: bool = True,
    ) -> tuple[list[Product], str]:
        constraints = self._parse_preferences(query, profile)
        budget = explicit_budget or constraints["budget"]

        candidate_limit = max(limit * 10, 40)
        statement = select(Product).where(Product.stock > 0)

        if constraints["min_sweetness"] is not None:
            statement = statement.where(Product.sweetness_level >= constraints["min_sweetness"])
        if constraints["max_sourness"] is not None:
            statement = statement.where(Product.sourness_level <= constraints["max_sourness"])
        if constraints["max_seed"] is not None:
            statement = statement.where(Product.seed_level <= constraints["max_seed"])
        if constraints["min_juiciness"] is not None:
            statement = statement.where(Product.juiciness_level >= constraints["min_juiciness"])
        if constraints["min_aroma"] is not None:
            statement = statement.where(Product.aroma_level >= constraints["min_aroma"])
        if constraints["min_crunchiness"] is not None:
            statement = statement.where(Product.crunchiness_level >= constraints["min_crunchiness"])
        if constraints["min_fiber"] is not None:
            statement = statement.where(Product.fiber_level >= constraints["min_fiber"])
        if constraints["min_vitamin_c"] is not None:
            statement = statement.where(Product.vitamin_c_level >= constraints["min_vitamin_c"])
        if constraints["max_sugar"] is not None:
            statement = statement.where(Product.sugar_content_level <= constraints["max_sugar"])
        if constraints["max_calories"] is not None:
            statement = statement.where(Product.calories_per_100g <= constraints["max_calories"])
        if constraints["preferred_texture"] is not None:
            statement = statement.where(Product.texture.ilike(f"%{constraints['preferred_texture']}%"))
        if budget is not None:
            statement = statement.where(Product.price <= budget)

        statement = statement.order_by(
            asc(Product.sourness_level),
            asc(Product.seed_level),
            asc(Product.price),
        ).limit(candidate_limit)

        products = list(db.scalars(statement))
        deep_learning_fallback_note = ""

        if products and use_deep_learning and retriever is not None:
            if self._supports_deep_learning(retriever):
                ranked_products = self._rank_with_deep_learning(
                    retriever,
                    query=query,
                    candidates=products,
                    constraints=constraints,
                    budget=budget,
                )
                if ranked_products:
                    products = ranked_products[:limit]
                    reason = self._build_reason(constraints=constraints, used_deep_learning=True)
                    return products, reason

                deep_learning_fallback_note = (
                    "Ở lượt này mình ưu tiên cách chấm điểm ổn định theo khẩu vị và dinh dưỡng."
                )
            else:
                deep_learning_fallback_note = "Hiện mình ưu tiên bộ tiêu chí khẩu vị và dinh dưỡng để giữ kết quả ổn định."

        if not products:
            # Graceful fallback to available products when constraints are too narrow.
            fallback = select(Product).where(Product.stock > 0).order_by(asc(Product.price)).limit(limit)
            products = list(db.scalars(fallback))
            reason = "Tiêu chí hiện tại hơi chặt, mình tạm đề xuất các sản phẩm còn hàng và dễ mua nhất trước nhé."
        else:
            products = products[:limit]
            reason = self._build_reason(
                constraints=constraints,
                used_deep_learning=False,
                fallback_note=deep_learning_fallback_note or None,
            )

        if deep_learning_fallback_note and not products:
            reason = f"{reason} {deep_learning_fallback_note}"

        return products, reason
