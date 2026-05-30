"""Encrypted Kestra API token storage using Fernet."""

import json
import os
import threading
from pathlib import Path

from cryptography.fernet import Fernet


class TokenStore:
    """Encrypted store mapping Entra user IDs to Kestra API tokens.

    Tokens are encrypted with Fernet symmetric encryption and stored as a JSON file.
    Thread-safe via a reentrant lock.
    """

    def __init__(self, encryption_key: bytes, file_path: str | Path | None = None):
        self._fernet = Fernet(__import__("base64").urlsafe_b64encode(encryption_key))
        self._file_path = Path(file_path) if file_path else Path("/tmp/.kestra-tokens.json")
        self._lock = threading.RLock()

    @classmethod
    def from_config(cls, encryption_key: bytes) -> "TokenStore":
        """Create from global config encryption key."""
        path = Path(os.getenv("KESTRA_TOKEN_STORE", "/tmp/.kestra-tokens.json"))
        return cls(encryption_key, file_path=path)

    def _read(self) -> dict[str, str]:
        if not self._file_path.exists():
            return {}
        with self._lock:
            content = self._file_path.read_text().strip()
            return json.loads(content) if content else {}

    def _write(self, data: dict[str, str]) -> None:
        with self._lock:
            self._file_path.write_text(json.dumps(data, indent=2))

    def store_token(self, user_id: str, token: str) -> None:
        """Encrypt and store a Kestra token for a user."""
        encrypted = self._fernet.encrypt(token.encode()).decode()
        data = self._read()
        data[user_id] = encrypted
        self._write(data)

    def get_token(self, user_id: str) -> str | None:
        """Decrypt and return a user's Kestra token, or None if not found."""
        data = self._read()
        encrypted = data.get(user_id)
        if encrypted is None:
            return None
        try:
            return self._fernet.decrypt(encrypted.encode()).decode()
        except Exception:
            return None

    def remove_token(self, user_id: str) -> bool:
        """Remove a user's token. Returns True if it existed."""
        data = self._read()
        if user_id not in data:
            return False
        del data[user_id]
        self._write(data)
        return True

    def list_users(self) -> list[str]:
        """List user IDs that have stored tokens."""
        return list(self._read().keys())
