"""Async HTTP client for Kestra REST API."""

from typing import Any

import httpx

from src.config import KestraConfig


class KestraError(Exception):
    """Sanitized upstream Kestra API error."""

    def __init__(self, status_code: int, reason: str):
        self.status_code = status_code
        self.reason = reason
        super().__init__(f"Kestra API error {status_code}: {reason}")


class KestraClient:
    """Async HTTP client for the Kestra REST API.

    All methods return parsed JSON. Non-2xx responses raise KestraError
    with the status code and a sanitized reason (no raw response bodies).
    """

    def __init__(self, config: KestraConfig) -> None:
        self._config = config
        self._base_url = config.api_url
        headers = {
            "Accept": "application/json",
        }
        if config.api_token:
            headers["Authorization"] = f"Bearer {config.api_token}"
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=30.0,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._client.aclose()

    async def close(self) -> None:
        await self._client.aclose()

    @classmethod
    def from_url(cls, url: str, api_token: str = "") -> "KestraClient":
        return cls(KestraConfig(api_url=url.rstrip("/"), api_token=api_token))

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an API request and handle errors."""
        try:
            resp = await self._client.request(method, path, **kwargs)
        except httpx.TimeoutException:
            raise KestraError(504, "Kestra API timeout") from None
        except httpx.RequestError as e:
            raise KestraError(
                503, f"Kestra unavailable: {_sanitize_error(e)}"
            ) from e

        if resp.is_success:
            return resp.json() if resp.content else {}

        # Map HTTP status to sanitized error
        reason_map = {
            400: "Bad request",
            401: "Authentication failed",
            403: "Access denied",
            404: "Resource not found",
            409: "Conflict",
            422: "Validation error",
            429: "Rate limited",
            500: "Internal server error",
            502: "Bad gateway",
            503: "Service unavailable",
        }
        reason = reason_map.get(resp.status_code, "Unexpected error")
        raise KestraError(resp.status_code, reason)

    async def list_flows(self, namespace: str | None = None) -> dict[str, Any]:
        """List flows, optionally filtered by namespace."""
        params = {}
        if namespace:
            params["namespace"] = namespace
        return await self._request("GET", "/flows", params=params or None)

    async def get_flow(self, namespace: str, flow_id: str) -> dict[str, Any]:
        """Get a single flow by namespace and ID."""
        return await self._request("GET", f"/flows/{namespace}/{flow_id}")

    async def create_or_update_flow(self, source_yaml: str) -> dict[str, Any]:
        """Create or update a flow from YAML source."""
        return await self._request(
            "POST",
            "/flows",
            content=source_yaml,
            headers={"Content-Type": "application/x-yaml"},
        )

    async def execute_flow(
        self,
        namespace: str,
        flow_id: str,
        inputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a flow, optionally with inputs as form data."""
        data = {}
        if inputs:
            data = {k: str(v) for k, v in inputs.items()}
        return await self._request(
            "POST",
            f"/executions/{namespace}/{flow_id}",
            data=data or None,
        )

    async def get_execution(self, execution_id: str) -> dict[str, Any]:
        """Get execution details by ID."""
        return await self._request("GET", f"/executions/{execution_id}")


def _sanitize_error(error: Exception) -> str:
    """Return a sanitized error message without internal details."""
    msg = str(error)
    if len(msg) > 200:
        msg = msg[:197] + "..."
    return msg
