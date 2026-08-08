"""bcrypt password hashing and JWT access tokens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import jwt
from jwt import InvalidTokenError

from app.config import Settings, get_settings
from app.core.exceptions import AuthenticationError


def hash_password(password: str) -> str:
    """Hash a UTF-8 password with bcrypt."""
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        raise ValueError("bcrypt 密码编码后不能超过 72 字节")
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Safely compare a plain password with a bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    user_id: UUID,
    roles: list[str],
    *,
    settings: Settings | None = None,
) -> tuple[str, int]:
    """Create a signed short-lived JWT and return token plus lifetime seconds."""
    config = settings or get_settings()
    expires_delta = timedelta(minutes=config.jwt_access_token_expire_minutes)
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "roles": roles,
        "iat": now,
        "exp": now + expires_delta,
        "type": "access",
    }
    token = jwt.encode(payload, config.jwt_secret_key, algorithm=config.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str, *, settings: Settings | None = None) -> dict:
    """Validate and decode an access JWT."""
    config = settings or get_settings()
    try:
        payload = jwt.decode(token, config.jwt_secret_key, algorithms=[config.jwt_algorithm])
    except InvalidTokenError as exc:
        raise AuthenticationError("Access Token 无效或已过期") from exc
    if payload.get("type") != "access" or not payload.get("sub"):
        raise AuthenticationError("Access Token 类型无效")
    return payload

