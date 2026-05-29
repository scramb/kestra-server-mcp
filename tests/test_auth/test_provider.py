"""Tests for EntraAuthProvider."""

import pytest
from mcp.server.auth.provider import AuthorizationParams
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyHttpUrl

from src.auth.provider import EntraAuthProvider
from src.auth.stores import (
    AuthCodeStore,
    AuthSessionStore,
    ClientStore,
    RefreshTokenStore,
)
from src.auth.token_factory import create_access_token
from src.config import OidcConfig


@pytest.fixture
def oidc_config():
    return OidcConfig(
        issuer_url="https://entra.example.com/v2.0",
        client_id="entra-app-id",
        client_secret="entra-app-secret",
        authority="https://login.microsoftonline.com/test-tenant",
        jwks_uri="https://login.microsoftonline.com/test-tenant/discovery/v2.0/keys",
        issuer="https://login.microsoftonline.com/test-tenant/v2.0",
        scopes=["openid", "profile"],
    )


@pytest.fixture
def signing_key():
    return b"k" * 32


@pytest.fixture
def callback_url():
    return "http://localhost:8081/oauth/entra-callback"


@pytest.fixture
def registered_client():
    return OAuthClientInformationFull(
        client_id="reg-client-1",
        redirect_uris=[AnyHttpUrl("http://localhost:9999/callback")],
        token_endpoint_auth_method="client_secret_post",
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
    )


@pytest.fixture
def provider(oidc_config, signing_key, callback_url):
    return EntraAuthProvider(
        client_store=ClientStore(),
        auth_session_store=AuthSessionStore(),
        auth_code_store=AuthCodeStore(),
        refresh_token_store=RefreshTokenStore(),
        oidc_config=oidc_config,
        token_signing_key=signing_key,
        access_token_ttl=3600,
        entra_callback_url=callback_url,
    )


class TestClientManagement:
    async def test_register_and_get(self, provider, registered_client):
        await provider.register_client(registered_client)
        retrieved = await provider.get_client(registered_client.client_id)
        assert retrieved == registered_client

    async def test_get_unknown_returns_none(self, provider):
        assert await provider.get_client("nonexistent") is None


class TestAuthorize:
    async def test_authorize_redirects_to_entra(self, provider, registered_client):
        await provider.register_client(registered_client)
        params = AuthorizationParams(
            state="mcp-state",
            scopes=["kestra.read"],
            code_challenge="pkce-challenge",
            redirect_uri=AnyHttpUrl("http://localhost:9999/callback"),
            redirect_uri_provided_explicitly=True,
        )
        url = await provider.authorize(registered_client, params)
        assert "login.microsoftonline.com" in url
        assert "oauth2/v2.0/authorize" in url
        assert "entra-app-id" in url
        assert "response_type=code" in url


class TestAuthorizationCodeExchange:
    async def test_full_code_exchange(self, provider, registered_client, signing_key):
        await provider.register_client(registered_client)

        # Simulate what the Entra callback does: store an auth code
        provider._codes.store(
            code="our-auth-code",
            client_id=registered_client.client_id,
            entra_user_id="entra-user-sub",
            code_challenge="pkce-challenge",
            redirect_uri="http://localhost:9999/callback",
            scopes=["kestra.read"],
        )

        # Load the auth code
        auth_code = await provider.load_authorization_code(registered_client, "our-auth-code")
        assert auth_code is not None
        assert auth_code.entra_user_id == "entra-user-sub"
        assert auth_code.scopes == ["kestra.read"]

        # Exchange for tokens
        result = await provider.exchange_authorization_code(registered_client, auth_code)
        assert isinstance(result, OAuthToken)
        assert result.token_type == "Bearer"
        assert result.access_token
        assert result.refresh_token
        assert result.expires_in == 3600

        # Validate the access token
        payload = await provider.load_access_token(result.access_token)
        assert payload is not None
        assert payload.entra_user_id == "entra-user-sub"
        assert payload.client_id == registered_client.client_id

    async def test_load_code_wrong_client(self, provider, registered_client):
        await provider.register_client(registered_client)
        provider._codes.store(
            code="code-1",
            client_id="other-client",
            entra_user_id="user-1",
            code_challenge="ch",
            redirect_uri="http://r",
            scopes=[],
        )
        result = await provider.load_authorization_code(registered_client, "code-1")
        assert result is None

    async def test_load_code_invalid(self, provider, registered_client):
        await provider.register_client(registered_client)
        result = await provider.load_authorization_code(registered_client, "bad-code")
        assert result is None


class TestAccessTokenValidation:
    async def test_valid_tokens_validates(self, provider, registered_client, signing_key):
        token = create_access_token(
            entra_user_id="user-1",
            client_id="c1",
            scopes=["kestra.read"],
            signing_key=signing_key,
        )
        access_token = await provider.load_access_token(token)
        assert access_token is not None
        assert access_token.entra_user_id == "user-1"

    async def test_invalid_token_returns_none(self, provider):
        result = await provider.load_access_token("garbage")
        assert result is None

    async def test_wrong_key_token_returns_none(self, provider, registered_client):
        token = create_access_token(
            entra_user_id="user-1",
            client_id="c1",
            scopes=[],
            signing_key=b"wrong-key-32-bytes-long!!",
        )
        result = await provider.load_access_token(token)
        assert result is None


class TestRefreshTokenFlow:
    async def test_store_and_load_refresh(self, provider, registered_client):
        await provider.register_client(registered_client)
        provider._refresh.store(
            "raw-refresh", registered_client.client_id, "user-1", ["kestra.read"]
        )

        rt = await provider.load_refresh_token(registered_client, "raw-refresh")
        assert rt is not None
        assert rt.entra_user_id == "user-1"
        assert rt.scopes == ["kestra.read"]

    async def test_exchange_refresh_rotates_tokens(self, provider, registered_client):
        await provider.register_client(registered_client)
        provider._refresh.store(
            "old-refresh", registered_client.client_id, "user-1", ["kestra.read"]
        )

        rt = await provider.load_refresh_token(registered_client, "old-refresh")
        result = await provider.exchange_refresh_token(registered_client, rt, ["kestra.read"])

        assert result.access_token
        assert result.refresh_token
        assert result.refresh_token != "old-refresh"
        # Old token should be gone
        assert provider._refresh.load("old-refresh") is None
        # New token should be stored
        assert provider._refresh.load(result.refresh_token) is not None

    async def test_load_refresh_wrong_client(self, provider, registered_client):
        await provider.register_client(registered_client)
        provider._refresh.store("rt", "other-client", "user-1", [])
        result = await provider.load_refresh_token(registered_client, "rt")
        assert result is None


class TestRevoke:
    async def test_revoke_refresh(self, provider, registered_client):
        provider._refresh.store("rt", registered_client.client_id, "user-1", [])
        rt = await provider.load_refresh_token(registered_client, "rt")
        await provider.revoke_token(rt)
        assert provider._refresh.load("rt") is None
