"""Integration tests for MCP server end-to-end flows."""

import pytest

from src.auth.permissions import (
    get_required_role_for_tool,
    has_role,
    map_claims_to_tools,
)
from src.client.kestra_client import KestraClient
from src.tools.auth_status import get_auth_status
from src.tools.create_or_update import handle_create_or_update_flow
from src.tools.execute_flow import handle_execute_flow
from src.tools.get_execution import handle_get_execution
from src.tools.get_flow import handle_get_flow
from src.tools.list_flows import handle_list_flows


class TestFullMVPJourney:
    """End-to-end MVP journey: auth → list → get → create → execute → get_execution."""

    @pytest.mark.asyncio
    async def test_full_mvp_journey_with_all_roles(
        self, session_manager, full_claims, test_entra_config, httpx_mock
    ):
        # 1. Create authenticated session
        token_result = {"access_token": "fake-access", "refresh_token": "fake-refresh"}
        identity = session_manager.create_session(
            full_claims, token_result, test_entra_config
        )

        # 2. Check auth status
        status = get_auth_status(identity=identity, session_manager=session_manager)
        assert status["authenticated"] is True
        assert "list_flows" in status["available_tools"]
        assert "execute_flow" in status["available_tools"]

        # 3. List flows
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows",
            json=[{"id": "flow1", "namespace": "company.team"}],
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            flows = await handle_list_flows(kestra_client=client)
        assert len(flows["flows"]) == 1

        # 4. Get flow
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows/company.team/flow1",
            json={"id": "flow1", "namespace": "company.team", "source": "id: flow1"},
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            flow = await handle_get_flow("company.team", "flow1", kestra_client=client)
        assert flow["id"] == "flow1"

        # 5. Create/update flow
        new_yaml = "id: newflow\nnamespace: company.team"
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows",
            method="POST",
            json={"id": "newflow", "namespace": "company.team", "revision": 1},
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            result = await handle_create_or_update_flow(source=new_yaml, kestra_client=client)
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
            exec_result = await handle_execute_flow(
                "company.team", "newflow", kestra_client=client
            )
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
            exec_detail = await handle_get_execution("exec-001", kestra_client=client)
        assert exec_detail["state"]["current"] == "SUCCESS"


class TestUpstreamErrorHandling:
    @pytest.mark.asyncio
    async def test_kestra_unavailable_returns_sanitized_error(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows",
            status_code=503,
        )
        async with KestraClient.from_url("http://localhost:8080/api/v1", "test-token") as client:
            result = await handle_list_flows(kestra_client=client)
        assert result["error"] is True
        assert result["code"] == "UPSTREAM_ERROR"
        assert result["status_code"] == 503
        # No stack traces or internal details
        assert "Traceback" not in str(result)


class TestPermissionDenyByDefault:
    """Verify deny-by-default behavior for all permission-gated tools."""

    def test_auth_status_always_allowed(self):
        assert get_required_role_for_tool("auth_status") is None

    def test_read_tools_require_flow_read(self):
        assert get_required_role_for_tool("list_flows") == "kestra.flow.read"
        assert get_required_role_for_tool("get_flow") == "kestra.flow.read"
        assert get_required_role_for_tool("get_execution") == "kestra.flow.read"

    def test_write_tools_require_flow_write(self):
        assert get_required_role_for_tool("create_or_update_flow") == "kestra.flow.write"

    def test_execute_tools_require_flow_execute(self):
        assert get_required_role_for_tool("execute_flow") == "kestra.flow.execute"

    def test_no_roles_denies_all_operational_tools(self):
        no_roles = {"sub": "user", "roles": []}
        tools = map_claims_to_tools(no_roles)
        assert tools == ["auth_status"]
        assert "list_flows" not in tools

    def test_permission_change_reflected_immediately(self, session_manager, test_entra_config):
        # Create session with read role only
        read_claims = {"sub": "user", "roles": ["kestra.flow.read"]}
        token = {"access_token": "tok", "refresh_token": "ref"}
        identity = session_manager.create_session(read_claims, token, test_entra_config)

        # Verify read access
        session1 = session_manager.get_session(identity)
        assert has_role(session1["claims"], "kestra.flow.read")
        assert not has_role(session1["claims"], "kestra.flow.write")

        # Simulate permission change by updating claims
        session1["claims"]["roles"] = ["kestra.flow.write"]
        assert not has_role(session1["claims"], "kestra.flow.read")
        assert has_role(session1["claims"], "kestra.flow.write")
