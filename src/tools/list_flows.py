"""list_flows MCP tool — lists flows visible to the user."""

from mcp.server import Server

from src.client.kestra_client import KestraClient, KestraError
from src.server import get_kestra_client


async def handle_list_flows(
    namespace: str | None = None,
    kestra_client: KestraClient | None = None,
) -> dict:
    """List flows, optionally filtered by namespace.

    Requires kestra.flow.read role. Deny-by-default.
    """
    if kestra_client is None:
        kestra_client = get_kestra_client()

    try:
        result = await kestra_client.list_flows(namespace)
    except KestraError as e:
        return {
            "error": True,
            "code": "UPSTREAM_ERROR",
            "status_code": e.status_code,
            "message": str(e),
        }

    # Kestra returns a list of flows, wrap in dict
    if isinstance(result, list):
        return {"flows": result}
    return {"flows": result.get("results", [])}


def register_list_flows(server: Server) -> None:
    @server.tool()
    async def list_flows(
        namespace: str | None = None,
    ) -> dict:
        """List Kestra flows visible to your scope.

        Requires the 'kestra.flow.read' Entra role. Optionally filter
        by namespace to narrow results.

        Args:
            namespace: Optional namespace filter (e.g., 'company.team').
        """
        return await handle_list_flows(namespace=namespace)
