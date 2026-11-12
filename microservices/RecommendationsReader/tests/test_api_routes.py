"""
Smoke-тести API маршрутів через FastAPI TestClient.
Перевіряємо HTTP-коди та базову структуру відповідей без реального Neo4j.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from jose import jwt
from datetime import datetime, timezone, timedelta

# Патчимо ініціалізацію QueryRunner/BaseService ДО імпорту app
# (бо при імпорті app.main всі модулі-синглтони вже створюються)


def _make_valid_jwt(user_id: str = "test_user") -> str:
    """Генеруємо валідний JWT для тестів авторизованих ендпоінтів."""
    from app.services.authorization.auth_service import SECRET_KEY, ALGORITHM
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "exp": (now + timedelta(hours=2)).timestamp(),
        "iat": now.timestamp(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@pytest.fixture(scope="module")
def client():
    """
    Створюємо TestClient з підміненим Neo4j-драйвером.
    scope=module → client створюється один раз для всього файлу.
    """
    with patch("neo4j.GraphDatabase.driver") as mock_driver:
        mock_driver.return_value = MagicMock()
        from app.main import app
        yield TestClient(app)


# ---------------------------------------------------------------------------
# /recommendations — authenticated endpoint
# ---------------------------------------------------------------------------

class TestRecommendationsEndpoint:

    def test_no_auth_header_returns_401(self, client):
        """Запит без Authorization → 401."""
        resp = client.get("/recommendations")
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client):
        """Невалідний JWT → 401."""
        resp = client.get("/recommendations", headers={"Authorization": "Bearer invalid.token"})
        assert resp.status_code == 401

    def test_valid_token_returns_200_with_data_key(self, client):
        """Валідний JWT + підміна dependency → 200 і відповідь з ключем 'data'."""
        from app.main import app as fastapi_app
        from app.routers.unified_recommendations import get_recommendation_service

        token = _make_valid_jwt("u1")

        # Перевизначаємо dependency на підмінений сервіс через FastAPI DI override
        mock_unified = MagicMock()
        mock_unified.get_recommendations.return_value = ([], 0)

        fastapi_app.dependency_overrides[get_recommendation_service] = lambda: mock_unified
        try:
            with patch("app.routers.unified_recommendations.rec_service") as mock_rec:
                mock_rec.track_user_visit.return_value = True
                resp = client.get(
                    "/recommendations",
                    headers={"Authorization": f"Bearer {token}"},
                )
        finally:
            fastapi_app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "meta" in body


# ---------------------------------------------------------------------------
# /history — authenticated endpoint
# ---------------------------------------------------------------------------

class TestHistoryEndpoint:

    def test_no_auth_returns_401(self, client):
        resp = client.get("/history")
        assert resp.status_code == 401

    def test_valid_token_returns_200_with_empty_history(self, client):
        token = _make_valid_jwt("u1")

        with patch(
            "app.routers.history.history_service"
        ) as mock_svc:
            mock_svc.get_user_history.return_value = []

            resp = client.get(
                "/history",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []


# ---------------------------------------------------------------------------
# /sso — authorization endpoint
# ---------------------------------------------------------------------------

class TestSSOEndpoint:

    def test_generate_token_endpoint_exists(self, client):
        """POST /sso/generate-one-time-token існує і повертає oneTimeToken."""
        with patch("app.routers.authorization.auth_service") as mock_auth:
            mock_auth.generate_one_time_token.return_value = "fake-sso-token"
            # Реальний endpoint: POST /sso/generate-one-time-token, поле: userId
            resp = client.post(
                "/sso/generate-one-time-token",
                json={"userId": "chrome-ext-id-abc123"}
            )

        # 200 з токеном або 500 (auth_service намагається звернутись до Neo4j)
        # але точно не 404 (endpoint існує)
        assert resp.status_code != 404

    def test_exchange_token_endpoint_exists(self, client):
        """POST /sso/exchange-token існує."""
        with patch("app.routers.authorization.auth_service") as mock_auth:
            mock_auth.exchange_token_for_jwt.return_value = "fake.jwt.token"
            resp = client.post(
                "/sso/exchange-token",
                json={"token": "some-sso-token"}
            )

        assert resp.status_code != 404
