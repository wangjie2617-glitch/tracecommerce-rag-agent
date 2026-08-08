"""Password and JWT unit tests."""

from datetime import timedelta
from uuid import uuid4

import jwt
import pytest

from app.config import Settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_bcrypt_hash_and_verify() -> None:
    password_hash = hash_password("SecurePass123!")
    assert password_hash != "SecurePass123!"
    assert password_hash.startswith("$2")
    assert verify_password("SecurePass123!", password_hash)
    assert not verify_password("wrong", password_hash)


def test_jwt_round_trip() -> None:
    settings = Settings(
        jwt_secret_key="test-secret-at-least-thirty-two-characters",
        jwt_access_token_expire_minutes=5,
    )
    user_id = uuid4()
    token, expires_in = create_access_token(user_id, ["operator"], settings=settings)
    payload = decode_access_token(token, settings=settings)
    assert payload["sub"] == str(user_id)
    assert payload["roles"] == ["operator"]
    assert expires_in == int(timedelta(minutes=5).total_seconds())


def test_invalid_jwt_is_rejected() -> None:
    settings = Settings(jwt_secret_key="test-secret-at-least-thirty-two-characters")
    bad_token = jwt.encode({"sub": str(uuid4()), "type": "wrong"}, settings.jwt_secret_key)
    with pytest.raises(AuthenticationError):
        decode_access_token(bad_token, settings=settings)


def test_settings_accept_comma_separated_lists(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://a.example,http://b.example")
    monkeypatch.setenv(
        "SHOPIFY_ALLOWED_PREFIXES",
        "https://help.shopify.com/en/manual/international,"
        "https://help.shopify.com/en/manual/taxes",
    )
    settings = Settings(_env_file=None)
    assert settings.cors_origins == ["http://a.example", "http://b.example"]
    assert len(settings.shopify_allowed_prefixes) == 2
