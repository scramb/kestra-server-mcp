"""JWT validation against Entra JWKS endpoint."""

import time
from typing import Any

import httpx
import jwt

from src.config import EntraConfig

_JWKS_CACHE: dict[str, tuple[dict, float]] = {}
JWKS_CACHE_TTL = 3600  # 1 hour


def _fetch_jwks(entra: EntraConfig) -> dict:
    """Fetch JWKS from Entra, using cached data if still valid."""
    now = time.time()
    if entra.jwks_uri in _JWKS_CACHE:
        cached, timestamp = _JWKS_CACHE[entra.jwks_uri]
        if now - timestamp < JWKS_CACHE_TTL:
            return cached

    resp = httpx.get(entra.jwks_uri, timeout=10.0)
    resp.raise_for_status()
    jwks = resp.json()
    _JWKS_CACHE[entra.jwks_uri] = (jwks, now)
    return jwks


def _invalidate_jwks_cache(entra: EntraConfig) -> None:
    _JWKS_CACHE.pop(entra.jwks_uri, None)


def validate_token(token: str, entra: EntraConfig) -> dict[str, Any] | None:
    """Validate a JWT against Entra JWKS.

    Returns parsed claims dict if valid, None if invalid/expired.
    """
    if not token:
        return None

    jwks = _fetch_jwks(entra)
    claims, key_matched = _validate_with_jwks(token, jwks, entra)

    # Only retry with fresh keys if no key matched the token at all
    # (key rotation scenario). Don't retry for expired/bad tokens.
    if claims is not None:
        return claims
    if key_matched:
        return None

    _invalidate_jwks_cache(entra)
    jwks = _fetch_jwks(entra)
    claims, _ = _validate_with_jwks(token, jwks, entra)
    return claims


def _validate_with_jwks(
    token: str, jwks: dict, entra: EntraConfig
) -> tuple[dict[str, Any] | None, bool]:
    """Attempt validation against all keys in JWKS.

    Returns (claims, key_matched) where:
    - claims is the parsed claims dict if valid, None otherwise
    - key_matched is True if at least one key structurally matched the token
      (kid found, correct algorithm) even if the token itself was invalid
    """
    key_matched = False
    for key_dict in jwks.get("keys", []):
        try:
            # Try to get the key header to check kid match
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
                audience=entra.client_id,
                issuer=entra.issuer,
                options={"verify_exp": True, "verify_nbf": True},
            )
            return claims, True
        except jwt.ExpiredSignatureError:
            return None, True
        except jwt.InvalidTokenError:
            continue
    return None, key_matched


def extract_claims(auth_header: str | None, entra: EntraConfig) -> dict[str, Any] | None:
    """Extract and validate claims from Authorization Bearer header."""
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return validate_token(parts[1], entra)
