"""execute_flow MCP tool — starts execution of a flow."""

from src.client.kestra_client import KestraError
from src.server import get_kestra_client


async def handle(arguments: dict) -> dict:
    """Execute a Kestra flow."""
    kestra_client = get_kestra_client()
    namespace = arguments["namespace"]
    flow_id = arguments["flow_id"]
    inputs = arguments.get("inputs")

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
