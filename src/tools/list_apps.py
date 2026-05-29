"""list_apps MCP tool -- lists Kestra apps from the catalog."""

from src.client.kestra_client import KestraError
from src.server import get_kestra_client


async def handle(_arguments: dict) -> dict:
    """List available apps from the catalog."""
    kestra_client = get_kestra_client()

    try:
        result = await kestra_client.list_apps()
    except KestraError as e:
        return {
            "error": True,
            "code": "UPSTREAM_ERROR",
            "status_code": e.status_code,
            "message": str(e),
        }

    if isinstance(result, list):
        return {"apps": result}
    return result
