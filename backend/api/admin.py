from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.api.mappers import to_product_out
from backend.core.cache import semantic_cache
from backend.core.config import Settings, get_settings
from backend.core.rate_limit import rate_limiter
from backend.core.security import UserContext, create_access_token, get_current_admin
from backend.database.queries import (
    check_existing_idempotent_response,
    get_product_by_id,
    get_latest_inventory_event_id,
    hash_updates,
    list_inventory_events,
    store_idempotent_response,
    update_product_profile,
    update_stock,
)
from backend.database.session import get_db
from backend.schemas import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminUpdateStockRequest,
    AdminUpdateStockResponse,
    InventoryEventOut,
    InventoryEventsResponse,
    ProductUpdateRequest,
    ProductUpdateResponse,
    UpdatedStockItem,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _refresh_local_product_state(request: Request, db: Session) -> None:
    services = getattr(request.app.state, "services", None)
    if services is not None:
        services.retriever.rebuild_index(db)
        services.inventory_revision = get_latest_inventory_event_id(db)
    semantic_cache.invalidate_prefix("chat:")
    semantic_cache.invalidate_prefix("recommend:")


@router.post("/login", response_model=AdminLoginResponse)
def admin_login(payload: AdminLoginRequest, settings: Settings = Depends(get_settings)) -> AdminLoginResponse:
    if payload.username != settings.admin_username or payload.password != settings.admin_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(
        payload={"sub": payload.username, "role": "admin"},
        settings=settings,
    )

    return AdminLoginResponse(
        access_token=token,
        expires_in_minutes=settings.admin_access_token_expire_minutes,
    )


@router.post("/update-stock", response_model=AdminUpdateStockResponse)
def admin_update_stock(
    payload: AdminUpdateStockRequest,
    request: Request,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    admin: UserContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminUpdateStockResponse:
    if not payload.updates:
        raise HTTPException(status_code=400, detail="updates must not be empty")

    limiter_key = f"admin:{admin.sub}"
    allowed = rate_limiter.allow(
        limiter_key,
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    updates = [item.model_dump() for item in payload.updates]
    request_hash = hash_updates(updates)

    try:
        existing = check_existing_idempotent_response(
            db,
            endpoint="/admin/update-stock",
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if existing:
        return AdminUpdateStockResponse(**existing)

    updated_items: list[UpdatedStockItem] = []
    for item in payload.updates:
        try:
            product = update_stock(
                db,
                actor=admin.sub,
                product_id=item.product_id,
                quantity=item.quantity,
                operation=item.operation,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        updated_items.append(
            UpdatedStockItem(
                product_id=product.id,
                name=product.name,
                stock=product.stock,
            )
        )

    # Rebuild local service index when this app owns one. In the split-service
    # deployment the chatbot service detects inventory_events and refreshes its
    # own in-memory index/cache on the next request.
    _refresh_local_product_state(request, db)

    response = AdminUpdateStockResponse(
        status="success",
        applied=True,
        idempotency_key=idempotency_key,
        updates=updated_items,
        actor=admin.sub,
        timestamp=datetime.now(timezone.utc),
        details={"updated_count": len(updated_items)},
    )

    store_idempotent_response(
        db,
        endpoint="/admin/update-stock",
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        response_json=response.model_dump(mode="json"),
    )

    return response


@router.patch("/products/{product_id}", response_model=ProductUpdateResponse)
def admin_update_product(
    product_id: int,
    payload: ProductUpdateRequest,
    request: Request,
    admin: UserContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> ProductUpdateResponse:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="At least one product field is required")

    try:
        product, changed_fields = update_product_profile(
            db,
            actor=admin.sub,
            product_id=product_id,
            updates=updates,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if changed_fields:
        _refresh_local_product_state(request, db)

    return ProductUpdateResponse(
        status="success",
        product=to_product_out(product),
        changed_fields=changed_fields,
        actor=admin.sub,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/inventory-events", response_model=InventoryEventsResponse)
def admin_inventory_events(
    product_id: Optional[int] = None,
    limit: int = 50,
    admin: UserContext = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> InventoryEventsResponse:
    del admin

    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200")
    if product_id is not None and get_product_by_id(db, product_id) is None:
        raise HTTPException(status_code=404, detail=f"Product id={product_id} not found")

    events = list_inventory_events(db, product_id=product_id, limit=limit)
    items = [
        InventoryEventOut(
            id=event.id,
            product_id=event.product_id,
            product_name=event.product.name if event.product else "",
            actor=event.actor,
            operation=event.operation,
            quantity_delta=event.quantity_delta,
            new_stock=event.new_stock,
            created_at=event.created_at,
        )
        for event in events
    ]
    return InventoryEventsResponse(total=len(items), items=items)
