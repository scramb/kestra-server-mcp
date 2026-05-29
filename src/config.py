"""Environment-based configuration for Kestra MCP server."""

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


@dataclass(frozen=True)
class OidcConfig:
    """Generic OIDC provider configuration.

    Supports any OIDC-compliant identity provider (Entra, Google, Okta, Keycloak, etc.).
    Backward-compatible with ENTRA_* env vars.
    """

    issuer_url: str
    client_id: str
    client_secret: str
    authority: str
    jwks_uri: str
    issuer: str  # the 'iss' claim value to validate
    scopes: list[str]  # scopes sent to the IdP authorize endpoint (e.g. openid profile)

    @classmethod
    def from_env(cls) -> "OidcConfig":
        issuer_url = os.getenv("OIDC_ISSUER_URL", "")
        authority = os.getenv("OIDC_AUTHORITY", "")
        client_id = os.getenv("OIDC_CLIENT_ID", "")
        client_secret = os.getenv("OIDC_CLIENT_SECRET", "")

        # Backward compatibility: ENTRA_* env vars
        entra_tenant = os.getenv("ENTRA_TENANT_ID", "")
        if entra_tenant:
            if not issuer_url:
                issuer_url = f"https://login.microsoftonline.com/{entra_tenant}/v2.0"
            if not authority:
                authority = f"https://login.microsoftonline.com/{entra_tenant}"
            client_id = client_id or os.getenv("ENTRA_CLIENT_ID", "")
            client_secret = client_secret or os.getenv("ENTRA_CLIENT_SECRET", "")

        if not issuer_url:
            raise ValueError(
                "OIDC_ISSUER_URL is required (or ENTRA_TENANT_ID for backward compat)"
            )
        if not client_id:
            raise ValueError(
                "OIDC_CLIENT_ID is required (or ENTRA_CLIENT_ID for backward compat)"
            )
        if not client_secret:
            raise ValueError(
                "OIDC_CLIENT_SECRET is required (or ENTRA_CLIENT_SECRET for backward compat)"
            )

        if not authority:
            authority = issuer_url.rstrip("/")

        jwks_uri = os.getenv("OIDC_JWKS_URI", "")
        if not jwks_uri:
            jwks_uri = f"{authority}/discovery/v2.0/keys"

        # The 'iss' claim to validate in tokens (defaults to issuer_url)
        issuer = os.getenv("OIDC_ISSUER", issuer_url)

        scopes_str = os.getenv("OIDC_SCOPES", "openid profile")
        scopes = scopes_str.split()

        return cls(
            issuer_url=issuer_url,
            client_id=client_id,
            client_secret=client_secret,
            authority=authority,
            jwks_uri=jwks_uri,
            issuer=issuer,
            scopes=scopes,
        )


@dataclass(frozen=True)
class KestraConfig:
    api_url: str
    tenant: str = ""
    verify_ssl: bool = True


@dataclass(frozen=True)
class ServerConfig:
    transport: str  # "http" (Streamable HTTP), "sse" (deprecated alias for http), or "stdio"
    host: str = "localhost"
    port: int = 8081


@dataclass(frozen=True)
class Config:
    oidc: OidcConfig
    kestra: KestraConfig
    server: ServerConfig
    encryption_key: bytes


def load_config() -> Config:
    oidc = OidcConfig.from_env()

    raw_url = _require("KESTRA_API_URL").rstrip("/")
    api_url = re.sub(r"(?<!:)//+", "/", raw_url)

    tenant = os.getenv("KESTRA_TENANT", "").strip("/")
    kestra = KestraConfig(
        api_url=api_url,
        tenant=tenant,
        verify_ssl=os.getenv("KESTRA_VERIFY_SSL", "true").lower() != "false",
    )

    server = ServerConfig(
        transport=os.getenv("KESTRA_MCP_TRANSPORT", "http").lower(),
        host=os.getenv("KESTRA_MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("KESTRA_MCP_PORT", "8081")),
    )

    if server.transport not in ("http", "sse", "stdio"):
        raise ValueError(
            f"KESTRA_MCP_TRANSPORT must be 'http', 'sse', or 'stdio', got: {server.transport}"
        )

    encryption_key_b64 = _require("ENCRYPTION_KEY")
    encryption_key = _decode_encryption_key(encryption_key_b64)

    return Config(
        oidc=oidc, kestra=kestra, server=server, encryption_key=encryption_key
    )


def _decode_encryption_key(b64_key: str) -> bytes:
    import base64

    key = base64.urlsafe_b64decode(b64_key)
    if len(key) != 32:
        raise ValueError("ENCRYPTION_KEY must decode to 32 bytes")
    return key


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Required environment variable {key} is not set")
    return value
