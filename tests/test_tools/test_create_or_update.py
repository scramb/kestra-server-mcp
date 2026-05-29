"""Tests for create_or_update_flow tool."""

import pytest

from src.client.kestra_client import KestraClient
from src.tools.create_or_update import handle_create_or_update_flow


class TestCreateOrUpdateFlow:
    VALID_YAML = """
id: test-flow
namespace: company.team
tasks:
  - id: hello
    type: io.kestra.plugin.core.log.Log
    message: Hello
"""

    @pytest.mark.asyncio
    async def test_creates_flow(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows",
            method="POST",
            json={"id": "test-flow", "namespace": "company.team", "revision": 1},
        )
        async with KestraClient.from_url(
            "http://localhost:8080/api/v1", api_token="test-token"
        ) as client:
            result = await handle_create_or_update_flow(
                source=self.VALID_YAML, kestra_client=client
            )
        assert result["id"] == "test-flow"
        assert result["revision"] == 1

    @pytest.mark.asyncio
    async def test_rejects_invalid_yaml(self):
        async with KestraClient.from_url(
            "http://localhost:8080/api/v1", api_token="test-token"
        ) as client:
            result = await handle_create_or_update_flow(
                source="not: valid: yaml: [", kestra_client=client
            )
        assert result["error"] is True
        assert result["code"] == "INVALID_YAML"

    @pytest.mark.asyncio
    async def test_handles_upstream_error(self, httpx_mock):
        httpx_mock.add_response(
            url="http://localhost:8080/api/v1/flows",
            method="POST",
            status_code=422,
        )
        async with KestraClient.from_url(
            "http://localhost:8080/api/v1", api_token="test-token"
        ) as client:
            result = await handle_create_or_update_flow(
                source=self.VALID_YAML, kestra_client=client
            )
        assert result["error"] is True
        assert result["code"] == "UPSTREAM_ERROR"
