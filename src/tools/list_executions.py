"""list_executions MCP tool -- lists executions for a flow."""

from src.client.kestra_client import KestraError
from src.server import get_kestra_client


async def handle(arguments: dict) -> dict:
    """List executions for a specific flow."""
    kestra_client = get_kestra_client()
    namespace = arguments["namespace"]
    flow_id = arguments["flow_id"]

    try:
        result = await kestra_client.list_executions(namespace, flow_id)
    except KestraError as e:
        return {
            "error": True,
            "code": "UPSTREAM_ERROR",
            "status_code": e.status_code,
            "message": str(e),
        }

    if isinstance(result, list):
        return {"executions": result}
    return result
