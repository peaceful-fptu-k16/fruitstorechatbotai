from __future__ import annotations

import re
from typing import Optional

from sqlalchemy.orm import Session

from backend.core.fruit_aliases import FRUIT_ALIASES, SHORT_CONTEXTUAL_ALIASES, extract_fruit_aliases
from backend.core.text import normalize_text
from backend.database.models import Product
from backend.database.queries import find_products_by_name, list_products


PRODUCT_ALIASES: tuple[str, ...] = FRUIT_ALIASES


EXTRA_NOISE_TOKENS: tuple[str, ...] = (
    "hom",
    "nay",
    "gi",
    "nao",
    "ngon",
    "shop",
    "cho",
    "minh",
    "em",
    "anh",
    "chi",
    "nhe",
    "voi",
)


class InventoryAgent:
    def list_available(self, db: Session, *, query: Optional[str] = None, limit: int = 8) -> list[Product]:
        return list_products(db, only_available=True, query=query, limit=limit)

    def check_inventory_by_name(self, db: Session, product_name: str) -> list[Product]:
        if not product_name.strip():
            return []
        return [product for product in find_products_by_name(db, product_name, limit=5) if product.stock > 0]

    def infer_focus_products(self, db: Session, user_message: str, *, limit: int = 3) -> list[Product]:
        normalized_message = normalize_text(user_message)
        if not normalized_message:
            return []

        message_tokens = set(normalized_message.replace("?", " ").split())
        matched_aliases = set(extract_fruit_aliases(normalized_message, aliases=PRODUCT_ALIASES))
        for alias in SHORT_CONTEXTUAL_ALIASES - matched_aliases:
            message_tokens.discard(alias)

        available_products = list_products(db, only_available=True, limit=60)

        scored: list[tuple[int, Product]] = []
        for product in available_products:
            normalized_name = normalize_text(product.name)
            score = 0

            if normalized_name in normalized_message:
                score += 8

            product_tokens = set(normalized_name.split())
            token_overlap = len(product_tokens & message_tokens)
            if token_overlap > 0:
                score += token_overlap * 2

            for alias in matched_aliases:
                if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", normalized_name) is not None:
                    score += 4

            if score > 0:
                scored.append((score, product))

        scored.sort(key=lambda item: (item[0], item[1].stock, -item[1].price), reverse=True)
        return [product for _, product in scored[:limit]]

    def extract_candidate_name(self, user_message: str) -> str:
        normalized = normalize_text(user_message)

        for alias in extract_fruit_aliases(normalized, aliases=PRODUCT_ALIASES):
            if alias:
                return alias

        noise_tokens = (
            "co",
            "con",
            "khong",
            "hang",
            "stock",
            "khong",
            "khong?",
            "trai",
            "qua",
            "cay",
            *SHORT_CONTEXTUAL_ALIASES,
            *EXTRA_NOISE_TOKENS,
        )
        parts = [part for part in normalized.replace("?", " ").split() if part not in noise_tokens and len(part) > 1]
        return " ".join(parts[:3]).strip()
