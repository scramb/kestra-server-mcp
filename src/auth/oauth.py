"""Entra OAuth 2.1 authentication with MSAL and session management."""

import msal

from src.config import EntraConfig


class SessionManager:
    """In-memory session store with token refresh support."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}
        self._msal_apps: dict[str, msal.ClientApplication] = {}

    def _get_msal_app(self, entra: EntraConfig) -> msal.ClientApplication:
        key = entra.client_id
        if key not in self._msal_apps:
            self._msal_apps[key] = msal.ConfidentialClientApplication(
                client_id=entra.client_id,
                client_credential=entra.client_secret,
                authority=entra.authority,
            )
        return self._msal_apps[key]

    def build_auth_url(self, entra: EntraConfig, state: str = "") -> str:
        """Build the Entra authorization URL for the OAuth flow."""
        app = self._get_msal_app(entra)
        return app.get_authorization_request_url(
            scopes=["openid", "profile"],
            redirect_uri=entra.redirect_uri,
            state=state or None,
        )

    def acquire_token(
        self, entra: EntraConfig, auth_code: str
    ) -> dict | None:
        """Exchange authorization code for tokens. Returns token dict or None."""
        app = self._get_msal_app(entra)
        result = app.acquire_token_by_authorization_code(
            code=auth_code,
            scopes=["openid", "profile"],
            redirect_uri=entra.redirect_uri,
        )
        if "error" in result:
            return None
        return result

    def create_session(
        self, claims: dict, token_result: dict, entra: EntraConfig
    ) -> str:
        """Create a new session from validated claims and token result.

        Returns the session identity key (sub claim).
        """
        identity = claims.get("sub", "")
        if not identity:
            raise ValueError("Token claims missing 'sub' field")

        self._sessions[identity] = {
            "claims": claims,
            "access_token": token_result["access_token"],
            "refresh_token": token_result.get("refresh_token"),
            "id_token": token_result.get("id_token"),
            "tenant_id": claims.get("tid", entra.tenant_id),
        }
        return identity

    def get_session(self, identity: str) -> dict | None:
        """Get session by identity key. Returns None if not found."""
        return self._sessions.get(identity)

    def remove_session(self, identity: str) -> None:
        """Invalidate a session."""
        self._sessions.pop(identity, None)

    def refresh_session(self, identity: str, entra: EntraConfig) -> dict | None:
        """Attempt silent token refresh. Returns updated token dict or None."""
        session = self._sessions.get(identity)
        if not session or not session.get("refresh_token"):
            return None

        app = self._get_msal_app(entra)
        result = app.acquire_token_by_refresh_token(
            refresh_token=session["refresh_token"],
            scopes=["openid", "profile"],
        )
        if "error" in result:
            self.remove_session(identity)
            return None

        session["access_token"] = result["access_token"]
        if "refresh_token" in result:
            session["refresh_token"] = result["refresh_token"]
        return result
