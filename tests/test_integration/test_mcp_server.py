"""Integration tests for MCP server end-to-end flows."""

from unittest.mock import patch

import pytest

from src.client.kestra_client import KestraClient
from src.tools.create_or_update import handle as create_or_update_handle
from src.tools.execute_flow import handle as execute_flow_handle
from src.tools.get_execution import handle as get_execution_handle
from src.tools.get_flow import handle as get_flow_handle
from src.tools.list_flows import handle as list_flows_handle


class TestFullMVPJourney:
    """End-to-end MVP journey: auth -> list -> get -> create -> execute -> get_execution."""

    @pytest.mark.asyncio
    async def test_full_mvp_journey(self, httpx_mock):
        # 3. List flows
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows/company.team",
            json=[{"id": "flow1", "namespace": "company.team"}],
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            with patch("src.tools.list_flows.get_kestra_client", return_value=client):
                flows = await list_flows_handle({"namespace": "company.team"})
        assert len(flows["flows"]) == 1

        # 4. Get flow
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows/company.team/flow1",
            json={"id": "flow1", "namespace": "company.team", "source": "id: flow1"},
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            with patch("src.tools.get_flow.get_kestra_client", return_value=client):
                flow = await get_flow_handle({"namespace": "company.team", "flow_id": "flow1"})
        assert flow["id"] == "flow1"

        # 5. Create/update flow
        new_yaml = "id: newflow\nnamespace: company.team"
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows",
            method="POST",
            json={"id": "newflow", "namespace": "company.team", "revision": 1},
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            with patch("src.tools.create_or_update.get_kestra_client", return_value=client):
                result = await create_or_update_handle({"source": new_yaml})
        assert result["id"] == "newflow"

        # 6. Execute flow
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/executions/company.team/newflow",
            method="POST",
            json={
                "id": "exec-001",
                "namespace": "company.team",
                "flow_id": "newflow",
                "state": {"current": "CREATED", "histories": []},
            },
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            with patch("src.tools.execute_flow.get_kestra_client", return_value=client):
                exec_result = await execute_flow_handle({"namespace": "company.team", "flow_id": "newflow"})
        assert exec_result["id"] == "exec-001"

        # 7. Get execution
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/executions/exec-001",
            json={
                "id": "exec-001",
                "namespace": "company.team",
                "flow_id": "newflow",
                "state": {"current": "SUCCESS", "histories": [], "duration": 2.0},
            },
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            with patch("src.tools.get_execution.get_kestra_client", return_value=client):
                exec_detail = await get_execution_handle({"execution_id": "exec-001"})
        assert exec_detail["state"]["current"] == "SUCCESS"


class TestUpstreamErrorHandling:
    @pytest.mark.asyncio
    async def test_kestra_unavailable_returns_sanitized_error(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows/company.team",
            status_code=503,
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            with patch("src.tools.list_flows.get_kestra_client", return_value=client):
                result = await list_flows_handle({"namespace": "company.team"})
        assert result["error"] is True
        assert result["code"] == "UPSTREAM_ERROR"
        assert result["status_code"] == 503
        assert "Traceback" not in str(result)
