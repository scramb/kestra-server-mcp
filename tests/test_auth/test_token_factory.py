"""Tests for self-signed JWT token factory."""

import time

import pytest

from src.auth.token_factory import (
    create_access_token,
    create_refresh_token,
    validate_access_token,
)


@pytest.fixture
def signing_key():
    return b"a" * 32


class TestCreateAccessToken:
    def test_creates_valid_token(self, signing_key):
        token = create_access_token(
            entra_user_id="user-123",
            client_id="client-abc",
            scopes=["kestra.read"],
            signing_key=signing_key,
        )
        assert token.count(".") == 2
        payload = validate_access_token(token, signing_key)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["client_id"] == "client-abc"
        assert payload["scopes"] == ["kestra.read"]
        assert "jti" in payload

    def test_token_expiry(self, signing_key):
        token = create_access_token(
            entra_user_id="user-123",
            client_id="c",
            scopes=[],
            signing_key=signing_key,
            ttl_seconds=0,
        )
        time.sleep(0.01)
        assert validate_access_token(token, signing_key) is None

    def test_future_token_is_valid(self, signing_key):
        token = create_access_token(
            entra_user_id="user-123",
            client_id="c",
            scopes=[],
            signing_key=signing_key,
            ttl_seconds=3600,
        )
        assert validate_access_token(token, signing_key) is not None


class TestValidateAccessToken:
    def test_wrong_key_returns_none(self, signing_key):
        token = create_access_token(
            entra_user_id="user-123",
            client_id="c",
            scopes=[],
            signing_key=signing_key,
        )
        wrong_key = b"b" * 32
        assert validate_access_token(token, wrong_key) is None

    def test_tampered_payload_returns_none(self, signing_key):
        token = create_access_token(
            entra_user_id="user-123",
            client_id="c",
            scopes=[],
            signing_key=signing_key,
        )
        parts = token.split(".")
        # Modify the payload (middle part) by replacing a character
        tampered = parts[0] + ".Zm9v." + parts[2]
        assert validate_access_token(tampered, signing_key) is None

    def test_malformed_token_returns_none(self, signing_key):
        assert validate_access_token("not.a.jwt.token", signing_key) is None
        assert validate_access_token("no-dots", signing_key) is None

    def test_garbage_signature_returns_none(self, signing_key):
        token = create_access_token(
            entra_user_id="user-123",
            client_id="c",
            scopes=[],
            signing_key=signing_key,
        )
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + ".garbage"
        assert validate_access_token(tampered, signing_key) is None

    def test_unique_jti_per_token(self, signing_key):
        t1 = create_access_token(
            entra_user_id="u1", client_id="c1", scopes=[], signing_key=signing_key
        )
        t2 = create_access_token(
            entra_user_id="u1", client_id="c1", scopes=[], signing_key=signing_key
        )
        p1 = validate_access_token(t1, signing_key)
        p2 = validate_access_token(t2, signing_key)
        assert p1["jti"] != p2["jti"]


class TestCreateRefreshToken:
    def test_returns_raw_and_hash(self):
        raw, hashed = create_refresh_token()
        assert len(raw) == 64
        assert len(hashed) == 64
        assert raw != hashed

    def test_tokens_are_unique(self):
        r1, _ = create_refresh_token()
        r2, _ = create_refresh_token()
        assert r1 != r2
