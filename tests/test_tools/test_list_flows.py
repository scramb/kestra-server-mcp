"""Tests for list_flows tool."""

from unittest.mock import patch

import pytest

from src.client.kestra_client import KestraClient
from src.tools.list_flows import handle


class TestListFlows:
    @pytest.mark.asyncio
    async def test_returns_flows(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows/company.team",
            json=[{"id": "flow1", "namespace": "company.team"}],
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            with patch("src.tools.list_flows.get_kestra_client", return_value=client):
                result = await handle({"namespace": "company.team"})
        assert result["flows"][0]["id"] == "flow1"

    @pytest.mark.asyncio
    async def test_handles_upstream_error(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows/company.team",
            status_code=503,
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            with patch("src.tools.list_flows.get_kestra_client", return_value=client):
                result = await handle({"namespace": "company.team"})
        assert result["error"] is True
        assert result["code"] == "UPSTREAM_ERROR"
