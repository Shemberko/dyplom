"""
Тести для AuthService — JWT генерація і SSO token flow.
Файл: app/services/authorization/auth_service.py

Увага: AuthService успадковує QueryRunner (не приймає client у __init__),
тому мокуємо методи run_one / run_query через patch на рівні instance.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from jose import jwt

from app.services.authorization.auth_service import (
    AuthService,
    SECRET_KEY,
    ALGORITHM,
    JWT_EXPIRY_HOURS,
)


# ---------------------------------------------------------------------------
# create_jwt_token
# ---------------------------------------------------------------------------

def test_create_jwt_token_contains_sub(monkeypatch):
    """JWT має поле 'sub' з user_id."""
    # Патчимо __init__ BaseService, щоб не ліз у Neo4j
    with patch("app.services.authorization.auth_service.QueryRunner.__init__", return_value=None):
        service = AuthService.__new__(AuthService)
        token = service.create_jwt_token("user_123", ["user"])

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "user_123"


def test_create_jwt_token_expires_in_correct_time(monkeypatch):
    """JWT має поле 'exp', яке відповідає JWT_EXPIRY_HOURS від зараз."""
    with patch("app.services.authorization.auth_service.QueryRunner.__init__", return_value=None):
        service = AuthService.__new__(AuthService)
        before = datetime.now(timezone.utc)
        token = service.create_jwt_token("u1", ["user"])
        after = datetime.now(timezone.utc)

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    exp_dt = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    expected_min = before + timedelta(hours=JWT_EXPIRY_HOURS - 1)
    expected_max = after + timedelta(hours=JWT_EXPIRY_HOURS + 1)
    assert expected_min < exp_dt < expected_max


# ---------------------------------------------------------------------------
# exchange_token_for_jwt
# ---------------------------------------------------------------------------

def test_exchange_token_returns_jwt_string():
    """exchange_token_for_jwt → рядок (JWT token)."""
    with patch("app.services.authorization.auth_service.QueryRunner.__init__", return_value=None):
        service = AuthService.__new__(AuthService)
        # Патчимо атомарний обмін токену
        service._neo4j_atomic_exchange_token = MagicMock(
            return_value={"id": "user_42", "roles": ["user"]}
        )
        result = service.exchange_token_for_jwt("some-sso-token")

    assert isinstance(result, str)
    payload = jwt.decode(result, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "user_42"


def test_exchange_token_raises_http_401_on_invalid():
    """Якщо токен не знайдено → HTTPException 401."""
    from fastapi import HTTPException

    with patch("app.services.authorization.auth_service.QueryRunner.__init__", return_value=None):
        service = AuthService.__new__(AuthService)
        service._neo4j_atomic_exchange_token = MagicMock(
            side_effect=ValueError("Token not found or expired.")
        )

        with pytest.raises(HTTPException) as exc_info:
            service.exchange_token_for_jwt("bad-token")

    assert exc_info.value.status_code == 401
