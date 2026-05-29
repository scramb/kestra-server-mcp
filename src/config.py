"""Environment-based configuration for Kestra MCP server."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


@dataclass(frozen=True)
class EntraConfig:
    tenant_id: str
    client_id: str
    client_secret: str
    authority: str = field(init=False)
    redirect_uri: str = "http://127.0.0.1:8081/oauth/callback"
    jwks_uri: str = field(init=False)
    issuer: str = field(init=False)

    def __post_init__(self):
        object.__setattr__(
            self,
            "authority",
            f"https://login.microsoftonline.com/{self.tenant_id}",
        )
        object.__setattr__(
            self,
            "jwks_uri",
            f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys",
        )
        object.__setattr__(
            self,
            "issuer",
            f"https://login.microsoftonline.com/{self.tenant_id}/v2.0",
        )


@dataclass(frozen=True)
class KestraConfig:
    api_url: str
    api_token: str = ""


@dataclass(frozen=True)
class ServerConfig:
    transport: str  # "sse" or "stdio"
    host: str = "127.0.0.1"
    port: int = 8081


@dataclass(frozen=True)
class Config:
    entra: EntraConfig
    kestra: KestraConfig
    server: ServerConfig


def load_config() -> Config:
    entra = EntraConfig(
        tenant_id=_require("ENTRA_TENANT_ID"),
        client_id=_require("ENTRA_CLIENT_ID"),
        client_secret=_require("ENTRA_CLIENT_SECRET"),
        redirect_uri=os.getenv("MCP_REDIRECT_URI", "http://127.0.0.1:8081/oauth/callback"),
    )

    kestra = KestraConfig(
        api_url=_require("KESTRA_API_URL").rstrip("/"),
        api_token=os.getenv("KESTRA_API_TOKEN", ""),
    )

    server = ServerConfig(
        transport=os.getenv("KESTRA_MCP_TRANSPORT", "sse").lower(),
        host=os.getenv("KESTRA_MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("KESTRA_MCP_PORT", "8081")),
    )

    if server.transport not in ("sse", "stdio"):
        raise ValueError(f"KESTRA_MCP_TRANSPORT must be 'sse' or 'stdio', got: {server.transport}")

    return Config(entra=entra, kestra=kestra, server=server)


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Required environment variable {key} is not set")
    return value
