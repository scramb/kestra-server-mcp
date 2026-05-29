"""Tests for permissions mapping."""


from src.auth.permissions import (
    get_identity,
    get_required_role_for_tool,
    has_role,
    map_claims_to_permissions,
    map_claims_to_tools,
)


class TestMapClaimsToTools:
    def test_no_roles_returns_only_auth_status(self):
        result = map_claims_to_tools({})
        assert result == ["auth_status"]

    def test_empty_roles_list(self):
        result = map_claims_to_tools({"roles": []})
        assert result == ["auth_status"]

    def test_flow_read_role(self):
        result = map_claims_to_tools({"roles": ["kestra.flow.read"]})
        assert sorted(result) == ["auth_status", "get_execution", "get_flow", "list_flows"]

    def test_flow_write_role(self):
        result = map_claims_to_tools({"roles": ["kestra.flow.write"]})
        assert sorted(result) == ["auth_status", "create_or_update_flow"]

    def test_flow_execute_role(self):
        result = map_claims_to_tools({"roles": ["kestra.flow.execute"]})
        assert sorted(result) == ["auth_status", "execute_flow"]

    def test_all_three_roles(self):
        result = map_claims_to_tools({
            "roles": ["kestra.flow.read", "kestra.flow.write", "kestra.flow.execute"]
        })
        assert "create_or_update_flow" in result
        assert "execute_flow" in result
        assert "list_flows" in result
        assert "get_flow" in result
        assert "get_execution" in result

    def test_unknown_role_is_ignored(self):
        result = map_claims_to_tools({"roles": ["unknown.role"]})
        assert result == ["auth_status"]

    def test_mixed_known_and_unknown_roles(self):
        result = map_claims_to_tools({"roles": ["kestra.flow.read", "unknown.role"]})
        assert "list_flows" in result
        assert "create_or_update_flow" not in result

    def test_roles_not_a_list(self):
        result = map_claims_to_tools({"roles": "kestra.flow.read"})
        assert result == ["auth_status"]


class TestMapClaimsToPermissions:
    def test_no_roles(self):
        assert map_claims_to_permissions({}) == []

    def test_single_role(self):
        assert map_claims_to_permissions({"roles": ["kestra.flow.read"]}) == ["flow.read"]

    def test_multiple_roles(self):
        result = map_claims_to_permissions({
            "roles": ["kestra.flow.read", "kestra.flow.write"]
        })
        assert sorted(result) == ["flow.read", "flow.write"]


class TestHasRole:
    def test_has_role_true(self):
        assert has_role({"roles": ["kestra.flow.read"]}, "kestra.flow.read") is True

    def test_has_role_false(self):
        assert has_role({"roles": ["kestra.flow.read"]}, "kestra.flow.write") is False

    def test_no_roles_key(self):
        assert has_role({}, "kestra.flow.read") is False

    def test_roles_not_a_list(self):
        assert has_role({"roles": "not-a-list"}, "kestra.flow.read") is False


class TestGetRequiredRoleForTool:
    def test_read_tools_require_flow_read(self):
        assert get_required_role_for_tool("list_flows") == "kestra.flow.read"
        assert get_required_role_for_tool("get_flow") == "kestra.flow.read"
        assert get_required_role_for_tool("get_execution") == "kestra.flow.read"

    def test_write_tool_requires_flow_write(self):
        assert get_required_role_for_tool("create_or_update_flow") == "kestra.flow.write"

    def test_execute_tool_requires_flow_execute(self):
        assert get_required_role_for_tool("execute_flow") == "kestra.flow.execute"

    def test_unknown_tool_returns_none(self):
        assert get_required_role_for_tool("nonexistent_tool") is None


class TestGetIdentity:
    def test_full_claims(self):
        claims = {"sub": "user-1", "name": "Alice", "tid": "tenant-1"}
        result = get_identity(claims)
        assert result["sub"] == "user-1"
        assert result["name"] == "Alice"
        assert result["tid"] == "tenant-1"

    def test_partial_claims(self):
        result = get_identity({"sub": "user-1"})
        assert result["sub"] == "user-1"
        assert result["name"] is None
        assert result["tid"] is None
