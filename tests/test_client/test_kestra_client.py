"""Tests for Kestra REST API client."""

import httpx
import pytest

from src.client.kestra_client import KestraClient, KestraError
from src.config import KestraConfig


@pytest.fixture
def kestra_config():
    return KestraConfig(
        api_url="http://localhost:8080/api/v1",
        tenant="",
        verify_ssl=True,
    )


@pytest.fixture
async def client(kestra_config):
    """KestraClient with a test token override."""
    return KestraClient(kestra_config, api_token="test-token")


class TestKestraClient:
    @pytest.mark.asyncio
    async def test_search_namespaces(self, kestra_config, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/namespaces/search",
            json={"results": [{"id": "company.team"}], "total": 1},
            match_headers={"Authorization": "Bearer test-token"},
        )
        async with KestraClient(kestra_config, api_token="test-token") as c:
            result = await c.search_namespaces()
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_list_flows(self, kestra_config, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows/company.team",
            json=[{"id": "flow1", "namespace": "company.team"}],
            match_headers={"Authorization": "Bearer test-token"},
        )
        async with KestraClient(kestra_config, api_token="test-token") as c:
            result = await c.list_flows("company.team")
        assert isinstance(result, list)
        assert result[0]["id"] == "flow1"

    @pytest.mark.asyncio
    async def test_get_flow_success(self, kestra_config, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows/company.team/myflow",
            json={"id": "myflow", "namespace": "company.team", "source": "id: myflow"},
        )
        async with KestraClient(kestra_config, api_token="test-token") as c:
            result = await c.get_flow("company.team", "myflow")
        assert result["id"] == "myflow"

    @pytest.mark.asyncio
    async def test_get_flow_404(self, kestra_config, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows/company.team/nonexistent",
            status_code=404,
        )
        async with KestraClient(kestra_config, api_token="test-token") as c:
            with pytest.raises(KestraError) as exc:
                await c.get_flow("company.team", "nonexistent")
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_or_update_flow(self, kestra_config, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows",
            method="POST",
            json={"id": "newflow", "namespace": "company.team", "revision": 1},
        )
        async with KestraClient(kestra_config, api_token="test-token") as c:
            result = await c.create_or_update_flow("id: newflow\nnamespace: company.team")
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
            },
        )
        async with KestraClient(kestra_config, api_token="test-token") as c:
            result = await c.execute_flow("company.team", "myflow")
        assert result["id"] == "exec-001"

    @pytest.mark.asyncio
    async def test_execute_flow_with_inputs(self, kestra_config, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/executions/company.team/myflow",
            method="POST",
            json={"id": "exec-002", "state": {"current": "CREATED"}},
        )
        async with KestraClient(kestra_config, api_token="test-token") as c:
            result = await c.execute_flow(
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
        async with KestraClient(kestra_config, api_token="test-token") as c:
            with pytest.raises(KestraError) as exc:
                await c.execute_flow("company.team", "nonexistent")
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
            },
        )
        async with KestraClient(kestra_config, api_token="test-token") as c:
            result = await c.get_execution("exec-001")
        assert result["id"] == "exec-001"

    @pytest.mark.asyncio
    async def test_get_execution_404(self, kestra_config, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/executions/nonexistent",
            status_code=404,
        )
        async with KestraClient(kestra_config, api_token="test-token") as c:
            with pytest.raises(KestraError) as exc:
                await c.get_execution("nonexistent")
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_server_error_mapping(self, kestra_config, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows/company.team",
            status_code=503,
        )
        async with KestraClient(kestra_config, api_token="test-token") as c:
            with pytest.raises(KestraError) as exc:
                await c.list_flows("company.team")
        assert exc.value.status_code == 503

    @pytest.mark.asyncio
    async def test_connection_error_mapping(self, kestra_config, httpx_mock):
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="http://localhost:8080/api/v1/flows/company.team",
        )
        async with KestraClient(kestra_config, api_token="test-token") as c:
            with pytest.raises(KestraError) as exc:
                await c.list_flows("company.team")
        assert exc.value.status_code == 503
