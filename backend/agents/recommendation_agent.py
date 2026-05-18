from __future__ import annotations

import re
from typing import Any, Optional

from sqlalchemy import asc, select
from sqlalchemy.orm import Session

from backend.agents.memory_agent import PreferenceProfile
from backend.core.text import normalize_text
from backend.database.models import Product
from backend.rag.embeddings import SentenceTransformerEmbeddingModel


FRUIT_ENTITY_ALIASES: tuple[str, ...] = (
    "thanh long",
    "viet quat",
    "xoai",
    "cam",
    "nho",
    "buoi",
    "tao",
    "dua",
    "chuoi",
    "oi",
    "kiwi",
    "le",
    "man",
    "dau",
)


class RecommendationAgent:
    @staticmethod
    def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
        return any(keyword in text for keyword in keywords)

    @staticmethod
    def _parse_money_value(number_text: str, suffix: Optional[str]) -> Optional[int]:
        normalized_number = number_text.replace(",", ".").strip()
        try:
            value = float(normalized_number)
        except Exception:
            return None

        if suffix in {"k", "nghin", "ngan"}:
            value *= 1000.0
        elif suffix == "trieu":
            value *= 1_000_000.0

        if value < 1000:
            return None
        return int(value)

    def _extract_budget_bounds(self, normalized_query: str) -> tuple[Optional[int], Optional[int]]:
        range_patterns = (
            r"(?:tu|khoang)\s*(\d+(?:[.,]\d+)?)\s*(k|nghin|ngan|trieu)?\s*(?:den|toi|-)\s*(\d+(?:[.,]\d+)?)\s*(k|nghin|ngan|trieu)?",
            r"(\d+(?:[.,]\d+)?)\s*(k|nghin|ngan|trieu)?\s*-\s*(\d+(?:[.,]\d+)?)\s*(k|nghin|ngan|trieu)?",
        )

        for pattern in range_patterns:
            match = re.search(pattern, normalized_query)
            if not match:
                continue

            left = self._parse_money_value(match.group(1), match.group(2))
            right = self._parse_money_value(match.group(3), match.group(4))
            if left is None or right is None:
                continue

            return (left, right) if left <= right else (right, left)

        min_price: Optional[int] = None
        max_price: Optional[int] = None

        max_patterns = (
            r"(?:duoi|toi da|khong qua|khong vuot qua|khong hon)\s*(\d+(?:[.,]\d+)?)\s*(k|nghin|ngan|trieu)?",
            r"(?:gia|ngan sach)\s*(?:duoi|toi da)?\s*(\d+(?:[.,]\d+)?)\s*(k|nghin|ngan|trieu)?",
        )
        for pattern in max_patterns:
            match = re.search(pattern, normalized_query)
            if not match:
                continue
            parsed = self._parse_money_value(match.group(1), match.group(2))
            if parsed is not None:
                max_price = parsed
                break

        min_patterns = (
            r"(?:tren|tu|it nhat|toi thieu|hon)\s*(\d+(?:[.,]\d+)?)\s*(k|nghin|ngan|trieu)?",
        )
        for pattern in min_patterns:
            match = re.search(pattern, normalized_query)
            if not match:
                continue
            parsed = self._parse_money_value(match.group(1), match.group(2))
            if parsed is not None:
                min_price = parsed
                break

        if min_price is None and max_price is None:
            generic_matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*(k|nghin|ngan|trieu)", normalized_query)
            if generic_matches:
                fallback_value = self._parse_money_value(generic_matches[0][0], generic_matches[0][1])
                if fallback_value is not None:
                    if any(token in normalized_query for token in ("tren", "tu", "it nhat", "toi thieu", "hon")):
                        min_price = fallback_value
                    else:
                        max_price = fallback_value

        if min_price is not None and max_price is not None and min_price > max_price:
            min_price, max_price = max_price, min_price

        return min_price, max_price

    def _extract_requested_entities(self, normalized_query: str) -> list[str]:
        requested: list[str] = []
        seen: set[str] = set()

        for alias in sorted(FRUIT_ENTITY_ALIASES, key=len, reverse=True):
            pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"
            if re.search(pattern, normalized_query) is None:
                continue

            if alias in seen:
                continue
            seen.add(alias)
            requested.append(alias)

        return requested

    def parse_preferences(self, query: str, profile: PreferenceProfile) -> dict:
        normalized = normalize_text(query)
        requested_entities = self._extract_requested_entities(normalized)

        explicit_low_sweet = self._contains_any(
            normalized,
            (
                "khong qua ngot",
                "dung ngot qua",
                "it ngot",
                "ngot nhe",
                "ngot vua",
            ),
        )

        explicit_sweet = self._contains_any(
            normalized,
            (
                "ngot",
                "ngot nhat",
                "rat ngot",
                "cuc ngot",
                "ngot hon",
            ),
        ) and not explicit_low_sweet
        explicit_low_sour = self._contains_any(
            normalized,
            (
                "it chua",
                "khong chua",
                "chua nhe",
                "chua nhe thoi",
                "chua vua",
                "khong qua chua",
                "dung chua qua",
            ),
        )
        explicit_sour = (
            self._contains_any(
                normalized,
                (
                    "chua",
                    "sour",
                    "chua nhat",
                    "rat chua",
                    "cuc chua",
                    "chua hon",
                ),
            )
            and not explicit_low_sour
        )
        wants_sweetest = self._contains_any(normalized, ("ngot nhat", "rat ngot", "cuc ngot"))
        wants_sourest = self._contains_any(normalized, ("chua nhat", "rat chua", "cuc chua", "chua hon"))

        if explicit_low_sweet:
            min_sweetness = None
            max_sweetness = 6
        elif (explicit_sour or explicit_low_sour) and not explicit_sweet:
            min_sweetness = None
            max_sweetness = None
        elif wants_sweetest:
            min_sweetness = 8
            max_sweetness = None
        elif explicit_sweet:
            min_sweetness = 7
            max_sweetness = None
        elif profile.prefers_sweet and not explicit_sour and not explicit_low_sour:
            min_sweetness = 7
            max_sweetness = None
        else:
            min_sweetness = None
            max_sweetness = None

        if explicit_low_sour:
            max_sourness = 3
            min_sourness = None
        elif wants_sourest:
            max_sourness = None
            min_sourness = 5
        elif explicit_sour:
            max_sourness = None
            min_sourness = 4
        elif profile.prefers_low_sour:
            max_sourness = 3
            min_sourness = None
        else:
            max_sourness = None
            min_sourness = None

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
            "min_sweetness": min_sweetness,
            "max_sweetness": max_sweetness,
            "min_sourness": min_sourness,
            "max_sourness": max_sourness,
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

        min_price, max_price = self._extract_budget_bounds(normalized)
        wants_budget_carryover = self._contains_any(
            normalized,
            (
                "giu nguyen ngan sach",
                "giu ngan sach",
                "nhu cu",
                "nhu truoc",
                "van tam gia do",
            ),
        )
        if max_price is not None or min_price is not None:
            constraints["min_price"] = min_price
            constraints["max_price"] = max_price
            constraints["budget"] = max_price
        elif wants_budget_carryover:
            constraints["min_price"] = None
            constraints["max_price"] = profile.budget_hint
            constraints["budget"] = profile.budget_hint
        else:
            constraints["min_price"] = None
            constraints["max_price"] = None
            constraints["budget"] = None

        constraints["requested_entities"] = requested_entities
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

        if constraints["max_sweetness"] is not None:
            score_parts.append((10.0 - float(product.sweetness_level)) / 10.0)

        if constraints["max_sourness"] is not None:
            score_parts.append((10.0 - float(product.sourness_level)) / 10.0)

        if constraints["min_sourness"] is not None:
            score_parts.append(float(product.sourness_level) / 10.0)

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

    @staticmethod
    def _tie_breaker_score(product: Product, *, constraints: dict) -> float:
        if constraints.get("min_sourness") is not None:
            return float(product.sourness_level) - float(product.sweetness_level) * 0.15

        if constraints.get("min_sweetness") is not None:
            return float(product.sweetness_level) - float(product.sourness_level) * 0.15

        return float(product.sweetness_level - product.sourness_level)

    @staticmethod
    def _product_matches_requested_entities(product: Product, requested_entities: list[str]) -> bool:
        normalized_name = normalize_text(product.name)
        return any(entity in normalized_name for entity in requested_entities)

    @staticmethod
    def _product_similarity_score(anchor: Product, candidate: Product) -> float:
        feature_pairs = (
            (anchor.sweetness_level, candidate.sweetness_level),
            (anchor.sourness_level, candidate.sourness_level),
            (anchor.juiciness_level, candidate.juiciness_level),
            (anchor.aroma_level, candidate.aroma_level),
            (anchor.crunchiness_level, candidate.crunchiness_level),
            (anchor.fiber_level, candidate.fiber_level),
            (anchor.vitamin_c_level, candidate.vitamin_c_level),
            (anchor.sugar_content_level, candidate.sugar_content_level),
        )

        distance = sum(abs(float(left) - float(right)) / 10.0 for left, right in feature_pairs)
        similarity = 1.0 - (distance / float(len(feature_pairs)))

        if normalize_text(anchor.texture) == normalize_text(candidate.texture):
            similarity += 0.07
        if normalize_text(anchor.best_use) == normalize_text(candidate.best_use):
            similarity += 0.06

        return max(0.0, min(1.0, similarity))

    def _prioritize_requested_then_similar(
        self,
        *,
        ranked_products: list[Product],
        requested_entities: list[str],
        constraints: dict,
        budget: Optional[int],
        limit: int,
    ) -> tuple[list[Product], bool, bool]:
        if not ranked_products:
            return [], False, False

        if not requested_entities:
            return ranked_products[:limit], False, False

        requested_matches = [
            product
            for product in ranked_products
            if self._product_matches_requested_entities(product, requested_entities)
        ]
        if not requested_matches:
            return ranked_products[:limit], False, False

        prioritized = requested_matches[:limit]
        remaining_slots = limit - len(prioritized)
        if remaining_slots <= 0:
            return prioritized, True, False

        prioritized_ids = {product.id for product in prioritized}
        non_requested_candidates = [
            product
            for product in ranked_products
            if product.id not in prioritized_ids
            and not self._product_matches_requested_entities(product, requested_entities)
        ]
        if not non_requested_candidates:
            return prioritized, True, False

        anchors = prioritized[: min(len(prioritized), 2)]
        similar_candidates = sorted(
            non_requested_candidates,
            key=lambda product: (
                max(self._product_similarity_score(anchor, product) for anchor in anchors),
                self._preference_score(product, constraints=constraints, budget=budget),
                self._tie_breaker_score(product, constraints=constraints),
                -product.price,
            ),
            reverse=True,
        )

        extras = similar_candidates[:remaining_slots]
        return prioritized + extras, True, bool(extras)

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
                self._tie_breaker_score(product, constraints=constraints),
                -product.price,
            ),
            reverse=True,
        )
        return ranked

    def _build_reason(
        self,
        *,
        constraints: dict,
        used_deep_learning: bool,
        fallback_note: Optional[str] = None,
        requested_entity_matched: bool = False,
        added_similar_products: bool = False,
        missing_requested_entities: bool = False,
    ) -> str:
        traits: list[str] = []
        if constraints.get("min_sweetness") is not None:
            traits.append("độ ngọt cao")
        if constraints.get("max_sweetness") is not None:
            traits.append("độ ngọt vừa phải")
        if constraints.get("max_sourness") is not None:
            traits.append("vị ít chua")
        if constraints.get("min_sourness") is not None:
            traits.append("vị chua rõ")
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

        min_price = constraints.get("min_price")
        max_price = constraints.get("max_price")
        if min_price is not None and max_price is not None:
            traits.append(
                f"ngân sách từ {int(min_price):,}đ đến {int(max_price):,}đ".replace(",", ".")
            )
        elif min_price is not None:
            traits.append(f"ngân sách từ {int(min_price):,}đ trở lên".replace(",", "."))
        elif max_price is not None:
            traits.append(f"ngân sách dưới {int(max_price):,}đ".replace(",", "."))

        requested_entities: list[str] = constraints.get("requested_entities") or []
        if requested_entities and requested_entity_matched:
            traits.append(f"đúng loại bạn cần ({', '.join(requested_entities)})")

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

        if requested_entity_matched:
            reason += " Mình ưu tiên xếp đúng loại quả bạn hỏi lên đầu danh sách."
        if added_similar_products:
            reason += " Sau đó mình thêm vài loại có thuộc tính gần giống để bạn dễ so sánh."
        elif missing_requested_entities and requested_entities:
            readable_entities = ", ".join(requested_entities)
            reason += (
                f" Hiện chưa có đúng loại ({readable_entities}), nên mình gợi ý các loại có thuộc tính gần giống."
            )

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
        min_price = constraints.get("min_price")
        max_price = explicit_budget if explicit_budget is not None else constraints.get("max_price")
        constraints["max_price"] = max_price
        constraints["budget"] = max_price
        budget = max_price

        candidate_limit = max(limit * 10, 40)
        statement = select(Product).where(Product.stock > 0)

        if constraints["min_sweetness"] is not None:
            statement = statement.where(Product.sweetness_level >= constraints["min_sweetness"])
        if constraints["max_sweetness"] is not None:
            statement = statement.where(Product.sweetness_level <= constraints["max_sweetness"])
        if constraints["max_sourness"] is not None:
            statement = statement.where(Product.sourness_level <= constraints["max_sourness"])
        if constraints["min_sourness"] is not None:
            statement = statement.where(Product.sourness_level >= constraints["min_sourness"])
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
        if min_price is not None:
            statement = statement.where(Product.price >= min_price)
        if max_price is not None:
            statement = statement.where(Product.price <= max_price)

        if constraints["min_sourness"] is not None:
            statement = statement.order_by(
                Product.sourness_level.desc(),
                Product.sweetness_level.desc(),
                asc(Product.price),
            )
        elif constraints["max_sweetness"] is not None:
            statement = statement.order_by(
                Product.sweetness_level.desc(),
                asc(Product.sourness_level),
                asc(Product.price),
            )
        elif constraints["max_sourness"] is not None:
            statement = statement.order_by(
                asc(Product.sourness_level),
                Product.sweetness_level.desc(),
                asc(Product.price),
            )
        elif constraints["min_sweetness"] is not None:
            statement = statement.order_by(
                Product.sweetness_level.desc(),
                asc(Product.sourness_level),
                asc(Product.price),
            )
        else:
            statement = statement.order_by(
                Product.sweetness_level.desc(),
                asc(Product.sourness_level),
                asc(Product.price),
            )

        statement = statement.limit(candidate_limit)

        products = list(db.scalars(statement))

        deep_learning_fallback_note = ""
        requested_entities: list[str] = constraints.get("requested_entities") or []

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
                    products, requested_entity_matched, added_similar_products = self._prioritize_requested_then_similar(
                        ranked_products=ranked_products,
                        requested_entities=requested_entities,
                        constraints=constraints,
                        budget=budget,
                        limit=limit,
                    )
                    reason = self._build_reason(
                        constraints=constraints,
                        used_deep_learning=True,
                        requested_entity_matched=requested_entity_matched,
                        added_similar_products=added_similar_products,
                        missing_requested_entities=bool(requested_entities and not requested_entity_matched),
                    )
                    return products, reason

                deep_learning_fallback_note = ""
            else:
                deep_learning_fallback_note = ""

        if not products:
            if requested_entities:
                readable_entities = ", ".join(requested_entities)
                reason = (
                    f"Mình chưa tìm thấy sản phẩm đúng loại bạn cần ({readable_entities}) "
                    "và khớp tiêu chí hiện tại."
                )
            else:
                reason = "Không tìm thấy sản phẩm khớp hoàn toàn với tiêu chí hiện tại của bạn."
            return [], reason
        else:
            products, requested_entity_matched, added_similar_products = self._prioritize_requested_then_similar(
                ranked_products=products,
                requested_entities=requested_entities,
                constraints=constraints,
                budget=budget,
                limit=limit,
            )
            reason = self._build_reason(
                constraints=constraints,
                used_deep_learning=False,
                fallback_note=deep_learning_fallback_note or None,
                requested_entity_matched=requested_entity_matched,
                added_similar_products=added_similar_products,
                missing_requested_entities=bool(requested_entities and not requested_entity_matched),
            )

        return products, reason
