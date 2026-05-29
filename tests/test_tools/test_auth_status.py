"""Tests for auth_status tool."""

import os
from unittest.mock import patch

import pytest

from src.auth.session import current_kestra_token
from src.tools.auth_status import handle


class TestAuthStatus:
    @pytest.mark.asyncio
    async def test_reports_unauthenticated_when_no_token(self):
        token = current_kestra_token.set("")
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
            current_kestra_token.reset(token)

    @pytest.mark.asyncio
    async def test_reports_authenticated_when_token_set(self):
        token = current_kestra_token.set("some-user-kestra-token")
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
            current_kestra_token.reset(token)

    @pytest.mark.asyncio
    async def test_all_tools_listed(self):
        token = current_kestra_token.set("")
        try:
            with patch.dict(
                os.environ,
                {"KESTRA_API_URL": "http://kestra:8080/api/v1"},
                clear=True,
            ):
                result = await handle({})
            expected = {
                "auth_status",
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
            current_kestra_token.reset(token)
