"""execute_flow MCP tool — starts execution of a flow."""

from mcp.server import Server

from src.client.kestra_client import KestraClient, KestraError
from src.server import get_kestra_client


async def handle_execute_flow(
    namespace: str,
    flow_id: str,
    inputs: dict | None = None,
    kestra_client: KestraClient | None = None,
) -> dict:
    """Execute a Kestra flow.

    Requires kestra.flow.execute role. Deny-by-default.
    """
    if kestra_client is None:
        kestra_client = get_kestra_client()

    try:
        result = await kestra_client.execute_flow(namespace, flow_id, inputs)
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


def register_execute_flow(server: Server) -> None:
    @server.tool()
    async def execute_flow(
        namespace: str,
        flow_id: str,
        inputs: dict | None = None,
    ) -> dict:
        """Execute a Kestra flow.

        Requires the 'kestra.flow.execute' Entra role. Optionally pass
        input values to the flow execution.

        Args:
            namespace: The flow namespace (e.g., 'company.team').
            flow_id: The flow ID to execute.
            inputs: Optional key-value pairs for flow inputs.
        """
        return await handle_execute_flow(namespace=namespace, flow_id=flow_id, inputs=inputs)
