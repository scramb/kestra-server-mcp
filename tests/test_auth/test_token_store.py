"""Tests for TokenStore."""

import tempfile
from pathlib import Path

from cryptography.fernet import Fernet

from src.auth.token_store import TokenStore


class TestTokenStore:
    def test_store_and_get_token(self):
        key = Fernet.generate_key()
        import base64
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)

        try:
            store = TokenStore(
                encryption_key=base64.urlsafe_b64decode(key),
                file_path=path,
            )
            store.store_token("user-001", "test-kestra-token")
            assert store.get_token("user-001") == "test-kestra-token"

            store.store_token("user-001", "new-token")
            assert store.get_token("user-001") == "new-token"

        finally:
            path.unlink(missing_ok=True)

    def test_get_nonexistent_returns_none(self):
        key = Fernet.generate_key()
        import base64
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)

        try:
            store = TokenStore(
                encryption_key=base64.urlsafe_b64decode(key),
                file_path=path,
            )
            assert store.get_token("no-such-user") is None
        finally:
            path.unlink(missing_ok=True)

    def test_remove_token(self):
        key = Fernet.generate_key()
        import base64
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)

        try:
            store = TokenStore(
                encryption_key=base64.urlsafe_b64decode(key),
                file_path=path,
            )
            store.store_token("user-001", "test-token")
            assert store.remove_token("user-001") is True
            assert store.get_token("user-001") is None
            assert store.remove_token("user-001") is False
        finally:
            path.unlink(missing_ok=True)

    def test_list_users(self):
        key = Fernet.generate_key()
        import base64
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)

        try:
            store = TokenStore(
                encryption_key=base64.urlsafe_b64decode(key),
                file_path=path,
            )
            store.store_token("user-a", "token-a")
            store.store_token("user-b", "token-b")
            users = store.list_users()
            assert set(users) == {"user-a", "user-b"}
        finally:
            path.unlink(missing_ok=True)

    def test_different_keys_produce_different_ciphertext(self):
        import base64

        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f1, \
             tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f2:
            path1 = Path(f1.name)
            path2 = Path(f2.name)

        try:
            store1 = TokenStore(
                encryption_key=base64.urlsafe_b64decode(key1),
                file_path=path1,
            )
            store2 = TokenStore(
                encryption_key=base64.urlsafe_b64decode(key2),
                file_path=path2,
            )
            store1.store_token("user", "token")
            store2.store_token("user", "token")

            # Both store the same token but encrypted with different keys
            raw1 = path1.read_text()
            raw2 = path2.read_text()
            assert raw1 != raw2
        finally:
            path1.unlink(missing_ok=True)
            path2.unlink(missing_ok=True)
