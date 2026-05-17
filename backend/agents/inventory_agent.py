from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from backend.core.text import normalize_text
from backend.database.models import Product
from backend.database.queries import find_products_by_name, list_products


PRODUCT_ALIASES: tuple[str, ...] = (
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
        return [product for product in find_products_by_name(db, product_name, limit=5) if product.stock > 0]

    def infer_focus_products(self, db: Session, user_message: str, *, limit: int = 3) -> list[Product]:
        normalized_message = normalize_text(user_message)
        if not normalized_message:
            return []

        message_tokens = set(normalized_message.replace("?", " ").split())
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

            for alias in PRODUCT_ALIASES:
                if alias in normalized_message and alias in normalized_name:
                    score += 4

            if score > 0:
                scored.append((score, product))

        scored.sort(key=lambda item: (item[0], item[1].stock, -item[1].price), reverse=True)
        return [product for _, product in scored[:limit]]

    def extract_candidate_name(self, user_message: str) -> str:
        normalized = normalize_text(user_message)

        for alias in PRODUCT_ALIASES:
            if alias in normalized:
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
            "cay",
            *EXTRA_NOISE_TOKENS,
        )
        parts = [part for part in normalized.replace("?", " ").split() if part not in noise_tokens and len(part) > 1]
        return " ".join(parts[:3]).strip()
