"""Entra ID OAuth callback handler.

Receives the redirect from Entra after user authentication, exchanges the
Entra authorization code for tokens, extracts the user identity, generates
our own authorization code, and redirects to the MCP client's redirect_uri.
"""

import logging
import secrets
from urllib.parse import urlencode

import msal
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from src.auth.session import extract_user_id, validate_oidc_token
from src.auth.stores import AuthCodeStore, AuthSessionStore
from src.config import OidcConfig

logger = logging.getLogger("kestra-mcp.auth")

# Scopes that MSAL reserves and rejects in acquire_token_by_authorization_code
_RESERVED_SCOPES = {"openid", "profile", "offline_access"}


def create_entra_callback_handler(
    oidc: OidcConfig,
    auth_session_store: AuthSessionStore,
    auth_code_store: AuthCodeStore,
):
    async def handle(request: Request):
        entra_code = request.query_params.get("code")
        entra_state = request.query_params.get("state")
        error = request.query_params.get("error")

        if error or not entra_code:
            return JSONResponse(
                {"error": "ENTRA_AUTH_FAILED", "message": error or "No code provided"},
                status_code=400,
            )

        session = auth_session_store.consume(entra_state)
        if session is None:
            return JSONResponse(
                {"error": "SESSION_EXPIRED",
                 "message": "Authentication session expired or invalid"},
                status_code=400,
            )

        app = msal.ConfidentialClientApplication(
            client_id=oidc.client_id,
            client_credential=oidc.client_secret,
            authority=oidc.authority,
        )
        result = app.acquire_token_by_authorization_code(
            code=entra_code,
            scopes=[s for s in oidc.scopes if s not in _RESERVED_SCOPES],
            redirect_uri=str(request.url_for("entra_callback")),
        )
        if "error" in result:
            logger.error("Entra token exchange failed: %s", result.get("error"))
            return JSONResponse(
                {"error": "ENTRA_TOKEN_EXCHANGE_FAILED",
                 "message": result.get("error_description", "Token exchange failed")},
                status_code=400,
            )

        id_token = result.get("id_token", "")
        claims = validate_oidc_token(id_token, oidc)
        if not claims:
            access_token = result.get("access_token", "")
            claims = validate_oidc_token(access_token, oidc)
        if not claims:
            return JSONResponse(
                {"error": "TOKEN_VALIDATION_FAILED",
                 "message": "Could not validate tokens from Entra"},
                status_code=400,
            )

        user_id = extract_user_id(claims)
        if not user_id:
            return JSONResponse(
                {"error": "USER_IDENTITY_MISSING",
                 "message": "Could not extract user identity from Entra tokens"},
                status_code=400,
            )

        our_code = secrets.token_urlsafe(32)
        auth_code_store.store(
            code=our_code,
            client_id=session["client_id"],
            entra_user_id=user_id,
            code_challenge=session["code_challenge"],
            redirect_uri=session["redirect_uri"],
            scopes=session["scopes"],
        )

        redirect_params = {"code": our_code}
        if session["original_state"]:
            redirect_params["state"] = session["original_state"]

        redirect_url = f"{session['redirect_uri']}?{urlencode(redirect_params)}"
        return RedirectResponse(redirect_url, status_code=302)

    return handle
