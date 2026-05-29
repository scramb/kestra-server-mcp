"""Kestra MCP server entry point and tool registration."""

import json
import logging
from typing import Any

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from src.client.kestra_client import KestraClient
from src.config import Config, load_config

logger = logging.getLogger("kestra-mcp")

# Global state; initialized at startup
_kestra_client: KestraClient | None = None
_config: Config | None = None


def get_kestra_client() -> KestraClient:
    assert _kestra_client is not None
    return _kestra_client


def get_config() -> Config:
    assert _config is not None
    return _config


# === Tool Definitions ===

def _build_tool_definitions() -> list[types.Tool]:
    return [
        types.Tool(
            name="register_kestra_token",
            description=(
                "Register your personal Kestra API token. Required before using any Kestra tools. "
                "Call this after authenticating to store your Kestra API token for this session."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "token": {
                        "type": "string",
                        "description": (
                            "Your Kestra API token (from Kestra UI -> "
                            "Administration -> Users)."
                        ),
                    },
                },
                "required": ["token"],
            },
        ),
        types.Tool(
            name="auth_status",
            description=(
                "Check your authentication status and available tool permissions. "
                "Returns whether you are authenticated and which MCP tools are available."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="search_namespaces",
            description="Search and list Kestra namespaces.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="list_flows",
            description="List Kestra flows in a namespace.",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "The flow namespace (e.g., 'company.team').",
                    },
                },
                "required": ["namespace"],
            },
        ),
        types.Tool(
            name="get_flow",
            description="Get a single Kestra flow including its YAML source.",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "The flow namespace (e.g., 'company.team').",
                    },
                    "flow_id": {
                        "type": "string",
                        "description": "The flow ID.",
                    },
                },
                "required": ["namespace", "flow_id"],
            },
        ),
        types.Tool(
            name="create_or_update_flow",
            description=(
                "Create or update a Kestra flow from a YAML definition. "
                "The source must be valid YAML containing at minimum 'id' and 'namespace' fields."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Flow definition as a YAML string.",
                    },
                },
                "required": ["source"],
            },
        ),
        types.Tool(
            name="execute_flow",
            description=(
                "Execute a Kestra flow. Optionally pass input values to the flow execution."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "The flow namespace (e.g., 'company.team').",
                    },
                    "flow_id": {
                        "type": "string",
                        "description": "The flow ID to execute.",
                    },
                    "inputs": {
                        "type": "object",
                        "description": "Optional key-value pairs for flow inputs.",
                    },
                },
                "required": ["namespace", "flow_id"],
            },
        ),
        types.Tool(
            name="get_execution",
            description="Get details of a Kestra execution.",
            inputSchema={
                "type": "object",
                "properties": {
                    "execution_id": {
                        "type": "string",
                        "description": "The execution ID (returned by execute_flow).",
                    },
                },
                "required": ["execution_id"],
            },
        ),
        types.Tool(
            name="list_executions",
            description="List executions for a specific flow.",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "The flow namespace.",
                    },
                    "flow_id": {
                        "type": "string",
                        "description": "The flow ID.",
                    },
                },
                "required": ["namespace", "flow_id"],
            },
        ),
        types.Tool(
            name="kill_execution",
            description="Kill/stop a running execution.",
            inputSchema={
                "type": "object",
                "properties": {
                    "execution_id": {
                        "type": "string",
                        "description": "The execution ID to kill.",
                    },
                },
                "required": ["execution_id"],
            },
        ),
        types.Tool(
            name="search_triggers",
            description="Search Kestra triggers, optionally filtered by namespace.",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "Optional namespace filter.",
                    },
                },
                "required": [],
            },
        ),
        types.Tool(
            name="list_apps",
            description="List Kestra apps from the catalog.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="get_app",
            description="Get details of a Kestra app by UID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "uid": {
                        "type": "string",
                        "description": "The app UID.",
                    },
                },
                "required": ["uid"],
            },
        ),
        types.Tool(
            name="create_app",
            description="Create a new Kestra app from JSON data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_data": {
                        "type": "object",
                        "description": "The app definition as a JSON object.",
                    },
                },
                "required": ["app_data"],
            },
        ),
    ]


