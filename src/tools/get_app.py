"""get_app MCP tool -- gets details of a Kestra app."""

from src.client.kestra_client import KestraError
from src.server import get_kestra_client


async def handle(arguments: dict) -> dict:
    """Get a single app by UID."""
    kestra_client = get_kestra_client()
    uid = arguments["uid"]

    try:
        result = await kestra_client.get_app(uid)
    except KestraError as e:
        if e.status_code == 404:
            return {
                "error": True,
                "code": "NOT_FOUND",
                "message": f"App '{uid}' not found",
            }
        return {
            "error": True,
            "code": "UPSTREAM_ERROR",
            "status_code": e.status_code,
            "message": str(e),
        }

    return result
