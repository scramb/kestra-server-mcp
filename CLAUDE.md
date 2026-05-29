<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the plan at
`/specs/001-kestra-mcp-oauth/plan.md` which includes:

- Python 3.11+ with uv package manager
- MCP SDK for server implementation (HTTPS/SSE primary, stdio fallback)
- MSAL for Entra OAuth 2.1, PyJWT for JWKS-based JWT validation
- httpx async client for Kestra REST API calls
- Entra app roles → Kestra permission mapping
- pytest with pytest-asyncio and pytest-httpx for testing
<!-- SPECKIT END -->
