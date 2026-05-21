from __future__ import annotations

import json
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from backend.api.chat import handle_chat_request
from backend.core.config import Settings, get_settings
from backend.core.facebook import MessengerClient, verify_facebook_signature
from backend.database.session import get_db
from backend.schemas import ChatRequest


router = APIRouter(prefix="/webhooks/facebook", tags=["facebook-messenger"])


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

            text = message.get("text")
            if not isinstance(text, str) or not text.strip():
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

            try:
                messenger.send_text(recipient_id=sender_id, text=reply_text)
            except (RuntimeError, httpx.HTTPError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to send Messenger reply: {exc}",
                ) from exc

            handled += 1

    return {"status": "ok", "handled": handled}
