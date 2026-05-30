"""OIDC session management and per-request Kestra token resolution."""

import logging
import time
from contextvars import ContextVar
from typing import Any

import httpx
import jwt

from src.auth.token_store import TokenStore
from src.config import OidcConfig

logger = logging.getLogger("kestra-mcp.auth")

current_user_id: ContextVar[str] = ContextVar("current_user_id", default="")

_JWKS_CACHE: dict[str, tuple[dict, float]] = {}
JWKS_CACHE_TTL = 3600

# Set at startup; resolved at access time per-request to avoid ContextVar staleness
# in long-lived MCP server background tasks.
_token_store: TokenStore | None = None


def set_session_token_store(store: TokenStore) -> None:
    global _token_store
    _token_store = store


def get_current_token() -> str:
    user_id = current_user_id.get()
    if not user_id or _token_store is None:
        return ""
    return _token_store.get_token(user_id) or ""


def validate_oidc_token(token: str, oidc: OidcConfig) -> dict[str, Any] | None:
    """Validate an OIDC JWT against the provider's JWKS and return claims, or None."""
    if not token:
        return None

    jwks = _fetch_jwks(oidc)
    claims, key_matched = _validate_with_jwks(token, jwks, oidc)

    if claims is not None:
        return claims
    if key_matched:
        return None

    _invalidate_jwks_cache(oidc)
    jwks = _fetch_jwks(oidc)
    claims, _ = _validate_with_jwks(token, jwks, oidc)
    return claims


def _fetch_jwks(oidc: OidcConfig) -> dict:
    now = time.time()
    if oidc.jwks_uri in _JWKS_CACHE:
        cached, timestamp = _JWKS_CACHE[oidc.jwks_uri]
        if now - timestamp < JWKS_CACHE_TTL:
            return cached

    resp = httpx.get(oidc.jwks_uri, timeout=10.0)
    resp.raise_for_status()
    jwks = resp.json()
    _JWKS_CACHE[oidc.jwks_uri] = (jwks, now)
    return jwks


def _invalidate_jwks_cache(oidc: OidcConfig) -> None:
    _JWKS_CACHE.pop(oidc.jwks_uri, None)


def _validate_with_jwks(
    token: str, jwks: dict, oidc: OidcConfig
) -> tuple[dict[str, Any] | None, bool]:
    key_matched = False
    for key_dict in jwks.get("keys", []):
        try:
            header = jwt.get_unverified_header(token)
            if header.get("kid") == key_dict.get("kid"):
                key_matched = True
        except jwt.InvalidTokenError:
            pass

        try:
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_dict)
            claims = jwt.decode(
                token,
                key=public_key,
                algorithms=["RS256"],
                audience=oidc.client_id,
                issuer=oidc.issuer,
                options={"verify_exp": True, "verify_nbf": True},
            )
            return claims, True
        except jwt.ExpiredSignatureError:
            return None, True
        except jwt.InvalidTokenError:
            continue
    return None, key_matched


def extract_user_id(claims: dict) -> str:
    """Extract user identifier from OIDC claims. Tries 'sub' first, then common alternatives."""
    return claims.get("sub") or claims.get("oid") or claims.get("preferred_username") or ""


class AuthMiddleware:
    """Starlette ASGI middleware that validates the MCP access token per request.

    Extracts our self-signed Bearer JWT from the Authorization header, validates
    it via the OAuth provider, and sets the current_user_id context var.
    Kestra token resolution happens at access time via get_current_token().
    """

    def __init__(self, app, provider, token_store: TokenStore, public_url: str = ""):
        self.app = app
        self.provider = provider
        self.token_store = token_store
        self._public_url = public_url

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path", "").rstrip("/") != "/mcp":
            await self.app(scope, receive, send)
            return

        auth_header = _get_header(scope, "authorization")
        bearer_token = _extract_bearer(auth_header)

        if bearer_token:
            access_token = await self.provider.load_access_token(bearer_token)
            if access_token is not None and access_token.entra_user_id:
                uid_token = current_user_id.set(access_token.entra_user_id)
                try:
                    await self.app(scope, receive, send)
                finally:
                    current_user_id.reset(uid_token)
                return
            # Invalid token — return OAuth discovery

        # Return MCP OAuth 2.0 discovery response (RFC 9728 §3)
        from starlette.responses import JSONResponse

        public_url = self._public_url or f"https://{_get_header(scope, 'host')}"
        www_auth = f'Bearer resource_metadata="{public_url}/mcp", auth_server="{public_url}"'
        response = JSONResponse(
            {"error": "UNAUTHENTICATED",
             "message": "Valid Bearer token required. See WWW-Authenticate header for OAuth metadata."},
            status_code=401,
            headers={"WWW-Authenticate": www_auth},
        )
        await response(scope, receive, send)


def _get_header(scope, name: str) -> str | None:
    name_lower = name.lower().encode()
    for key, value in scope.get("headers", []):
        if key.lower() == name_lower:
            return value.decode()
    return None


def _extract_bearer(header: str | None) -> str | None:
    if not header:
        return None
    parts = header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None
