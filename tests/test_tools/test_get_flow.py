"""Tests for get_flow tool."""

from unittest.mock import patch

import pytest

from src.client.kestra_client import KestraClient
from src.tools.get_flow import handle


class TestGetFlow:
    @pytest.mark.asyncio
    async def test_returns_flow(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows/company.team/myflow",
            json={"id": "myflow", "namespace": "company.team", "source": "id: myflow"},
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            with patch("src.tools.get_flow.get_kestra_client", return_value=client):
                result = await handle({"namespace": "company.team", "flow_id": "myflow"})
        assert result["id"] == "myflow"
        assert result["source"] == "id: myflow"

    @pytest.mark.asyncio
    async def test_returns_not_found(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows/company.team/nonexistent",
            status_code=404,
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            with patch("src.tools.get_flow.get_kestra_client", return_value=client):
                result = await handle({"namespace": "company.team", "flow_id": "nonexistent"})
        assert result["error"] is True
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_handles_upstream_error(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows/company.team/myflow",
            status_code=500,
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            with patch("src.tools.get_flow.get_kestra_client", return_value=client):
                result = await handle({"namespace": "company.team", "flow_id": "myflow"})
        assert result["error"] is True
        assert result["code"] == "UPSTREAM_ERROR"
