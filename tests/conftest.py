"""Shared pytest fixtures for all tests."""

import base64
import os

import pytest
from cryptography.fernet import Fernet

from src.config import Config, KestraConfig, OidcConfig, ServerConfig


@pytest.fixture
def test_oidc_config():
    return OidcConfig(
        issuer_url="https://test-provider.example.com",
        client_id="test-client-id",
        client_secret="test-client-secret",
        authority="https://test-provider.example.com",
        jwks_uri="https://test-provider.example.com/discovery/keys",
        issuer="https://test-provider.example.com",
    )


@pytest.fixture
def test_kestra_config():
    return KestraConfig(
        api_url="http://localhost:8080/api/v1",
        tenant="",
        verify_ssl=True,
    )


@pytest.fixture
def test_server_config():
    return ServerConfig(transport="stdio")


@pytest.fixture
def test_encryption_key():
    return Fernet.generate_key()


@pytest.fixture
def test_config(test_oidc_config, test_kestra_config, test_server_config, test_encryption_key):
    return Config(
        oidc=test_oidc_config,
        kestra=test_kestra_config,
        server=test_server_config,
        encryption_key=base64.urlsafe_b64decode(test_encryption_key),
    )


@pytest.fixture(autouse=True)
def clean_env():
    """Ensure no real env vars leak into tests."""
    sensitive = [
        "OIDC_ISSUER_URL",
        "OIDC_CLIENT_ID",
        "OIDC_CLIENT_SECRET",
        "OIDC_AUTHORITY",
        "OIDC_JWKS_URI",
        "ENTRA_TENANT_ID",
        "ENTRA_CLIENT_ID",
        "ENTRA_CLIENT_SECRET",
        "KESTRA_API_URL",
        "KESTRA_API_TOKEN",
        "KESTRA_TENANT",
        "KESTRA_MCP_TRANSPORT",
        "ENCRYPTION_KEY",
    ]
    saved = {k: os.environ.pop(k, None) for k in sensitive}
    yield
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v
