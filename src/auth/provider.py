"""EntraAuthProvider — implements OAuthAuthorizationServerProvider for Entra ID proxy.

Our server acts as the OAuth Authorization Server. The MCP client
registers with us (DCR), we redirect the user to Entra for authentication,
and we issue our own self-signed JWT access tokens carrying the Entra
user identity.
"""

from urllib.parse import urlencode

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    RefreshToken,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyHttpUrl

from src.auth.stores import AuthCodeStore, AuthSessionStore, ClientStore, RefreshTokenStore
from src.auth.token_factory import (
    create_access_token,
    create_refresh_token,
    validate_access_token,
)
from src.config import OidcConfig


class KestraAuthorizationCode(AuthorizationCode):
    entra_user_id: str = ""


class KestraRefreshToken(RefreshToken):
    entra_user_id: str = ""


class KestraAccessToken(AccessToken):
    entra_user_id: str = ""


class EntraAuthProvider:
    """OAuth Authorization Server provider that proxies auth to Entra ID.

    Implements the OAuthAuthorizationServerProvider protocol from the MCP SDK.
    """

    def __init__(
        self,
        client_store: ClientStore,
        auth_session_store: AuthSessionStore,
        auth_code_store: AuthCodeStore,
        refresh_token_store: RefreshTokenStore,
        oidc_config: OidcConfig,
        token_signing_key: bytes,
        access_token_ttl: int,
        entra_callback_url: str,
    ):
        self._clients = client_store
        self._sessions = auth_session_store
        self._codes = auth_code_store
        self._refresh = refresh_token_store
        self._oidc = oidc_config
        self._signing_key = token_signing_key
        self._token_ttl = access_token_ttl
        self._callback_url = entra_callback_url

    # --- Client management ---

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self._clients.put(client_info)

    # --- Authorization ---

    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams,
    ) -> str:
        if client.client_id is None:
            raise AuthorizeError("invalid_request", "Client has no ID")

        entra_state = self._sessions.create(
            client_id=client.client_id,
            original_state=params.state,
            redirect_uri=str(params.redirect_uri),
            code_challenge=params.code_challenge,
            scopes=params.scopes,
        )

        entra_params = {
            "client_id": self._oidc.client_id,
            "response_type": "code",
            "redirect_uri": self._callback_url,
            "scope": " ".join(self._oidc.scopes),
            "state": entra_state,
            "response_mode": "query",
        }
        return f"{self._oidc.authority}/oauth2/v2.0/authorize?{urlencode(entra_params)}"

    # --- Authorization codes ---

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> KestraAuthorizationCode | None:
        entry = self._codes.consume(authorization_code)
        if entry is None:
            return None
        if entry["client_id"] != client.client_id:
            return None
        return KestraAuthorizationCode(
            code=authorization_code,
            client_id=entry["client_id"],
            entra_user_id=entry["entra_user_id"],
            code_challenge=entry["code_challenge"],
            redirect_uri=AnyHttpUrl(entry["redirect_uri"]),
            scopes=entry["scopes"],
            expires_at=entry["expires_at"],
            redirect_uri_provided_explicitly=True,
        )

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: KestraAuthorizationCode,
    ) -> OAuthToken:
        access_token_str = create_access_token(
            entra_user_id=authorization_code.entra_user_id,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            signing_key=self._signing_key,
            ttl_seconds=self._token_ttl,
        )
        raw_refresh, _ = create_refresh_token()
        self._refresh.store(
            raw_refresh,
            client.client_id,
            authorization_code.entra_user_id,
            authorization_code.scopes,
        )
        return OAuthToken(
            access_token=access_token_str,
            token_type="Bearer",
            expires_in=self._token_ttl,
            scope=" ".join(authorization_code.scopes) if authorization_code.scopes else None,
            refresh_token=raw_refresh,
        )

    # --- Refresh tokens ---

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> KestraRefreshToken | None:
        entry = self._refresh.load(refresh_token)
        if entry is None:
            return None
        if entry["client_id"] != client.client_id:
            return None
        return KestraRefreshToken(
            token=refresh_token,
            client_id=entry["client_id"],
            scopes=entry["scopes"],
            entra_user_id=entry["entra_user_id"],
            expires_at=entry["expires_at"],
        )

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: KestraRefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        new_access = create_access_token(
            entra_user_id=refresh_token.entra_user_id,
            client_id=client.client_id,
            scopes=scopes,
            signing_key=self._signing_key,
            ttl_seconds=self._token_ttl,
        )
        new_raw, _ = create_refresh_token()
        self._refresh.rotate(refresh_token.token, new_raw)
        return OAuthToken(
            access_token=new_access,
            token_type="Bearer",
            expires_in=self._token_ttl,
            scope=" ".join(scopes) if scopes else None,
            refresh_token=new_raw,
        )

    # --- Access tokens ---

    async def load_access_token(self, token: str) -> KestraAccessToken | None:
        payload = validate_access_token(token, self._signing_key)
        if payload is None:
            return None
        return KestraAccessToken(
            token=token,
            client_id=payload["client_id"],
            scopes=payload["scopes"],
            entra_user_id=payload["sub"],
            expires_at=payload["exp"],
        )

    # --- Revocation ---

    async def revoke_token(self, token: KestraAccessToken | KestraRefreshToken) -> None:
        if isinstance(token, KestraRefreshToken):
            self._refresh.revoke(token.token)
