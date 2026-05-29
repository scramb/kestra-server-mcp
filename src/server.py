"""Kestra MCP server entry point and tool registration."""


from mcp.server import Server
from mcp.server.stdio import stdio_server

from src.auth.oauth import SessionManager
from src.auth.permissions import get_required_role_for_tool, has_role
from src.client.kestra_client import KestraClient
from src.config import Config, load_config

# Global state; initialized at startup
_server: Server | None = None
_session_manager: SessionManager | None = None
_kestra_client: KestraClient | None = None
_config: Config | None = None


def get_session_manager() -> SessionManager:
    assert _session_manager is not None
    return _session_manager


def get_kestra_client() -> KestraClient:
    assert _kestra_client is not None
    return _kestra_client


def get_config() -> Config:
    assert _config is not None
    return _config


def require_role(claims: dict | None, tool_name: str) -> None:
    """Raise PermissionError if session doesn't have required role for the tool.

    Deny-by-default: missing session or missing role = refusal.
    """
    required_role = get_required_role_for_tool(tool_name)
    if required_role is None:
        return  # No role required

    if not claims:
        raise PermissionError("UNAUTHENTICATED: No valid session. Please sign in.")

    if not has_role(claims, required_role):
        raise PermissionError(
            f"INSUFFICIENT_PERMISSION: '{tool_name}' requires role '{required_role}'"
        )


def create_server() -> Server:
    """Create and configure the MCP server with all tools registered."""
    global _server, _session_manager, _kestra_client, _config

    _config = load_config()
    _session_manager = SessionManager()
    _kestra_client = KestraClient(_config.kestra)
    _server = Server("kestra-mcp")

    # Import tools here to avoid circular imports
    from src.tools.auth_status import register_auth_status
    from src.tools.create_or_update import register_create_or_update_flow
    from src.tools.execute_flow import register_execute_flow
    from src.tools.get_execution import register_get_execution
    from src.tools.get_flow import register_get_flow
    from src.tools.list_flows import register_list_flows

    register_auth_status(_server)
    register_list_flows(_server)
    register_get_flow(_server)
    register_create_or_update_flow(_server)
    register_execute_flow(_server)
    register_get_execution(_server)

    return _server


async def run_sse() -> None:
    """Run the MCP server with SSE/HTTP transport."""
    import uvicorn
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Route

    _server = create_server()
    sse = SseServerTransport("/messages")

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as (read_stream, write_stream):
            await _server.run(
                read_stream, write_stream, _server.create_initialization_options()
            )

    async def handle_messages(request):
        await sse.handle_post_message(request.scope, request.receive, request._send)

    app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages", endpoint=handle_messages, methods=["POST"]),
        ]
    )

    cfg = _config.server
    uvicorn_config = uvicorn.Config(
        app, host=cfg.host, port=cfg.port, log_level="info"
    )
    server = uvicorn.Server(uvicorn_config)
    await server.serve()


async def run_stdio() -> None:
    """Run the MCP server with stdio transport."""
    _server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await _server.run(
            read_stream, write_stream, _server.create_initialization_options()
        )


def main() -> None:
    """Entry point. Detects transport mode and starts the server."""
    import asyncio

    # Load config early to validate env vars
    cfg = load_config()

    if cfg.server.transport == "stdio":
        asyncio.run(run_stdio())
    else:
        # Default to SSE/HTTP
        asyncio.run(run_sse())


if __name__ == "__main__":
    main()
