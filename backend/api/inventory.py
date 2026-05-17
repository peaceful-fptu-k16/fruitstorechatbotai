from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.mappers import to_product_out
from backend.database.queries import find_products_by_name, get_product_by_id
from backend.database.session import get_db
from backend.schemas import InventoryResponse

router = APIRouter(tags=["inventory"])


@router.get("/inventory", response_model=InventoryResponse)
def check_inventory(
    product_id: Optional[int] = Query(default=None),
    name: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> InventoryResponse:
    if product_id is None and not name:
        return InventoryResponse(product=None, message="Vui lòng cung cấp product_id hoặc tên để kiểm tra tồn kho.")

    if product_id is not None:
        product = get_product_by_id(db, product_id)
        if not product:
            return InventoryResponse(product=None, message="Không tìm thấy sản phẩm.")
        status_text = "Còn hàng" if product.stock > 0 else "Tạm hết hàng"
        return InventoryResponse(
            product=to_product_out(product),
            message=f"{product.name}: {status_text}, tồn kho {product.stock}.",
        )

    matches = find_products_by_name(db, name or "", limit=5)
    if not matches:
        return InventoryResponse(product=None, message="Không tìm thấy sản phẩm phù hợp.")

    best = matches[0]
    status_text = "Còn hàng" if best.stock > 0 else "Tạm hết hàng"
    return InventoryResponse(
        product=to_product_out(best),
        message=f"{best.name}: {status_text}, tồn kho {best.stock}.",
    )
