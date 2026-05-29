"""Tests for Kestra REST API client."""

import httpx
import pytest

from src.client.kestra_client import KestraClient, KestraError
from src.config import KestraConfig


@pytest.fixture
def kestra_config():
    return KestraConfig(
        api_url="http://localhost:8080/api/v1",
        api_token="test-token",
    )


class TestKestraClient:
    @pytest.mark.asyncio
    async def test_list_flows_no_filter(self, kestra_config, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows",
            json=[{"id": "flow1", "namespace": "company.team"}],
            match_headers={"Authorization": "Bearer test-token"},
        )
        async with KestraClient(kestra_config) as client:
            result = await client.list_flows()
        assert isinstance(result, list)
        assert result[0]["id"] == "flow1"

    @pytest.mark.asyncio
    async def test_list_flows_with_namespace(self, kestra_config, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows?namespace=company.team",
            json=[{"id": "flow1", "namespace": "company.team"}],
        )
        async with KestraClient(kestra_config) as client:
            result = await client.list_flows("company.team")
        assert result[0]["namespace"] == "company.team"

    @pytest.mark.asyncio
    async def test_get_flow_success(self, kestra_config, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows/company.team/myflow",
            json={"id": "myflow", "namespace": "company.team", "source": "id: myflow"},
        )
        async with KestraClient(kestra_config) as client:
            result = await client.get_flow("company.team", "myflow")
        assert result["id"] == "myflow"
        assert result["source"] == "id: myflow"

    @pytest.mark.asyncio
    async def test_get_flow_404(self, kestra_config, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows/company.team/nonexistent",
            status_code=404,
        )
        async with KestraClient(kestra_config) as client:
            with pytest.raises(KestraError) as exc:
                await client.get_flow("company.team", "nonexistent")
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_or_update_flow(self, kestra_config, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows",
            method="POST",
            json={"id": "newflow", "namespace": "company.team", "revision": 1},
        )
        async with KestraClient(kestra_config) as client:
            result = await client.create_or_update_flow("id: newflow\nnamespace: company.team")
        assert result["id"] == "newflow"

    @pytest.mark.asyncio
    async def test_execute_flow_success(self, kestra_config, httpx_mock):
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
        async with KestraClient(kestra_config) as client:
            result = await client.execute_flow("company.team", "myflow")
        assert result["id"] == "exec-001"
        assert result["state"]["current"] == "CREATED"

    @pytest.mark.asyncio
    async def test_execute_flow_with_inputs(self, kestra_config, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/executions/company.team/myflow",
            method="POST",
            json={"id": "exec-002", "state": {"current": "CREATED"}},
        )
        async with KestraClient(kestra_config) as client:
            result = await client.execute_flow(
                "company.team", "myflow", inputs={"param1": "value1"}
            )
        assert result["id"] == "exec-002"

    @pytest.mark.asyncio
    async def test_execute_flow_404(self, kestra_config, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/executions/company.team/nonexistent",
            method="POST",
            status_code=404,
        )
        async with KestraClient(kestra_config) as client:
            with pytest.raises(KestraError) as exc:
                await client.execute_flow("company.team", "nonexistent")
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_execution_success(self, kestra_config, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/executions/exec-001",
            json={
                "id": "exec-001",
                "namespace": "company.team",
                "flow_id": "myflow",
                "state": {"current": "SUCCESS", "histories": []},
                "task_run_list": [],
                "url": "http://localhost:8080/ui/executions/company.team/myflow/exec-001",
            },
        )
        async with KestraClient(kestra_config) as client:
            result = await client.get_execution("exec-001")
        assert result["id"] == "exec-001"
        assert result["state"]["current"] == "SUCCESS"

    @pytest.mark.asyncio
    async def test_get_execution_404(self, kestra_config, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/executions/nonexistent",
            status_code=404,
        )
        async with KestraClient(kestra_config) as client:
            with pytest.raises(KestraError) as exc:
                await client.get_execution("nonexistent")
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_server_error_mapping(self, kestra_config, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows",
            status_code=503,
        )
        async with KestraClient(kestra_config) as client:
            with pytest.raises(KestraError) as exc:
                await client.list_flows()
        assert exc.value.status_code == 503

    @pytest.mark.asyncio
    async def test_connection_error_mapping(self, kestra_config, httpx_mock):
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="http://localhost:8080/api/v1/flows",
        )
        async with KestraClient(kestra_config) as client:
            with pytest.raises(KestraError) as exc:
                await client.list_flows()
        assert exc.value.status_code == 503
