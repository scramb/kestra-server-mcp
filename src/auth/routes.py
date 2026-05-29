"""Kestra API token management HTTP routes."""

import logging

from starlette.requests import Request
from starlette.responses import JSONResponse

from src.auth.session import extract_user_id, validate_oidc_token
from src.auth.token_store import TokenStore
from src.config import OidcConfig

logger = logging.getLogger("kestra-mcp.auth")


def build_routes(oidc: OidcConfig, token_store: TokenStore):
    """Build handlers for Kestra API token storage, removal, and status."""

    async def store_token(request: Request) -> JSONResponse:
        """Store a Kestra token. Accepts either Bearer auth or explicit user_id."""
        body = await request.json()
        kestra_token = body.get("kestra_token", "")
        if not kestra_token:
            return JSONResponse(
                {"error": "MISSING_TOKEN", "message": "kestra_token field is required"},
                status_code=400,
            )

        user_id = body.get("user_id", "")
        auth_header = request.headers.get("authorization", "")
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            claims = validate_oidc_token(parts[1], oidc)
            if claims:
                user_id = extract_user_id(claims)

        if not user_id:
            return JSONResponse(
                {
                    "error": "USER_ID_REQUIRED",
                    "message": "Provide either a Bearer token or user_id in the request body",
                },
                status_code=400,
            )

        token_store.store_token(user_id, kestra_token)
        logger.info("Stored Kestra token for user %s", user_id)
        return JSONResponse({"status": "stored", "user_id": user_id})

    async def remove_token(request: Request) -> JSONResponse:
        """Remove a user's stored Kestra token. Accepts Bearer auth or explicit user_id."""
        body = await request.json() if request.method == "POST" else {}
        user_id = body.get("user_id", "")

        auth_header = request.headers.get("authorization", "")
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            claims = validate_oidc_token(parts[1], oidc)
            if claims:
                user_id = extract_user_id(claims)

        if not user_id:
            return JSONResponse(
                {
                    "error": "USER_ID_REQUIRED",
                    "message": "Provide either a Bearer token or user_id in the request body",
                },
                status_code=400,
            )

        removed = token_store.remove_token(user_id)
        return JSONResponse(
            {
                "status": "removed" if removed else "not_found",
                "user_id": user_id,
            }
        )

    async def auth_status_page(request: Request) -> JSONResponse:
        """Return current auth status based on Bearer token."""
        auth_header = request.headers.get("authorization", "")
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return JSONResponse(
                {
                    "authenticated": False,
                    "message": "No valid Bearer token",
                }
            )

        claims = validate_oidc_token(parts[1], oidc)
        if not claims:
            return JSONResponse(
                {
                    "authenticated": False,
                    "message": "Invalid or expired token",
                }
            )

        user_id = extract_user_id(claims)
        has_token = token_store.get_token(user_id) is not None
        return JSONResponse(
            {
                "authenticated": True,
                "user_id": user_id,
                "name": claims.get("name", ""),
                "kestra_token_registered": has_token,
            }
        )

    return {
        "store_token": store_token,
        "remove_token": remove_token,
        "auth_status_page": auth_status_page,
    }
