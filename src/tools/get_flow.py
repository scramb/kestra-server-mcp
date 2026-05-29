"""get_flow MCP tool — retrieves a single flow with YAML source."""

from mcp.server import Server

from src.client.kestra_client import KestraClient, KestraError
from src.server import get_kestra_client


async def handle_get_flow(
    namespace: str,
    flow_id: str,
    kestra_client: KestraClient | None = None,
) -> dict:
    """Get a single flow by namespace and ID.

    Requires kestra.flow.read role. Deny-by-default.
    """
    if kestra_client is None:
        kestra_client = get_kestra_client()

    try:
        result = await kestra_client.get_flow(namespace, flow_id)
    except KestraError as e:
        if e.status_code == 404:
            return {
                "error": True,
                "code": "NOT_FOUND",
                "message": f"Flow '{namespace}/{flow_id}' not found",
            }
        return {
            "error": True,
            "code": "UPSTREAM_ERROR",
            "status_code": e.status_code,
            "message": str(e),
        }

    return result


def register_get_flow(server: Server) -> None:
    @server.tool()
    async def get_flow(
        namespace: str,
        flow_id: str,
    ) -> dict:
        """Get a single Kestra flow including its YAML source.

        Requires the 'kestra.flow.read' Entra role.

        Args:
            namespace: The flow namespace (e.g., 'company.team').
            flow_id: The flow ID.
        """
        return await handle_get_flow(namespace=namespace, flow_id=flow_id)
