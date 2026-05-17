from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.mappers import to_product_out
from backend.database.queries import list_products
from backend.database.session import get_db
from backend.schemas import ProductsResponse

router = APIRouter(tags=["products"])


@router.get("/products", response_model=ProductsResponse)
def get_products(
    query: Optional[str] = Query(default=None, description="Search by product name"),
    available_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ProductsResponse:
    products = list_products(db, only_available=available_only, query=query, limit=limit)
    return ProductsResponse(total=len(products), items=[to_product_out(product) for product in products])
