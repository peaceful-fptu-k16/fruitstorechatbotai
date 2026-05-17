from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from backend.core.text import normalize_text
from backend.database.models import Product
from backend.database.queries import find_products_by_name, list_products


class InventoryAgent:
    def list_available(self, db: Session, *, query: Optional[str] = None, limit: int = 8) -> list[Product]:
        return list_products(db, only_available=True, query=query, limit=limit)

    def check_inventory_by_name(self, db: Session, product_name: str) -> list[Product]:
        return [product for product in find_products_by_name(db, product_name, limit=5) if product.stock > 0]

    def extract_candidate_name(self, user_message: str) -> str:
        normalized = normalize_text(user_message)
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
        )
        parts = [part for part in normalized.replace("?", " ").split() if part not in noise_tokens]
        return " ".join(parts).strip()
