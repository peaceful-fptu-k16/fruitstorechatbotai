from fastapi.testclient import TestClient

from backend.main import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_chat_recommendation_route() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={
                "user_id": "tester",
                "session_id": "session-1",
                "message": "Gợi ý trái ít chua",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "recommendation"
    assert isinstance(payload["products"], list)


def test_chat_available_products_tracks_requested_fruit_context() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={
                "user_id": "tester",
                "session_id": "session-available-1",
                "message": "Xoài hôm nay có gì ngon không?",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "available_products"
    assert "Xoài" in payload["answer"]
    assert ("giá" in payload["answer"]) or ("còn" in payload["answer"])


def test_chat_recommendation_respects_requested_entity() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={
                "user_id": "tester",
                "session_id": "session-cam-1",
                "message": "Tôi muốn mua cam",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "recommendation"
    assert "cam" in payload["answer"].lower()
    assert payload["products"]
    assert "cam" in payload["products"][0]["name"].lower()


def test_admin_update_stock_idempotent() -> None:
    with TestClient(app) as client:
        login = client.post(
            "/admin/login",
            json={"username": "admin", "password": "admin123"},
        )
        token = login.json()["access_token"]

        headers = {
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "test-idempotency-key",
        }
        payload = {"updates": [{"product_id": 1, "operation": "inc", "quantity": 1}]}

        first = client.post("/admin/update-stock", json=payload, headers=headers)
        second = client.post("/admin/update-stock", json=payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["idempotency_key"] == second.json()["idempotency_key"]
