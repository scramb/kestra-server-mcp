"""Self-signed HS256 JWT creation and validation for access tokens.

No PyJWT dependency — uses stdlib hmac + hashlib + base64.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any


def create_access_token(
    *,
    entra_user_id: str,
    client_id: str,
    scopes: list[str],
    signing_key: bytes,
    ttl_seconds: int = 3600,
) -> str:
    """Create a self-signed JWT (HS256) access token carrying the Entra user identity."""
    now = int(time.time())
    payload = {
        "sub": entra_user_id,
        "client_id": client_id,
        "scopes": scopes,
        "iat": now,
        "exp": now + ttl_seconds,
        "jti": secrets.token_hex(16),
    }
    header_b64 = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}))
    payload_b64 = _b64url(json.dumps(payload))
    message = f"{header_b64}.{payload_b64}"
    sig = hmac.new(signing_key, message.encode(), hashlib.sha256).digest()
    return f"{message}.{_b64url_bytes(sig)}"


def validate_access_token(token: str, signing_key: bytes) -> dict[str, Any] | None:
    """Decode and validate a self-signed JWT. Returns payload or None."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    header_b64, payload_b64, sig_b64 = parts

    message = f"{header_b64}.{payload_b64}"
    expected_sig = hmac.new(signing_key, message.encode(), hashlib.sha256).digest()
    try:
        actual_sig = _b64url_decode(sig_b64)
    except Exception:
        return None
    if not hmac.compare_digest(expected_sig, actual_sig):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_b64).decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if payload.get("exp", 0) < time.time():
        return None
    return payload


def create_refresh_token() -> tuple[str, str]:
    """Generate a random refresh token. Returns (raw_token, sha256_hash)."""
    raw = secrets.token_hex(32)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def _b64url(s: str) -> str:
    return _b64url_bytes(s.encode())


def _b64url_bytes(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(data: str) -> bytes:
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)
