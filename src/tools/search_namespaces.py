"""search_namespaces MCP tool -- lists all accessible namespaces."""

from src.client.kestra_client import KestraError
from src.server import get_kestra_client


async def handle(_arguments: dict) -> dict:
    """Search and list all accessible namespaces."""
    kestra_client = get_kestra_client()

    try:
        result = await kestra_client.search_namespaces()
    except KestraError as e:
        return {
            "error": True,
            "code": "UPSTREAM_ERROR",
            "status_code": e.status_code,
            "message": str(e),
        }

    if isinstance(result, list):
        return {"namespaces": result}
    return result
