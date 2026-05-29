"""create_app MCP tool -- creates a new Kestra app."""

from src.client.kestra_client import KestraError
from src.server import get_kestra_client


async def handle(arguments: dict) -> dict:
    """Create a new app from JSON data."""
    kestra_client = get_kestra_client()
    app_data = arguments["app_data"]

    try:
        result = await kestra_client.create_app(app_data)
    except KestraError as e:
        return {
            "error": True,
            "code": "UPSTREAM_ERROR",
            "status_code": e.status_code,
            "message": str(e),
        }

    return result
