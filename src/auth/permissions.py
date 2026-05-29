"""Claims-to-permissions mapping. Deny-by-default."""

from typing import Any

# Entra app role → MCP tool mapping
ROLE_TOOL_MAP: dict[str, list[str]] = {
    "kestra.flow.read": ["list_flows", "get_flow", "get_execution"],
    "kestra.flow.write": ["create_or_update_flow"],
    "kestra.flow.execute": ["execute_flow"],
}

# Role → permission domain label
ROLE_DOMAIN_MAP: dict[str, str] = {
    "kestra.flow.read": "flow.read",
    "kestra.flow.write": "flow.write",
    "kestra.flow.execute": "flow.execute",
}


def map_claims_to_tools(claims: dict[str, Any]) -> list[str]:
    """Map Entra token claims to allowed MCP tool names.

    Returns list of tool names the user is authorized to use.
    Always includes auth_status regardless of roles.
    """
    roles: list[str] = claims.get("roles", [])
    if not isinstance(roles, list):
        roles = []

    tools: set[str] = {"auth_status"}
    for role in roles:
        role_tools = ROLE_TOOL_MAP.get(role, [])
        tools.update(role_tools)
    return sorted(tools)


def map_claims_to_permissions(claims: dict[str, Any]) -> list[str]:
    """Map Entra token claims to permission domain labels."""
    roles: list[str] = claims.get("roles", [])
    if not isinstance(roles, list):
        roles = []

    permissions: set[str] = set()
    for role in roles:
        domain = ROLE_DOMAIN_MAP.get(role)
        if domain:
            permissions.add(domain)
    return sorted(permissions)


def get_identity(claims: dict[str, Any]) -> dict[str, str | None]:
    """Extract identity fields from claims."""
    return {
        "sub": claims.get("sub"),
        "name": claims.get("name"),
        "tid": claims.get("tid"),
    }


def has_role(claims: dict[str, Any], role: str) -> bool:
    """Check if claims contain a specific role."""
    roles: list[str] = claims.get("roles", [])
    if not isinstance(roles, list):
        return False
    return role in roles


def get_required_role_for_tool(tool_name: str) -> str | None:
    """Return the role required for a given tool, or None if no role required."""
    TOOL_ROLE_MAP: dict[str, str] = {
        "list_flows": "kestra.flow.read",
        "get_flow": "kestra.flow.read",
        "get_execution": "kestra.flow.read",
        "create_or_update_flow": "kestra.flow.write",
        "execute_flow": "kestra.flow.execute",
    }
    return TOOL_ROLE_MAP.get(tool_name)
