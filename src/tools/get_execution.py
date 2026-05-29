"""get_execution MCP tool — retrieves execution details."""

from mcp.server import Server

from src.client.kestra_client import KestraClient, KestraError
from src.server import get_kestra_client


async def handle_get_execution(
    execution_id: str,
    kestra_client: KestraClient | None = None,
) -> dict:
    """Get execution details by ID.

    Requires kestra.flow.read role. Deny-by-default.
    """
    if kestra_client is None:
        kestra_client = get_kestra_client()

    try:
        result = await kestra_client.get_execution(execution_id)
    except KestraError as e:
        if e.status_code == 404:
            return {
                "error": True,
                "code": "NOT_FOUND",
                "message": f"Execution '{execution_id}' not found",
            }
        return {
            "error": True,
            "code": "UPSTREAM_ERROR",
            "status_code": e.status_code,
            "message": str(e),
        }

    return result


def register_get_execution(server: Server) -> None:
    @server.tool()
    async def get_execution(
        execution_id: str,
    ) -> dict:
        """Get details of a Kestra execution.

        Requires the 'kestra.flow.read' Entra role.

        Args:
            execution_id: The execution ID (returned by execute_flow).
        """
        return await handle_get_execution(execution_id=execution_id)
