"""Tests for auth_status tool."""


from src.tools.auth_status import get_auth_status


class TestAuthStatusUnauthenticated:
    def test_returns_unauthenticated_when_identity_none(self, session_manager):
        result = get_auth_status(identity=None, session_manager=session_manager)
        assert result["authenticated"] is False
        assert result["identity"] is None
        assert result["tenant_id"] is None
        assert result["permissions"] == []
        assert result["available_tools"] == ["auth_status"]

    def test_returns_unauthenticated_when_session_not_found(self, session_manager):
        result = get_auth_status(identity="nonexistent-user", session_manager=session_manager)
        assert result["authenticated"] is False
        assert result["available_tools"] == ["auth_status"]


class TestAuthStatusAuthenticated:
    def test_returns_authenticated_with_roles(
        self, session_manager, full_claims, test_entra_config
    ):
        token_result = {
            "access_token": "fake-access",
            "refresh_token": "fake-refresh",
        }
        identity = session_manager.create_session(
            full_claims, token_result, test_entra_config
        )

        result = get_auth_status(identity=identity, session_manager=session_manager)
        assert result["authenticated"] is True
        assert result["identity"] is not None
        assert result["tenant_id"] == "test-tenant-id"
        assert "flow.read" in result["permissions"]
        assert "flow.write" in result["permissions"]
        assert "flow.execute" in result["permissions"]
        assert "auth_status" in result["available_tools"]

    def test_read_only_user_sees_read_tools(
        self, session_manager, read_only_claims, test_entra_config
    ):
        token_result = {
            "access_token": "fake-access",
            "refresh_token": "fake-refresh",
        }
        identity = session_manager.create_session(
            read_only_claims, token_result, test_entra_config
        )

        result = get_auth_status(identity=identity, session_manager=session_manager)
        assert result["authenticated"] is True
        assert result["permissions"] == ["flow.read"]
        assert "list_flows" in result["available_tools"]
        assert "get_flow" in result["available_tools"]
        assert "create_or_update_flow" not in result["available_tools"]
        assert "execute_flow" not in result["available_tools"]

    def test_no_roles_user_sees_only_auth_status(
        self, session_manager, no_role_claims, test_entra_config
    ):
        token_result = {
            "access_token": "fake-access",
            "refresh_token": "fake-refresh",
        }
        identity = session_manager.create_session(
            no_role_claims, token_result, test_entra_config
        )

        result = get_auth_status(identity=identity, session_manager=session_manager)
        assert result["authenticated"] is True
        assert result["permissions"] == []
        assert result["available_tools"] == ["auth_status"]
