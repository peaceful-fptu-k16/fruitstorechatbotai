from __future__ import annotations

import json
import re
from typing import Optional
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from backend.api.mappers import to_product_out
from backend.api.chat import handle_chat_request
from backend.core.config import Settings, get_settings
from backend.core.facebook import (
    MessengerClient,
    MessengerGenericElement,
    MessengerTemplateButton,
    verify_facebook_signature,
)
from backend.core.text import normalize_text
from backend.database.queries import get_product_by_id
from backend.database.session import get_db
from backend.schemas import ChatRequest, ProductOut


router = APIRouter(prefix="/webhooks/facebook", tags=["facebook-messenger"])

FRUIT_EMOJI_MAP: tuple[tuple[str, str], ...] = (
    ("xoài", "🥭"),
    ("cam", "🍊"),
    ("táo", "🍎"),
    ("nho", "🍇"),
    ("dâu tây", "🍓"),
    ("dâu", "🍓"),
    ("chuối", "🍌"),
    ("dứa", "🍍"),
    ("thơm", "🍍"),
    ("mít", "🌿"),
    ("bưởi", "🍋"),
    ("chanh", "🍋"),
    ("kiwi", "🥝"),
    ("lê", "🍐"),
    ("việt quất", "🫐"),
    ("thanh long", "🐉"),
    ("vải", "🍒"),
    ("chôm chôm", "🌺"),
    ("sapoche", "🟤"),
    ("ổi", "🟢"),
    ("mận", "🟣"),
)


def _format_vnd(price: int) -> str:
    return f"{price:,.0f}".replace(",", ".") + "đ"


def _product_slug(name: str) -> str:
    return quote("-".join(normalize_text(name).split()))


def _fruit_emoji(name: str) -> str:
    normalized_name = normalize_text(name)
    for keyword, emoji in FRUIT_EMOJI_MAP:
        if normalize_text(keyword) in normalized_name:
            return emoji
    return "🍑"


def _twemoji_codepoint(emoji: str) -> str:
    codepoints = [
        f"{ord(char):x}"
        for char in emoji
        if ord(char) not in {0xFE0E, 0xFE0F, 0x200D}
    ]
    return "-".join(codepoints)


def _fruit_logo_image_url(product: ProductOut) -> str:
    codepoint = _twemoji_codepoint(_fruit_emoji(product.name))
    if not codepoint:
        return ""
    return f"https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/{codepoint}.png"


def _product_image_url(product: ProductOut, settings: Settings) -> str:
    image_base = settings.facebook_product_image_base_url.strip()
    if not image_base:
        return _fruit_logo_image_url(product)

    try:
        if "{id}" in image_base or "{slug}" in image_base:
            image_url = image_base.format(id=product.id, slug=_product_slug(product.name))
        else:
            image_url = f"{image_base.rstrip('/')}/{product.id}.jpg"
    except Exception:
        return ""

    if not image_url.lower().startswith("https://"):
        return _fruit_logo_image_url(product)
    return image_url


def _build_product_template_elements(
    products: list[ProductOut],
    *,
    settings: Settings,
) -> list[MessengerGenericElement]:
    elements: list[MessengerGenericElement] = []
    for product in products[:10]:
        subtitle_parts = [
            _format_vnd(product.price),
            f"còn {product.stock}",
        ]
        if product.best_use:
            subtitle_parts.append(product.best_use)

        elements.append(
            MessengerGenericElement(
                title=product.name,
                subtitle=" · ".join(subtitle_parts),
                image_url=_product_image_url(product, settings),
                buttons=(
                    MessengerTemplateButton(title="Xem chi tiết", payload=f"PRODUCT:DETAIL:{product.id}"),
                    MessengerTemplateButton(title="Đặt hàng", payload=f"PRODUCT:ORDER:{product.id}"),
                    MessengerTemplateButton(title="Thêm vào giỏ", payload=f"PRODUCT:ADD_TO_CART:{product.id}"),
                ),
            )
        )
    return elements


