# Research: Kestra MCP OAuth MVP

**Date**: 2026-05-29 | **Related**: [plan.md](./plan.md), [spec.md](./spec.md)

## Decisions

### 1. MCP Server Framework: `mcp` Python SDK

**Decision**: Use the official `mcp` Python package (>=1.0) for MCP server implementation and tool registration.

**Rationale**:
- Official Anthropic-maintained Python SDK for MCP protocol
- Built-in support for both stdio and HTTP/SSE transports
- Decorator-based tool registration (`@server.tool()`) simplifies implementation
- Active development and community support

**Alternatives considered**:
- FastMCP (standalone HTTP server) — less mature, fewer protocol features
- Manual JSON-RPC over stdio — unnecessary reinvention
- `starlette`/`fastapi` custom server — would need to implement MCP protocol from scratch

### 2. Entra OAuth 2.1: MSAL Python Library

**Decision**: Use `msal` (Microsoft Authentication Library for Python) for Entra OAuth 2.1 authorization code flow with PKCE.

**Rationale**:
- Microsoft-supported, actively maintained
- Built-in PKCE enforcement for authorization code flow
- Token cache support (in-memory for MVP)
- Handles token refresh transparently via `acquire_token_silent()`
- Works with Entra ID and Azure AD endpoints

**Alternatives considered**:
- Direct OAuth 2.1 HTTP calls — more code to maintain, needs PKCE implementation
- `azure-identity` — oriented toward Azure SDK, heavier dependency
- `authlib` — general OAuth library, no Entra-specific convenience

### 3. JWT Validation: `PyJWT` + Requests to JWKS Endpoint

**Decision**: Use `PyJWT` with manual JWKS key fetching (cached in-memory with TTL) from the Entra `jwks_uri` (at `https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys`).

**Rationale**:
- `PyJWT` is the dominant Python JWT library, supports RS256/ES256
- Entra JWKS endpoints are well-known, stable URLs
- In-memory key cache with TTL (1 hour) is sufficient for single-process MVP
- Avoids dependency on `python-jose` (less maintained) or `jwcrypto` (heavier)

**Key caching strategy**: Fetch JWKS on first validation, cache for 60 minutes, refetch on cache miss or key not found. Rotate keys gracefully by retrying once on validation failure with fresh fetch.

**Alternatives considered**:
- `python-jose` — maintenance has slowed significantly
- `msal` built-in ID token validation — only validates ID tokens, not access tokens
- Dedicated JWKS client library — unnecessary dependency

### 4. Claims-to-Permissions Mapping

**Decision**: Map Entra token claims (specifically `roles` claim from app roles) to Kestra permission domains. The MCP server maps these to Kestra API token scopes or passes the Entra identity to Kestra for RBAC evaluation.

**Mapping**:
- `roles: ["kestra.flow.read"]` → can call `list_flows`, `get_flow`, `get_execution`
- `roles: ["kestra.flow.write"]` → can call `create_or_update_flow`
- `roles: ["kestra.flow.execute"]` → can call `execute_flow`
- No roles → only `auth_status` available

**Rationale**:
- Entra app roles provide a standard, self-contained permission model
- No dependency on group membership resolution (avoids Graph API call)
- Clean separation: Entra owns identity + role assignment; Kestra owns RBAC enforcement on the API side
- The MCP server acts as middleware: maps claims to tool visibility, then Kestra enforces actual access

**Alternatives considered**:
- Entra security groups — requires Microsoft Graph API call to resolve, adds latency and dependency
- Custom token claims — requires Entra claims mapping policy, harder to administer
- Kestra API token per user — would require per-user API token provisioning, too heavy for MVP

### 5. Kestra API Client: `httpx` Async

**Decision**: Use `httpx` with async support (`httpx.AsyncClient`) for all Kestra API calls. Single connection pool, reusable across tool handlers.

**Rationale**:
- `mcp` SDK is async-native, so the client must be async
- `httpx` is the modern async HTTP client for Python (replaces `requests` + `aiohttp`)
- Connection pooling, timeout support, retry hooks built in
- Supports `application/x-yaml` content type for flow create/update

**Kestra API endpoints used**:
| Tool | Method | Path |
|------|--------|------|
| list_flows | GET | `/api/v1/flows` |
| get_flow | GET | `/api/v1/flows/{namespace}/{flowId}` |
| create_or_update_flow | POST | `/api/v1/flows` |
| execute_flow | POST | `/api/v1/executions/{namespace}/{flowId}` |
| get_execution | GET | `/api/v1/executions/{executionId}` |

Authentication to Kestra API: Bearer token via Kestra API token (configured in environment, not per-user).

**Alternatives considered**:
- `aiohttp` — works but `httpx` has better API ergonomics and broader ecosystem
- `requests` (sync) — incompatible with async MCP server
- Kestra Python SDK (if exists) — no official maintained Python SDK

### 6. Transport Strategy: HTTPS Primary, stdio/uv Fallback

**Decision**: Primary deployment via `mcp` SDK's SSE/HTTP transport (HTTPS behind reverse proxy). Fallback via `mcp` SDK's stdio transport invoked by `uv run kestra-mcp`.

**Rationale**:
- HTTPS transport enables remote access (IDE ↔ remote server), core value prop
- stdio fallback via `uv run` provides zero-config local development with same tool handlers
- Both transports use identical tool registration — no code duplication
- Security guarantees preserved across transports since JWT validation is independent of transport layer

**Implementation**: Entry point `src/server.py` detects transport mode from environment (`KESTRA_MCP_TRANSPORT=stdio|sse`) and starts the appropriate server.

**Alternatives considered**:
- SSE-only — loses local development convenience
- stdio-only — no remote access, defeats primary use case

### 7. Project Setup: uv

**Decision**: Use `uv` for dependency management, virtual environments, and `pyproject.toml`-based project configuration.

**Rationale**:
- Fast, modern Python package manager
- Single `pyproject.toml` for both project metadata and dependencies
- `uv run` enables the stdio transport fallback without manual venv activation
- Lock file (`uv.lock`) ensures reproducible installs

**Alternatives considered**:
- `poetry` — mature but slower; `uv` is faster and gaining adoption
- `pip` + `venv` — manual venv management adds friction
- `pdm` — less ecosystem momentum than `uv`

### 8. Testing: pytest with Async Support

**Decision**: Use `pytest` + `pytest-asyncio` + `pytest-httpx` for HTTP mocking + `pytest-mock` for general mocking.

**Rationale**:
- `pytest` is the Python testing standard
- `pytest-asyncio` enables testing async MCP tool handlers directly
- `pytest-httpx` intercepts httpx calls to mock Kestra API responses
- JWKS endpoint can be mocked via `pytest-httpx` or a custom fixture with generated test keys

**Test categories**:
- Unit tests: auth logic, permission mapping, JWT validation
- Tool tests: each tool handler with mocked Kestra client, verifying auth gating
- Integration tests: MCP server via stdio, full request/response cycle
