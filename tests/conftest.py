"""Shared pytest fixtures for all tests."""

import os
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from src.auth.oauth import SessionManager
from src.config import Config, EntraConfig, KestraConfig, ServerConfig

# === JWKS Test Helpers ===

@pytest.fixture
def rsa_key_pair():
    """Generate a test RSA key pair."""
    key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return {"private_pem": private_pem, "public_pem": public_pem, "key": key}


@pytest.fixture
def jwks_response(rsa_key_pair):
    """Build a minimal JWKS response for the test key."""

    public_key = rsa_key_pair["key"].public_key()
    public_numbers = public_key.public_numbers()

    import base64

    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    # Encode modulus (n) and exponent (e) as base64url
    n_bytes_len = (public_numbers.n.bit_length() + 7) // 8
    n_bytes = public_numbers.n.to_bytes(n_bytes_len, "big")
    e_bytes = public_numbers.e.to_bytes(
        (public_numbers.e.bit_length() + 7) // 8, "big"
    )

    jwk = {
        "kty": "RSA",
        "kid": "test-key-001",
        "alg": "RS256",
        "use": "sig",
        "n": _b64url(n_bytes),
        "e": _b64url(e_bytes),
    }
    return {"keys": [jwk]}


# === Test Config ===

@pytest.fixture
def test_entra_config():
    return EntraConfig(
        tenant_id="test-tenant-id",
        client_id="test-client-id",
        client_secret="test-client-secret",
    )


@pytest.fixture
def test_kestra_config():
    return KestraConfig(
        api_url="http://localhost:8080/api/v1",
        api_token="test-api-token",
    )


@pytest.fixture
def test_server_config():
    return ServerConfig(transport="stdio")


@pytest.fixture
def test_config(test_entra_config, test_kestra_config, test_server_config):
    return Config(
        entra=test_entra_config,
        kestra=test_kestra_config,
        server=test_server_config,
    )


# === Token Helpers ===

def _build_token(
    rsa_key_pair: dict,
    entra_config: EntraConfig,
    subject: str = "test-user-001",
    roles: list[str] | None = None,
    expired: bool = False,
    issuer_override: str | None = None,
    audience_override: str | None = None,
) -> str:
    now = datetime.now(UTC)
    exp = now - timedelta(hours=1) if expired else now + timedelta(hours=1)

    claims = {
        "sub": subject,
        "name": "Test User",
        "tid": entra_config.tenant_id,
        "iss": issuer_override or entra_config.issuer,
        "aud": audience_override or entra_config.client_id,
        "iat": now,
        "nbf": now - timedelta(minutes=5),
        "exp": exp,
    }
    if roles is not None:
        claims["roles"] = roles

    return jwt.encode(
        claims,
        rsa_key_pair["private_pem"],
        algorithm="RS256",
        headers={"kid": "test-key-001"},
    )


@pytest.fixture
def valid_token(rsa_key_pair, test_entra_config):
    """A valid JWT with all roles."""
    return _build_token(
        rsa_key_pair,
        test_entra_config,
        roles=["kestra.flow.read", "kestra.flow.write", "kestra.flow.execute"],
    )


@pytest.fixture
def valid_token_read_only(rsa_key_pair, test_entra_config):
    """A valid JWT with only flow.read role."""
    return _build_token(rsa_key_pair, test_entra_config, roles=["kestra.flow.read"])


@pytest.fixture
def valid_token_no_roles(rsa_key_pair, test_entra_config):
    """A valid JWT with no roles — only auth_status available."""
    return _build_token(rsa_key_pair, test_entra_config, roles=[])


@pytest.fixture
def expired_token(rsa_key_pair, test_entra_config):
    """An expired JWT."""
    return _build_token(
        rsa_key_pair, test_entra_config, roles=["kestra.flow.read"], expired=True
    )


@pytest.fixture
def wrong_issuer_token(rsa_key_pair, test_entra_config):
    """A JWT with wrong issuer."""
    return _build_token(
        rsa_key_pair,
        test_entra_config,
        roles=["kestra.flow.read"],
        issuer_override="https://wrong-issuer.example.com",
    )


@pytest.fixture
def wrong_audience_token(rsa_key_pair, test_entra_config):
    """A JWT with wrong audience."""
    return _build_token(
        rsa_key_pair,
        test_entra_config,
        roles=["kestra.flow.read"],
        audience_override="wrong-audience",
    )


# === Token Claims ===

@pytest.fixture
def full_claims():
    """Claims dict with all roles."""
    return {
        "sub": "test-user-001",
        "name": "Test User",
        "tid": "test-tenant-id",
        "roles": ["kestra.flow.read", "kestra.flow.write", "kestra.flow.execute"],
    }


@pytest.fixture
def read_only_claims():
    """Claims dict with only flow.read."""
    return {
        "sub": "test-user-002",
        "name": "Reader",
        "tid": "test-tenant-id",
        "roles": ["kestra.flow.read"],
    }


@pytest.fixture
def no_role_claims():
    """Claims dict with no roles."""
    return {
        "sub": "test-user-003",
        "name": "No Roles",
        "tid": "test-tenant-id",
    }


# === Session Manager ===

@pytest.fixture
def session_manager():
    return SessionManager()


# === JWKS Cache Cleanup ===

@pytest.fixture(autouse=True)
def clear_jwks_cache():
    """Clear JWKS cache before each test to avoid cross-test pollution."""
    from src.auth.jwt_validator import _JWKS_CACHE

    _JWKS_CACHE.clear()
    yield
    _JWKS_CACHE.clear()


# === Environment Mocking ===

@pytest.fixture(autouse=True)
def clean_env():
    """Ensure no real env vars leak into tests."""
    sensitive = [
        "ENTRA_TENANT_ID",
        "ENTRA_CLIENT_ID",
        "ENTRA_CLIENT_SECRET",
        "KESTRA_API_URL",
        "KESTRA_API_TOKEN",
        "KESTRA_MCP_TRANSPORT",
    ]
    saved = {k: os.environ.pop(k, None) for k in sensitive}
    yield
    for k, v in saved.items():
        if v is not None:
            os.environ[k] = v
