from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from backend.admin_main import app as admin_app
from backend.chatbot_main import app as chatbot_app
from backend.core.config import get_settings
from backend.core.facebook import MessengerClient


def test_admin_service_serves_admin_ui() -> None:
    with TestClient(admin_app) as client:
        response = client.get("/admin")

    assert response.status_code == 200
    assert "Quản trị cửa hàng trái cây" in response.text
    assert "/admin/update-stock" in response.text
    assert "/admin/products/" in response.text


def test_admin_can_update_product_profile_and_view_audit() -> None:
    with TestClient(admin_app) as client:
        login = client.post(
            "/admin/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        products = client.get("/products", params={"query": "Cam", "limit": 5})
        assert products.status_code == 200
        product = products.json()["items"][0]
        product_id = product["id"]
        original_price = product["price"]
        new_price = original_price + 123

        try:
            update = client.patch(
                f"/admin/products/{product_id}",
                json={"price": new_price, "description": product["description"] + " Test"},
                headers=headers,
            )
            assert update.status_code == 200
            payload = update.json()
            assert payload["product"]["price"] == new_price
            assert set(payload["changed_fields"]) == {"price", "description"}

            audit = client.get("/admin/inventory-events", params={"product_id": product_id}, headers=headers)
            assert audit.status_code == 200
            audit_payload = audit.json()
            assert audit_payload["items"]
            assert audit_payload["items"][0]["operation"] == "product_update"
        finally:
            client.patch(
                f"/admin/products/{product_id}",
                json={"price": original_price, "description": product["description"]},
                headers=headers,
            )


def test_facebook_webhook_verification(monkeypatch) -> None:
    monkeypatch.setenv("FACEBOOK_VERIFY_TOKEN", "verify-token")
    get_settings.cache_clear()

    with TestClient(chatbot_app) as client:
        response = client.get(
            "/webhooks/facebook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "verify-token",
                "hub.challenge": "challenge-123",
            },
        )

    assert response.status_code == 200
    assert response.text == "challenge-123"


def test_facebook_webhook_rejects_invalid_verify_token(monkeypatch) -> None:
    monkeypatch.setenv("FACEBOOK_VERIFY_TOKEN", "verify-token")
    get_settings.cache_clear()

    with TestClient(chatbot_app) as client:
        response = client.get(
            "/webhooks/facebook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "challenge-123",
            },
        )

    assert response.status_code == 403


def test_facebook_webhook_replies_to_text_message(monkeypatch) -> None:
    get_settings.cache_clear()
    sent: list[dict] = []

    def fake_send_text(self, *, recipient_id: str, text: str, messaging_type: str = "RESPONSE") -> None:
        sent.append(
            {
                "recipient_id": recipient_id,
                "text": text,
                "messaging_type": messaging_type,
            }
        )

    monkeypatch.setattr(MessengerClient, "send_text", fake_send_text)

    payload = {
        "object": "page",
        "entry": [
            {
                "messaging": [
                    {
                        "sender": {"id": "psid-1"},
                        "recipient": {"id": "page-1"},
                        "timestamp": 1,
                        "message": {"mid": "m-1", "text": "Cam con hang khong?"},
                    }
                ]
            }
        ],
    }

    with TestClient(chatbot_app) as client:
        response = client.post("/webhooks/facebook", json=payload)

    assert response.status_code == 200
    assert response.json()["handled"] == 1
    assert sent
    assert sent[0]["recipient_id"] == "psid-1"
    assert sent[0]["messaging_type"] == "RESPONSE"
    assert sent[0]["text"]


def test_chatbot_service_refreshes_after_admin_stock_update() -> None:
    idempotency_key = f"split-service-{uuid4()}"

    with TestClient(chatbot_app) as chatbot_client:
        initial_revision = chatbot_app.state.services.inventory_revision

        with TestClient(admin_app) as admin_client:
            login = admin_client.post(
                "/admin/login",
                json={"username": "admin", "password": "admin123"},
            )
            assert login.status_code == 200
            token = login.json()["access_token"]

            update = admin_client.post(
                "/admin/update-stock",
                json={"updates": [{"product_id": 1, "operation": "inc", "quantity": 1}]},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Idempotency-Key": idempotency_key,
                },
            )
            assert update.status_code == 200

        response = chatbot_client.post(
            "/chat",
            json={
                "user_id": "tester",
                "session_id": f"split-service-{uuid4()}",
                "message": "Xoai con hang khong?",
            },
        )

    assert response.status_code == 200
    assert chatbot_app.state.services.inventory_revision > initial_revision


def test_chatbot_service_refreshes_after_admin_product_update() -> None:
    with TestClient(chatbot_app) as chatbot_client:
        initial_revision = chatbot_app.state.services.inventory_revision

        with TestClient(admin_app) as admin_client:
            login = admin_client.post(
                "/admin/login",
                json={"username": "admin", "password": "admin123"},
            )
            assert login.status_code == 200
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            products = admin_client.get("/products", params={"query": "Cam", "limit": 5})
            product = products.json()["items"][0]
            product_id = product["id"]
            original_best_use = product["best_use"]

            try:
                update = admin_client.patch(
                    f"/admin/products/{product_id}",
                    json={"best_use": original_best_use + " test"},
                    headers=headers,
                )
                assert update.status_code == 200

                response = chatbot_client.post(
                    "/chat",
                    json={
                        "user_id": "tester",
                        "session_id": f"product-refresh-{uuid4()}",
                        "message": "Cam con hang khong?",
                    },
                )
                assert response.status_code == 200
                assert chatbot_app.state.services.inventory_revision > initial_revision
            finally:
                admin_client.patch(
                    f"/admin/products/{product_id}",
                    json={"best_use": original_best_use},
                    headers=headers,
                )
