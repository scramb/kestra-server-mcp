"""Tests for get_execution tool."""

from unittest.mock import patch

import pytest

from src.client.kestra_client import KestraClient
from src.tools.get_execution import handle


class TestGetExecution:
    @pytest.mark.asyncio
    async def test_returns_execution(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/executions/exec-001",
            json={
                "id": "exec-001",
                "namespace": "company.team",
                "flow_id": "myflow",
                "state": {"current": "SUCCESS", "histories": [], "duration": 2.5},
                "task_run_list": [],
                "url": "http://localhost:8080/ui/executions/company.team/myflow/exec-001",
            },
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            with patch("src.tools.get_execution.get_kestra_client", return_value=client):
                result = await handle({"execution_id": "exec-001"})
        assert result["id"] == "exec-001"
        assert result["state"]["current"] == "SUCCESS"

    @pytest.mark.asyncio
    async def test_returns_not_found(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/executions/nonexistent",
            status_code=404,
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            with patch("src.tools.get_execution.get_kestra_client", return_value=client):
                result = await handle({"execution_id": "nonexistent"})
        assert result["error"] is True
        assert result["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_handles_upstream_error(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/executions/exec-001",
            status_code=500,
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            with patch("src.tools.get_execution.get_kestra_client", return_value=client):
                result = await handle({"execution_id": "exec-001"})
        assert result["error"] is True
        assert result["code"] == "UPSTREAM_ERROR"
