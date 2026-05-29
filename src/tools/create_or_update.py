"""create_or_update_flow MCP tool — creates or updates a flow from YAML."""

import yaml as yaml_lib
from mcp.server import Server

from src.client.kestra_client import KestraClient, KestraError
from src.server import get_kestra_client


async def handle_create_or_update_flow(
    source: str,
    kestra_client: KestraClient | None = None,
) -> dict:
    """Create or update a Kestra flow from YAML source.

    Requires kestra.flow.write role. Deny-by-default.
    Validates that source is parsable YAML before sending.
    """
    if kestra_client is None:
        kestra_client = get_kestra_client()

    # Validate YAML before sending
    try:
        yaml_lib.safe_load(source)
    except yaml_lib.YAMLError as e:
        return {
            "error": True,
            "code": "INVALID_YAML",
            "message": f"Source is not valid YAML: {e}",
        }

    try:
        result = await kestra_client.create_or_update_flow(source)
    except KestraError as e:
        return {
            "error": True,
            "code": "UPSTREAM_ERROR",
            "status_code": e.status_code,
            "message": str(e),
        }

    return result


def register_create_or_update_flow(server: Server) -> None:
    @server.tool()
    async def create_or_update_flow(
        source: str,
    ) -> dict:
        """Create or update a Kestra flow from a YAML definition.

        Requires the 'kestra.flow.write' Entra role. The source must
        be valid YAML containing at minimum 'id' and 'namespace' fields.

        Args:
            source: Flow definition as a YAML string.
        """
        return await handle_create_or_update_flow(source=source)
