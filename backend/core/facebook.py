from __future__ import annotations

import hashlib
import hmac
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Optional

import httpx

from backend.core.config import Settings


def verify_facebook_signature(*, app_secret: str, body: bytes, signature_header: Optional[str]) -> bool:
    if not app_secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    supplied = signature_header.removeprefix("sha256=")
    expected = hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(supplied, expected)


def split_messenger_text(text: str, *, limit: int = 1900) -> list[str]:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return [normalized]

    chunks: list[str] = []
    current = ""
    for sentence in normalized.replace(". ", ".\n").splitlines():
        if not current:
            current = sentence
            continue
        if len(current) + 1 + len(sentence) <= limit:
            current = f"{current} {sentence}"
        else:
            chunks.append(current[:limit])
            current = sentence
    if current:
        chunks.append(current[:limit])
    return chunks


def _trim_messenger_text(value: str, *, limit: int) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 3)].rstrip() + "..."


@dataclass(frozen=True)
class MessengerTemplateButton:
    title: str
    payload: str
    type: str = "postback"


@dataclass(frozen=True)
class MessengerGenericElement:
    title: str
    subtitle: str = ""
    image_url: str = ""
    buttons: tuple[MessengerTemplateButton, ...] = ()


@dataclass
class MessengerClient:
    settings: Settings

    @property
    def messages_url(self) -> str:
        page_id = self.settings.facebook_page_id or "me"
        version = self.settings.facebook_graph_api_version.strip("/") or "v22.0"
        return f"https://graph.facebook.com/{version}/{page_id}/messages"

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.facebook_page_access_token}",
            "Content-Type": "application/json",
        }

    def _post_message(self, *, payload: dict) -> None:
        if not self.settings.facebook_page_access_token:
            raise RuntimeError("FACEBOOK_PAGE_ACCESS_TOKEN is required to send Messenger replies")

        with httpx.Client(timeout=self.settings.facebook_request_timeout_seconds) as client:
            response = client.post(self.messages_url, headers=self._headers, json=payload)
            response.raise_for_status()

    def send_text(self, *, recipient_id: str, text: str, messaging_type: str = "RESPONSE") -> None:
        if not self.settings.facebook_page_access_token:
            raise RuntimeError("FACEBOOK_PAGE_ACCESS_TOKEN is required to send Messenger replies")

        for chunk in split_messenger_text(text):
            self._post_message(
                payload={
                    "messaging_type": messaging_type,
                    "recipient": {"id": recipient_id},
                    "message": {"text": chunk},
                }
            )

    def send_generic_template(
        self,
        *,
        recipient_id: str,
        elements: Sequence[MessengerGenericElement],
        messaging_type: str = "RESPONSE",
        image_aspect_ratio: str = "square",
    ) -> None:
        if not elements:
            return

        payload_elements = []
        for element in elements[:10]:
            item: dict = {"title": _trim_messenger_text(element.title, limit=80)}
            if element.subtitle:
                item["subtitle"] = _trim_messenger_text(element.subtitle, limit=80)
            if element.image_url:
                item["image_url"] = element.image_url

            buttons = []
            for button in element.buttons[:3]:
                if not button.payload.strip():
                    continue
                buttons.append(
                    {
                        "type": button.type,
                        "title": _trim_messenger_text(button.title, limit=20),
                        "payload": button.payload.strip()[:1000],
                    }
                )
            if buttons:
                item["buttons"] = buttons

            payload_elements.append(item)

        self._post_message(
            payload={
                "messaging_type": messaging_type,
                "recipient": {"id": recipient_id},
                "message": {
                    "attachment": {
                        "type": "template",
                        "payload": {
                            "template_type": "generic",
                            "image_aspect_ratio": image_aspect_ratio,
                            "elements": payload_elements,
                        },
                    }
                },
            }
        )