def create_server() -> Server:
    """Create and configure the MCP server with all tools registered."""
    global _kestra_client, _config

    _config = load_config()
    _kestra_client = KestraClient(_config.kestra)
    _server = Server("kestra-mcp")

    # Import tool handlers
    from src.tools.auth_status import handle as auth_status_handle
    from src.tools.create_app import handle as create_app_handle
    from src.tools.create_or_update import handle as create_or_update_handle
    from src.tools.execute_flow import handle as execute_flow_handle
    from src.tools.get_app import handle as get_app_handle
    from src.tools.get_execution import handle as get_execution_handle
    from src.tools.get_flow import handle as get_flow_handle
    from src.tools.kill_execution import handle as kill_execution_handle
    from src.tools.list_apps import handle as list_apps_handle
    from src.tools.list_executions import handle as list_executions_handle
    from src.tools.list_flows import handle as list_flows_handle
    from src.tools.register_token import handle as register_token_handle
    from src.tools.search_namespaces import handle as search_namespaces_handle
    from src.tools.search_triggers import handle as search_triggers_handle

    TOOL_HANDLERS = {
        "auth_status": auth_status_handle,
        "register_kestra_token": register_token_handle,
        "search_namespaces": search_namespaces_handle,
        "list_flows": list_flows_handle,
        "get_flow": get_flow_handle,
        "create_or_update_flow": create_or_update_handle,
        "execute_flow": execute_flow_handle,
        "get_execution": get_execution_handle,
        "list_executions": list_executions_handle,
        "kill_execution": kill_execution_handle,
        "search_triggers": search_triggers_handle,
        "list_apps": list_apps_handle,
        "get_app": get_app_handle,
        "create_app": create_app_handle,
    }

    @_server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return _build_tool_definitions()

    @_server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
        """Dispatch tool call to the correct handler."""
        handler = TOOL_HANDLERS.get(name)
        if handler is None:
            return [types.TextContent(type="text", text=json.dumps({
                "error": True,
                "code": "NOT_FOUND",
                "message": f"Unknown tool: {name}",
            }, indent=2))]

        try:
            result = await handler(arguments)
        except Exception as e:
            logger.exception("Tool %s failed", name)
            return [types.TextContent(type="text", text=json.dumps({
                "error": True,
                "code": "UPSTREAM_ERROR",
                "message": str(e),
            }, indent=2))]

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    return _server


