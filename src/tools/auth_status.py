"""auth_status MCP tool — reports authentication state and permissions."""

from typing import TYPE_CHECKING

from mcp.server import Server

from src.auth.permissions import (
    get_identity,
    map_claims_to_permissions,
    map_claims_to_tools,
)

if TYPE_CHECKING:
    from src.auth.oauth import SessionManager


def get_auth_status(
    identity: str | None = None,
    session_manager: "SessionManager | None" = None,
) -> dict:
    """Return auth status for a given session identity.

    If identity is None, returns unauthenticated state.
    session_manager can be injected for testing; if None, uses the global.
    """
    if session_manager is None:
        from src.server import get_session_manager

        session_manager = get_session_manager()

    if identity is None:
        return {
            "authenticated": False,
            "identity": None,
            "tenant_id": None,
            "permissions": [],
            "available_tools": ["auth_status"],
        }

    session = session_manager.get_session(identity)
    if session is None:
        return {
            "authenticated": False,
            "identity": None,
            "tenant_id": None,
            "permissions": [],
            "available_tools": ["auth_status"],
        }

    claims = session["claims"]
    identity_info = get_identity(claims)
    return {
        "authenticated": True,
        "identity": identity_info.get("name") or identity_info.get("sub"),
        "tenant_id": identity_info.get("tid"),
        "permissions": map_claims_to_permissions(claims),
        "available_tools": map_claims_to_tools(claims),
    }


def register_auth_status(server: Server) -> None:
    """Register the auth_status tool on the MCP server."""

    @server.tool()
    async def auth_status() -> dict:
        """Check your authentication status and available tool permissions.

        Returns whether you are authenticated, your identity, and which
        MCP tools you are authorized to use based on your Entra roles.
        """
        return get_auth_status(identity=None)
