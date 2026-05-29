# Implementation Plan: Kestra MCP OAuth MVP

**Branch**: `001-kestra-mcp-oauth` | **Date**: 2026-05-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-kestra-mcp-oauth/spec.md`

## Summary

Build a Python MCP server that authenticates users via OAuth 2.1 / Microsoft Entra, delegates
authorization to Kestra's RBAC model, and exposes six MCP tools backed by the Kestra REST API.
Primary transport is remote HTTPS MCP with a local stdio/uv fallback. JWT tokens are validated
against Entra JWKS endpoints, with token claims mapped to Kestra permissions per-request.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: mcp (Python MCP SDK >=1.0), httpx (async HTTP client), pyjwt, msal (Microsoft Authentication Library), pytest

**Storage**: Session state in-memory (no persistent storage for MVP); Entra tenant config via environment variables

**Testing**: pytest, pytest-asyncio, pytest-httpx (HTTP mocking), pytest-mock

**Target Platform**: Linux server (HTTPS transport) + macOS/Linux developer workstation (stdio/uv fallback)

**Project Type**: MCP server (Python package)

**Performance Goals**: SC-004 targets — 3s for status/read, 5s for write/execute initiation under normal conditions

**Constraints**: Single-tenant (one Entra tenant per deployment), deny-by-default authorization, HTTPS primary transport required

**Scale/Scope**: MVP — 6 tools (auth_status, list_flows, get_flow, create_or_update_flow, execute_flow, get_execution), single Kestra instance

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Kestra API Scope Gate**: PASS — All 6 planned tools map to concrete Kestra REST API endpoints (see contracts/). No documentation scraping.
- **Security-First Gate**: PASS — Trust boundary defined at MCP server ↔ Kestra API boundary. JWT validated via Entra JWKS. Secrets (Entra client secret, Kestra API token) via environment variables only. Attack-aware failures: expired/invalid JWTs rejected pre-request, upstream Kestra errors sanitized.
- **Identity Gate**: PASS — OAuth 2.1 authorization code flow with PKCE via MSAL. Token refresh uses refresh token (silent). Entra JWKS endpoint for JWT signature validation. Required scope: `openid profile` for identity, Kestra API token for upstream auth.
- **Authorization Gate**: PASS — Deny-by-default: every tool handler checks Entra claims → maps to Kestra permission domain → validates against Kestra API on each request. Missing/ambiguous permissions = denial with reason.
- **Transport Gate**: PASS — HTTPS primary via MCP HTTP transport. stdio/uv fallback preserves same auth/authorization chain via environment-based config. Fallback justified: developer tooling convenience; auth guarantees preserved because Entra JWT validation is transport-agnostic.

## Project Structure

### Documentation (this feature)

```text
specs/001-kestra-mcp-oauth/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── auth_status.json
│   ├── list_flows.json
│   ├── get_flow.json
│   ├── create_or_update_flow.json
│   ├── execute_flow.json
│   └── get_execution.json
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/
├── __init__.py
├── server.py            # MCP server entry point, transport setup
├── auth/
│   ├── __init__.py
│   ├── oauth.py         # Entra OAuth 2.1 flow (MSAL), token acquisition/refresh
│   ├── jwt_validator.py # JWT validation against Entra JWKS
│   └── permissions.py   # Claims-to-Kestra-permission mapping, deny-by-default
├── client/
│   ├── __init__.py
│   └── kestra_client.py # Async HTTP client for Kestra REST API (httpx)
├── tools/
│   ├── __init__.py
│   ├── auth_status.py   # auth_status MCP tool
│   ├── list_flows.py    # list_flows MCP tool
│   ├── get_flow.py      # get_flow MCP tool
│   ├── create_or_update.py  # create_or_update_flow MCP tool
│   ├── execute_flow.py  # execute_flow MCP tool
│   └── get_execution.py # get_execution MCP tool
└── config.py            # Environment-based configuration (tenant ID, client ID, etc.)

tests/
├── __init__.py
├── conftest.py          # pytest fixtures (mock Kestra API, mock Entra JWKS, config)
├── test_auth/
│   ├── test_oauth.py
│   ├── test_jwt_validator.py
│   └── test_permissions.py
├── test_client/
│   └── test_kestra_client.py
├── test_tools/
│   ├── test_auth_status.py
│   ├── test_list_flows.py
│   ├── test_get_flow.py
│   ├── test_create_or_update.py
│   ├── test_execute_flow.py
│   └── test_get_execution.py
└── test_integration/
    └── test_mcp_server.py  # End-to-end MCP server tests

pyproject.toml           # uv/pip project config, dependencies, entry points
uv.lock                  # uv lock file
```

**Structure Decision**: Single Python project with `src/` layout. Auth, client, and tools are separate packages for testability and clear boundaries. Tests mirror the source structure. No frontend — this is a headless MCP server.

## Complexity Tracking

> No violations. All constitution gates pass.