async def run_streamable_http() -> None:
    """Run the MCP server with Streamable HTTP transport and OAuth Authorization Server."""
    import contextlib
    import os

    import uvicorn
    from mcp.server.auth.routes import (
        create_auth_routes,
        create_protected_resource_routes,
    )
    from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from pydantic import AnyHttpUrl
    from starlette.applications import Starlette
    from starlette.routing import Route

    from src.auth.entra_callback import create_entra_callback_handler
    from src.auth.provider import EntraAuthProvider
    from src.auth.routes import build_routes
    from src.auth.session import AuthMiddleware
    from src.auth.stores import (
        AuthCodeStore,
        AuthSessionStore,
        ClientStore,
        RefreshTokenStore,
    )
    from src.auth.token_store import TokenStore

    server = create_server()
    session_manager = StreamableHTTPSessionManager(app=server)
    token_store = TokenStore.from_config(_config.encryption_key)
    from src.tools.register_token import set_token_store
    set_token_store(token_store)
    from src.auth.session import set_session_token_store
    set_session_token_store(token_store)

    # --- Compute URLs ---
    host = _config.server.host
    port = _config.server.port
    issuer_url = os.getenv("AUTH_SERVER_ISSUER_URL", f"http://{host}:{port}")
    entra_callback_url = os.getenv(
        "OIDC_REDIRECT_URI", f"{issuer_url}/oauth/entra-callback"
    )
    access_token_ttl = int(os.getenv("ACCESS_TOKEN_TTL_SECONDS", "3600"))

    issuer = AnyHttpUrl(issuer_url)
    resource_url = AnyHttpUrl(f"{issuer_url}/mcp")

    # --- OAuth stores ---
    client_store = ClientStore()
    auth_session_store = AuthSessionStore()
    auth_code_store = AuthCodeStore()
    refresh_token_store = RefreshTokenStore()

    # --- OAuth provider ---
    provider = EntraAuthProvider(
        client_store=client_store,
        auth_session_store=auth_session_store,
        auth_code_store=auth_code_store,
        refresh_token_store=refresh_token_store,
        oidc_config=_config.oidc,
        token_signing_key=_config.encryption_key,
        access_token_ttl=access_token_ttl,
        entra_callback_url=entra_callback_url,
    )

    # --- SDK routes: OAuth Authorization Server ---
    auth_routes = create_auth_routes(
        provider=provider,
        issuer_url=issuer,
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=["kestra.read", "kestra.write"],
            default_scopes=["kestra.read", "kestra.write"],
        ),
        revocation_options=RevocationOptions(enabled=True),
    )

    # --- SDK routes: Protected Resource Metadata (RFC 9728) ---
    protected_routes = create_protected_resource_routes(
        resource_url=resource_url,
        authorization_servers=[issuer],
        scopes_supported=["kestra.read", "kestra.write"],
    )

    # --- Kestra token management routes ---
    kestra_routes = build_routes(_config.oidc, token_store)

    # --- Entra callback handler ---
    entra_callback = create_entra_callback_handler(
        _config.oidc, auth_session_store, auth_code_store
    )

    class _MCPEndpoint:
        def __init__(self, handler):
            self.handler = handler

        async def __call__(self, scope, receive, send):
            await self.handler(scope, receive, send)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        async with session_manager.run():
            yield

    app = Starlette(
        lifespan=lifespan,
        routes=[
            # SDK OAuth Authorization Server routes
            *auth_routes,
            # SDK Protected Resource Metadata routes
            *protected_routes,
            # MCP endpoint
            Route("/mcp", endpoint=_MCPEndpoint(session_manager.handle_request)),
            # Entra ID callback
            Route(
                "/oauth/entra-callback",
                endpoint=entra_callback,
                methods=["GET"],
                name="entra_callback",
            ),
            # Kestra API token management
            Route("/kestra-token", endpoint=kestra_routes["store_token"], methods=["POST"]),
            Route("/kestra-token/remove", endpoint=kestra_routes["remove_token"], methods=["POST"]),
            Route("/auth", endpoint=kestra_routes["auth_status_page"]),
        ],
    )

    # Wrap with Kestra token resolution middleware (only intercepts /mcp)
    app = AuthMiddleware(app, provider, token_store)

    cfg = _config.server
    uvicorn_config = uvicorn.Config(
        app, host=cfg.host, port=cfg.port, log_level="info"
    )
    uv_server = uvicorn.Server(uvicorn_config)
    await uv_server.serve()


async def run_stdio() -> None:
    """Run the MCP server with stdio transport."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


def main() -> None:
    """Entry point. Detects transport mode and starts the server."""
    import asyncio
    import sys

    cfg = load_config()

    # CLI commands for token management
    if len(sys.argv) > 1:
        _handle_cli(cfg, sys.argv[1:])
        return

    if cfg.server.transport == "stdio":
        asyncio.run(run_stdio())
    else:
        asyncio.run(run_streamable_http())


def _handle_cli(cfg: Config, args: list[str]) -> None:
    """Handle CLI commands for token management."""
    from src.auth.token_store import TokenStore

    store = TokenStore.from_config(cfg.encryption_key)

    if args[0] == "add-token":
        if len(args) != 3:
            print("Usage: kestra-mcp add-token <token> <user-id>")
            return
        token, user_id = args[1], args[2]
        store.store_token(user_id, token)
        print(f"Token stored for user: {user_id}")

    elif args[0] == "remove-token":
        if len(args) != 2:
            print("Usage: kestra-mcp remove-token <user-id>")
            return
        user_id = args[1]
        if store.remove_token(user_id):
            print(f"Token removed for user: {user_id}")
        else:
            print(f"No token found for user: {user_id}")

    elif args[0] == "list-users":
        users = store.list_users()
        if users:
            print("Users with stored tokens:")
            for u in users:
                print(f"  {u}")
        else:
            print("No stored tokens.")

    elif args[0] == "generate-key":
        from cryptography.fernet import Fernet
        print(Fernet.generate_key().decode())

    else:
        print(f"Unknown command: {args[0]}")
        print("Commands: add-token, remove-token, list-users, generate-key")


if __name__ == "__main__":
    main()
