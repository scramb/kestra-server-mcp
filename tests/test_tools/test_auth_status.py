"""Tests for auth_status tool."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from src.auth.session import current_user_id, set_session_token_store
from src.auth.token_store import TokenStore
from src.tools.auth_status import handle


@pytest.fixture
def token_store(tmp_path: Path):
    key = b"k" * 32
    return TokenStore(encryption_key=key, file_path=tmp_path / "tokens.json")


class TestAuthStatus:
    @pytest.mark.asyncio
    async def test_reports_unauthenticated_when_no_token(self, token_store):
        set_session_token_store(token_store)
        user = current_user_id.set("")
        try:
            with patch.dict(
                os.environ,
                {"KESTRA_API_URL": "http://kestra:8080/api/v1"},
                clear=True,
            ):
                result = await handle({})
            assert result["authenticated"] is False
            assert result["token_configured"] is False
            assert result["api_url"] == "http://kestra:8080/api/v1"
        finally:
            current_user_id.reset(user)

    @pytest.mark.asyncio
    async def test_reports_authenticated_when_token_set(self, token_store):
        token_store.store_token("user-1", "some-user-kestra-token")
        set_session_token_store(token_store)
        user = current_user_id.set("user-1")
        try:
            with patch.dict(
                os.environ,
                {"KESTRA_API_URL": "http://kestra:8080/api/v1"},
                clear=True,
            ):
                result = await handle({})
            assert result["authenticated"] is True
            assert result["token_configured"] is True
        finally:
            current_user_id.reset(user)

    @pytest.mark.asyncio
    async def test_all_tools_listed(self, token_store):
        set_session_token_store(token_store)
        user = current_user_id.set("")
        try:
            with patch.dict(
                os.environ,
                {"KESTRA_API_URL": "http://kestra:8080/api/v1"},
                clear=True,
            ):
                result = await handle({})
            expected = {
                "auth_status",
                "register_kestra_token",
                "search_namespaces",
                "list_flows",
                "get_flow",
                "create_or_update_flow",
                "execute_flow",
                "get_execution",
                "list_executions",
                "kill_execution",
                "search_triggers",
                "list_apps",
                "get_app",
                "create_app",
            }
            assert set(result["available_tools"]) == expected
        finally:
            current_user_id.reset(user)
