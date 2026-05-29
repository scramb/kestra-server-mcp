"""create_or_update_flow MCP tool — creates or updates a flow from YAML."""

import yaml as yaml_lib

from src.client.kestra_client import KestraError
from src.server import get_kestra_client


async def handle(arguments: dict) -> dict:
    """Create or update a Kestra flow from YAML source.

    Validates that source is parsable YAML before sending.
    """
    kestra_client = get_kestra_client()
    source = arguments["source"]

    try:
        yaml_lib.safe_load(source)
    except yaml_lib.YAMLError as e:
        return {
            "error": True,
            "code": "INVALID_YAML",
            "message": f"Source is not valid YAML: {e}",
        }

    try:
        result = await kestra_client.create_or_update_flow(source)
    except KestraError as e:
        return {
            "error": True,
            "code": "UPSTREAM_ERROR",
            "status_code": e.status_code,
            "message": str(e),
        }

    return result
