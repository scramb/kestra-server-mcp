"""kill_execution MCP tool -- stops a running execution."""

from src.client.kestra_client import KestraError
from src.server import get_kestra_client


async def handle(arguments: dict) -> dict:
    """Kill/stop a running execution."""
    kestra_client = get_kestra_client()
    execution_id = arguments["execution_id"]

    try:
        result = await kestra_client.kill_execution(execution_id)
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

    return result if result else {"status": "killed", "execution_id": execution_id}
