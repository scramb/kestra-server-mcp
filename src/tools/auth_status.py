"""auth_status MCP tool -- reports authentication state."""

import os

from src.auth.session import current_user_id, get_current_token


async def handle(_arguments: dict) -> dict:
    """Report whether a user-bound Kestra token is available and show all tools."""
    try:
        token = get_current_token()
    except PermissionError:
        token = ""
    return {
        "authenticated": bool(current_user_id.get()),
        "token_configured": bool(token),
        "api_url": os.getenv("KESTRA_API_URL", ""),
        "available_tools": [
            "auth_status",
            "register_kestra_token",
            "search_namespaces",
            "list_flows",
            "get_flow",
            "create_or_update_flow",
            "execute_flow",
            "get_execution",
            "list_executions",
            "kill_execution",
            "search_triggers",
            "list_apps",
            "get_app",
            "create_app",
        ],
    }