def _handle_product_postback(
    payload: str,
    *,
    db: Session,
) -> tuple[str, list[ProductOut]]:
    match = re.fullmatch(r"PRODUCT:(DETAIL|ORDER|ADD_TO_CART):(\d+)", payload)
    if not match:
        return "Mình chưa xử lý được nút này. Bạn nhắn lại nhu cầu mua trái cây giúp mình nhé.", []

    action = match.group(1)
    product = get_product_by_id(db, int(match.group(2)))
    if product is None:
        return "Sản phẩm này hiện không còn trong danh sách của shop.", []

    product_out = to_product_out(product)
    if action == "DETAIL":
        answer = (
            f"{product.name}: giá {_format_vnd(product.price)}, còn {product.stock}. "
            f"{product.description or product.best_use}"
        )
        return answer, [product_out]

    if action == "ORDER":
        return (
            f"Mình ghi nhận bạn muốn đặt {product.name}. "
            "Bạn gửi số lượng và địa chỉ nhận hàng để mình kiểm tra tồn kho và tạm tính đơn nhé.",
            [product_out],
        )

    return (
        f"Mình đã ghi nhận {product.name} vào giỏ tạm. "
        "Bạn có thể bấm thêm sản phẩm khác hoặc gửi số lượng, địa chỉ để chốt đơn.",
        [product_out],
    )


@router.get("", response_class=PlainTextResponse)
def verify_webhook(
    hub_mode: Optional[str] = Query(default=None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(default=None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(default=None, alias="hub.challenge"),
    settings: Settings = Depends(get_settings),
) -> PlainTextResponse:
    if (
        hub_mode == "subscribe"
        and hub_challenge is not None
        and hub_verify_token == settings.facebook_verify_token
    ):
        return PlainTextResponse(hub_challenge)

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Facebook verify token")


@router.post("")
async def receive_webhook(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    body = await request.body()
    if not verify_facebook_signature(
        app_secret=settings.facebook_app_secret,
        body=body,
        signature_header=request.headers.get("X-Hub-Signature-256"),
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Facebook signature")

    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload") from exc

    if payload.get("object") != "page":
        return {"status": "ignored", "handled": 0}

    messenger = MessengerClient(settings=settings)
    handled = 0

    for entry in payload.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = event.get("sender", {}).get("id")
            message = event.get("message") or {}
            if not sender_id or message.get("is_echo"):
                continue

            product_cards: list[MessengerGenericElement] = []
            postback = event.get("postback") or {}
            postback_payload = postback.get("payload")
            text = message.get("text")
            if isinstance(postback_payload, str) and postback_payload.strip():
                postback_text, postback_products = _handle_product_postback(postback_payload.strip(), db=db)
                reply_text = postback_text
                product_cards = _build_product_template_elements(postback_products, settings=settings)
            elif not isinstance(text, str) or not text.strip():
                reply_text = "Hien tai shop ho tro tu van bang tin nhan van ban. Ban gui nhu cau mua hoa qua giup minh nhe."
            else:
                chat_response = handle_chat_request(
                    ChatRequest(
                        user_id=f"facebook:{sender_id}",
                        session_id=f"facebook:{sender_id}",
                        message=text,
                        language="vi",
                    ),
                    app_state=request.app.state,
                    db=db,
                    source="/webhooks/facebook",
                )
                reply_text = chat_response.answer
                product_cards = _build_product_template_elements(chat_response.products, settings=settings)

            try:
                messenger.send_text(recipient_id=sender_id, text=reply_text)
                if product_cards:
                    messenger.send_generic_template(recipient_id=sender_id, elements=product_cards)
            except (RuntimeError, httpx.HTTPError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to send Messenger reply: {exc}",
                ) from exc

            handled += 1

    return {"status": "ok", "handled": handled}
