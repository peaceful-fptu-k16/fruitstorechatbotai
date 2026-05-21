from __future__ import annotations

import hashlib
import hmac
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


@dataclass
class MessengerClient:
    settings: Settings

    @property
    def messages_url(self) -> str:
        page_id = self.settings.facebook_page_id or "me"
        version = self.settings.facebook_graph_api_version.strip("/") or "v22.0"
        return f"https://graph.facebook.com/{version}/{page_id}/messages"

    def send_text(self, *, recipient_id: str, text: str, messaging_type: str = "RESPONSE") -> None:
        if not self.settings.facebook_page_access_token:
            raise RuntimeError("FACEBOOK_PAGE_ACCESS_TOKEN is required to send Messenger replies")

        headers = {
            "Authorization": f"Bearer {self.settings.facebook_page_access_token}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=self.settings.facebook_request_timeout_seconds) as client:
            for chunk in split_messenger_text(text):
                response = client.post(
                    self.messages_url,
                    headers=headers,
                    json={
                        "messaging_type": messaging_type,
                        "recipient": {"id": recipient_id},
                        "message": {"text": chunk},
                    },
                )
                response.raise_for_status()
