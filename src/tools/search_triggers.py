"""search_triggers MCP tool -- searches Kestra triggers."""

from src.client.kestra_client import KestraError
from src.server import get_kestra_client


async def handle(arguments: dict) -> dict:
    """Search triggers, optionally filtered by namespace."""
    kestra_client = get_kestra_client()
    namespace = arguments.get("namespace")

    try:
        result = await kestra_client.search_triggers(namespace)
    except KestraError as e:
        return {
            "error": True,
            "code": "UPSTREAM_ERROR",
            "status_code": e.status_code,
            "message": str(e),
        }

    if isinstance(result, list):
        return {"triggers": result}
    return result
