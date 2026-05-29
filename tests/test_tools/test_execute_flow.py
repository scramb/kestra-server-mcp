"""Tests for execute_flow tool."""

from unittest.mock import patch

import pytest

from src.client.kestra_client import KestraClient
from src.tools.execute_flow import handle


class TestExecuteFlow:
    @pytest.mark.asyncio
    async def test_executes_flow(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/executions/company.team/myflow",
            method="POST",
            json={
                "id": "exec-001",
                "namespace": "company.team",
                "flow_id": "myflow",
                "state": {"current": "CREATED", "histories": []},
                "url": "http://localhost:8080/ui/executions/company.team/myflow/exec-001",
            },
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            with patch("src.tools.execute_flow.get_kestra_client", return_value=client):
                result = await handle({"namespace": "company.team", "flow_id": "myflow"})
        assert result["id"] == "exec-001"
        assert result["state"]["current"] == "CREATED"

    @pytest.mark.asyncio
    async def test_executes_flow_with_inputs(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/executions/company.team/myflow",
            method="POST",
            json={"id": "exec-002", "state": {"current": "CREATED"}},
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            with patch("src.tools.execute_flow.get_kestra_client", return_value=client):
                result = await handle({
                    "namespace": "company.team",
                    "flow_id": "myflow",
                    "inputs": {"greeting": "hello"},
                })
        assert result["id"] == "exec-002"

    @pytest.mark.asyncio
    async def test_returns_not_found(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/executions/company.team/nonexistent",
            method="POST",
            status_code=404,
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            with patch("src.tools.execute_flow.get_kestra_client", return_value=client):
                result = await handle({"namespace": "company.team", "flow_id": "nonexistent"})
        assert result["error"] is True
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_handles_upstream_error(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/executions/company.team/myflow",
            method="POST",
            status_code=500,
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            with patch("src.tools.execute_flow.get_kestra_client", return_value=client):
                result = await handle({"namespace": "company.team", "flow_id": "myflow"})
        assert result["error"] is True
        assert result["code"] == "UPSTREAM_ERROR"
