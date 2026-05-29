"""In-memory stores for OAuth state: clients, auth sessions, auth codes, refresh tokens.

All stores are thread-safe and enforce expiry. Not persisted — server restart
means clients re-authenticate.
"""

import hashlib
import secrets
import time
from threading import Lock
from typing import Any

from mcp.shared.auth import OAuthClientInformationFull


class ClientStore:
    """Thread-safe in-memory store for dynamically registered OAuth clients."""

    def __init__(self):
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._lock = Lock()

    def get(self, client_id: str) -> OAuthClientInformationFull | None:
        with self._lock:
            client = self._clients.get(client_id)
            if client is None:
                return None
            if (
                client.client_secret_expires_at is not None
                and client.client_secret_expires_at < int(time.time())
            ):
                self._clients.pop(client_id, None)
                return None
            return client

    def put(self, client: OAuthClientInformationFull) -> None:
        with self._lock:
            self._clients[client.client_id] = client  # type: ignore[index]

    def remove(self, client_id: str) -> None:
        with self._lock:
            self._clients.pop(client_id, None)


class AuthSessionStore:
    """Pending authorization sessions between /authorize and Entra callback.

    Keyed by a random 'entra_state' token sent to Entra as the OAuth state param.
    Sessions expire after 5 minutes.
    """

    SESSION_TTL = 300

    def __init__(self):
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def create(
        self,
        client_id: str,
        original_state: str | None,
        redirect_uri: str,
        code_challenge: str,
        scopes: list[str] | None,
    ) -> str:
        state_token = secrets.token_hex(32)
        with self._lock:
            self._sessions[state_token] = {
                "client_id": client_id,
                "original_state": original_state,
                "redirect_uri": redirect_uri,
                "code_challenge": code_challenge,
                "scopes": scopes or [],
                "created_at": time.time(),
            }
        return state_token

    def consume(self, state_token: str) -> dict[str, Any] | None:
        with self._lock:
            session = self._sessions.pop(state_token, None)
        if session is None:
            return None
        if session["created_at"] + self.SESSION_TTL < time.time():
            return None
        return session


class AuthCodeStore:
    """Authorization codes issued by our server. One-time-use, 60 second TTL."""

    CODE_TTL = 60

    def __init__(self):
        self._codes: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def store(
        self,
        code: str,
        client_id: str,
        entra_user_id: str,
        code_challenge: str,
        redirect_uri: str,
        scopes: list[str] | None,
    ) -> None:
        with self._lock:
            self._codes[code] = {
                "client_id": client_id,
                "entra_user_id": entra_user_id,
                "code_challenge": code_challenge,
                "redirect_uri": redirect_uri,
                "scopes": scopes or [],
                "expires_at": time.time() + self.CODE_TTL,
            }

    def consume(self, code: str) -> dict[str, Any] | None:
        with self._lock:
            entry = self._codes.pop(code, None)
        if entry is None:
            return None
        if entry["expires_at"] < time.time():
            return None
        return entry


class RefreshTokenStore:
    """Refresh tokens. Keyed by SHA-256 hash of the raw token. 30 day TTL."""

    REFRESH_TTL = 86400 * 30

    def __init__(self):
        self._tokens: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def store(self, raw_token: str, client_id: str, entra_user_id: str, scopes: list[str]) -> None:
        hashed = hashlib.sha256(raw_token.encode()).hexdigest()
        now = int(time.time())
        with self._lock:
            self._tokens[hashed] = {
                "client_id": client_id,
                "entra_user_id": entra_user_id,
                "scopes": scopes,
                "created_at": now,
                "expires_at": now + self.REFRESH_TTL,
            }

    def load(self, raw_token: str) -> dict[str, Any] | None:
        hashed = hashlib.sha256(raw_token.encode()).hexdigest()
        with self._lock:
            entry = self._tokens.get(hashed)
        if entry is None:
            return None
        if entry["expires_at"] < int(time.time()):
            with self._lock:
                self._tokens.pop(hashed, None)
            return None
        return entry

    def rotate(self, old_raw: str, new_raw: str) -> None:
        old_hashed = hashlib.sha256(old_raw.encode()).hexdigest()
        new_hashed = hashlib.sha256(new_raw.encode()).hexdigest()
        with self._lock:
            entry = self._tokens.pop(old_hashed, None)
            if entry:
                self._tokens[new_hashed] = entry

    def revoke(self, raw_token: str) -> None:
        hashed = hashlib.sha256(raw_token.encode()).hexdigest()
        with self._lock:
            self._tokens.pop(hashed, None)
