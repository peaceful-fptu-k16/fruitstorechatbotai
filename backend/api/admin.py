from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.core.cache import semantic_cache
from backend.core.config import Settings, get_settings
from backend.core.rate_limit import rate_limiter
from backend.core.security import UserContext, create_access_token, get_current_admin
from backend.database.queries import (
    check_existing_idempotent_response,
    hash_updates,
    store_idempotent_response,
    update_stock,
)
from backend.database.session import get_db
from backend.schemas import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminUpdateStockRequest,
    AdminUpdateStockResponse,
    UpdatedStockItem,
)

router = APIRouter(prefix="/admin", tags=["admin"])


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

    # Rebuild index to ensure semantic layer observes product updates.
    request.app.state.services.retriever.rebuild_index(db)
    semantic_cache.invalidate_prefix("chat:rec:")
    semantic_cache.invalidate_prefix("recommend:")

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
