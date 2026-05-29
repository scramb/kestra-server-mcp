"""Tests for in-memory OAuth stores."""

import time

import pytest
from pydantic import AnyHttpUrl

from mcp.shared.auth import OAuthClientInformationFull

from src.auth.stores import (
    AuthCodeStore,
    AuthSessionStore,
    ClientStore,
    RefreshTokenStore,
)


@pytest.fixture
def sample_client():
    return OAuthClientInformationFull(
        client_id="test-client-id",
        redirect_uris=[AnyHttpUrl("http://localhost:8888/callback")],
        token_endpoint_auth_method="client_secret_post",
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
    )


class TestClientStore:
    def test_put_and_get(self, sample_client):
        store = ClientStore()
        store.put(sample_client)
        assert store.get(sample_client.client_id) == sample_client

    def test_get_unknown_returns_none(self):
        store = ClientStore()
        assert store.get("nonexistent") is None

    def test_remove(self, sample_client):
        store = ClientStore()
        store.put(sample_client)
        store.remove(sample_client.client_id)
        assert store.get(sample_client.client_id) is None

    def test_remove_nonexistent_does_not_raise(self):
        store = ClientStore()
        store.remove("nonexistent")


class TestAuthSessionStore:
    def test_create_and_consume(self):
        store = AuthSessionStore()
        state = store.create(
            client_id="c1",
            original_state="orig",
            redirect_uri="http://localhost/cb",
            code_challenge="challenge",
            scopes=["s1"],
        )
        session = store.consume(state)
        assert session is not None
        assert session["client_id"] == "c1"
        assert session["original_state"] == "orig"
        assert session["redirect_uri"] == "http://localhost/cb"

    def test_consume_is_one_time(self):
        store = AuthSessionStore()
        state = store.create("c1", None, "http://localhost/cb", "ch", None)
        assert store.consume(state) is not None
        assert store.consume(state) is None

    def test_consume_expired_returns_none(self):
        store = AuthSessionStore()
        store.SESSION_TTL = 0  # Immediately expired
        state = store.create("c1", None, "http://localhost/cb", "ch", None)
        time.sleep(0.01)
        assert store.consume(state) is None

    def test_state_token_unique(self):
        store = AuthSessionStore()
        s1 = store.create("c1", None, "http://localhost/cb", "ch", None)
        s2 = store.create("c2", None, "http://localhost/cb", "ch", None)
        assert s1 != s2


class TestAuthCodeStore:
    def test_store_and_consume(self):
        store = AuthCodeStore()
        store.store("code1", "c1", "user1", "challenge", "http://redirect", ["s1"])
        entry = store.consume("code1")
        assert entry is not None
        assert entry["client_id"] == "c1"
        assert entry["entra_user_id"] == "user1"

    def test_consume_is_one_time(self):
        store = AuthCodeStore()
        store.store("code1", "c1", "user1", "ch", "http://r", [])
        assert store.consume("code1") is not None
        assert store.consume("code1") is None

    def test_consume_expired_returns_none(self):
        store = AuthCodeStore()
        store.CODE_TTL = 0
        store.store("code1", "c1", "user1", "ch", "http://r", [])
        time.sleep(0.01)
        assert store.consume("code1") is None


class TestRefreshTokenStore:
    def test_store_and_load(self):
        store = RefreshTokenStore()
        store.store("raw-token", "c1", "user1", ["s1"])
        entry = store.load("raw-token")
        assert entry is not None
        assert entry["client_id"] == "c1"
        assert entry["entra_user_id"] == "user1"
        assert entry["scopes"] == ["s1"]

    def test_load_unknown_returns_none(self):
        store = RefreshTokenStore()
        assert store.load("nonexistent") is None

    def test_rotate(self):
        store = RefreshTokenStore()
        store.store("old-token", "c1", "user1", [])
        store.rotate("old-token", "new-token")
        assert store.load("old-token") is None
        assert store.load("new-token") is not None

    def test_revoke(self):
        store = RefreshTokenStore()
        store.store("token", "c1", "user1", [])
        store.revoke("token")
        assert store.load("token") is None
