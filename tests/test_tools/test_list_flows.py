"""Tests for list_flows tool."""

import pytest

from src.client.kestra_client import KestraClient
from src.tools.list_flows import handle_list_flows


@pytest.fixture
def kestra_client():
    return KestraClient.from_url("http://localhost:8080/api/v1", api_token="test-token")


class TestListFlows:
    @pytest.mark.asyncio
    async def test_returns_flows(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows",
            json=[{"id": "flow1", "namespace": "company.team"}],
        )
        async with KestraClient.from_url(
            "http://localhost:8080/api/v1", api_token="test-token"
        ) as client:
            result = await handle_list_flows(kestra_client=client)
        assert result["flows"][0]["id"] == "flow1"

    @pytest.mark.asyncio
    async def test_returns_flows_with_namespace(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows?namespace=company.team",
            json=[{"id": "flow1", "namespace": "company.team"}],
        )
        async with KestraClient.from_url(
            "http://localhost:8080/api/v1", api_token="test-token"
        ) as client:
            result = await handle_list_flows(namespace="company.team", kestra_client=client)
        assert len(result["flows"]) == 1

    @pytest.mark.asyncio
    async def test_handles_upstream_error(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows",
            status_code=503,
        )
        async with KestraClient.from_url(
            "http://localhost:8080/api/v1", api_token="test-token"
        ) as client:
            result = await handle_list_flows(kestra_client=client)
        assert result["error"] is True
        assert result["code"] == "UPSTREAM_ERROR"
