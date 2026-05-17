from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from backend.core.config import Settings, get_settings


class UserContext(BaseModel):
    sub: str
    role: str


security_scheme = HTTPBearer(auto_error=False)


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("utf-8")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("utf-8"))


def _sign(data: str, secret: str) -> str:
    signature = hmac.new(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).digest()
    return _b64url_encode(signature)


def create_access_token(
    payload: Dict[str, Any], settings: Settings, expires_minutes: Optional[int] = None
) -> str:
    expire_delta = expires_minutes or settings.admin_access_token_expire_minutes
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expire_delta)

    to_encode = payload.copy()
    to_encode["exp"] = int(expires_at.timestamp())

    if settings.admin_jwt_algorithm != "HS256":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Only HS256 is supported in this implementation",
        )

    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(to_encode, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}"
    signature_b64 = _sign(signing_input, settings.admin_jwt_secret)
    return f"{signing_input}.{signature_b64}"


def decode_access_token(token: str, settings: Settings) -> Dict[str, Any]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}"
        expected_signature = _sign(signing_input, settings.admin_jwt_secret)

        if not hmac.compare_digest(expected_signature, signature_b64):
            raise ValueError("Invalid token signature")

        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))

        exp = payload.get("exp")
        if exp is None or int(exp) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("Token expired")

        return payload
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    settings: Settings = Depends(get_settings),
) -> UserContext:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )

    claims = decode_access_token(credentials.credentials, settings)
    subject = claims.get("sub")
    role = claims.get("role")

    if not subject or role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role is required",
        )

    return UserContext(sub=subject, role=role)
