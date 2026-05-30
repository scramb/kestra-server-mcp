# Kestra MCP Server

<p align="center">
  <strong>Model Context Protocol server for <a href="https://kestra.io">Kestra</a> workflow orchestration</strong>
</p>

<p align="center">
  <a href="https://github.com/kestra-io/kestra-server-mcp/actions"><img src="https://img.shields.io/github/actions/workflow/status/kestra-io/kestra-server-mcp/pr-checks.yaml?branch=main" alt="CI"></a>
  <a href="https://pypi.org/project/kestra-mcp"><img src="https://img.shields.io/pypi/v/kestra-mcp" alt="PyPI"></a>
  <a href="https://www.apache.org/licenses/LICENSE-2.0"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License"></a>
  <a href="https://github.com/kestra-io/kestra-server-mcp/blob/main/CODE_OF_CONDUCT.md"><img src="https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg" alt="Code of Conduct"></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-Server-blue?logoColor=white" alt="MCP"></a>
</p>

---

Kestra MCP Server connects AI assistants (Claude, Copilot, etc.) to your [Kestra](https://kestra.io) instance through the [Model Context Protocol](https://modelcontextprotocol.io). It authenticates users via OAuth 2.1 / OpenID Connect (Entra ID, Google, Okta, Keycloak) and enforces role-based access control by mapping identity provider claims to Kestra permissions.

## Features

- **OAuth 2.1 / OIDC authentication** — Supports Entra ID, Google, Okta, Keycloak, and any OpenID Connect provider
- **Authorization Server** — Acts as a full OAuth 2.1 Authorization Server, issuing access tokens to MCP clients
- **Role-based access control** — Maps identity provider claims to Kestra permissions per request (deny-by-default)
- **Dual transport** — Streamable HTTP for remote access, stdio for local IDE integration
- **Kestra API token management** — Users register their Kestra token once per session for upstream API calls
- **JWT validation** — Validates tokens against identity provider JWKS endpoints with signature verification

### Available Tools

| Tool | Description |
|------|-------------|
| `auth_status` | Check authentication status and available tool permissions |
| `register_kestra_token` | Register a Kestra API token for upstream calls |
| `search_namespaces` | Search and list Kestra namespaces |
| `list_flows` | List flows in a namespace |
| `get_flow` | Get a flow including its YAML source |
| `create_or_update_flow` | Create or update a flow from a YAML definition |
| `execute_flow` | Execute a flow with optional input values |
| `get_execution` | Get details of an execution |
| `list_executions` | List executions for a flow |
| `kill_execution` | Kill a running execution |
| `search_triggers` | Search triggers, optionally filtered by namespace |
| `list_apps` | List Kestra apps from the catalog |
| `get_app` | Get app details by UID |
| `create_app` | Create a new app from JSON data |

## Quickstart

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager
- Access to a Kestra instance (OSS or Enterprise)
- An OIDC identity provider (Entra ID, Google, Okta, Keycloak, etc.)

### Install

```bash
pip install kestra-mcp
```

Or for local development:

```bash
git clone https://github.com/kestra-io/kestra-server-mcp.git
cd kestra-server-mcp
uv sync
```

### Configure

Create a `.env` file:

```bash
cp .env.example .env
```

Set the required environment variables:

```ini
# OpenID Connect (Entra ID, Google, Okta, Keycloak, etc.)
OIDC_ISSUER_URL=https://login.microsoftonline.com/<tenant-id>/v2.0
OIDC_CLIENT_ID=your-client-id
OIDC_CLIENT_SECRET=your-client-secret
OIDC_SCOPES=openid profile

# Kestra API
KESTRA_API_URL=http://localhost:8080/api/v1
KESTRA_TENANT=main

# Fernet encryption key (generate with: uv run kestra-mcp generate-key)
ENCRYPTION_KEY=your-fernet-key

# Transport: "http" for Streamable HTTP (remote), "stdio" for local
KESTRA_MCP_TRANSPORT=http
KESTRA_MCP_HOST=localhost
KESTRA_MCP_PORT=8081
```

### Run

**Streamable HTTP** (remote access, full OAuth support):

```bash
uv run kestra-mcp
```

**stdio** (local IDE integration):

```bash
KESTRA_MCP_TRANSPORT=stdio uv run kestra-mcp
```

### Connect an MCP client

Add to your MCP client configuration:

```json
{
  "mcpServers": {
    "kestra": {
      "url": "http://127.0.0.1:8081/mcp"
    }
  }
}
```

Or for stdio:

```json
{
  "mcpServers": {
    "kestra": {
      "command": "uv",
      "args": ["run", "kestra-mcp"],
      "env": {
        "KESTRA_MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

### CLI token management

```bash
uv run kestra-mcp add-token <kestra-api-token> <user-id>
uv run kestra-mcp remove-token <user-id>
uv run kestra-mcp list-users
uv run kestra-mcp generate-key
```

## Architecture

```
┌──────────────┐     MCP over HTTP     ┌────────────────────┐     httpx     ┌──────────────┐
│  MCP Client  │ ◄──────────────────► │  Kestra MCP Server │ ◄──────────► │  Kestra API  │
│ (Claude,     │                      │                    │              │  (REST)      │
│  Copilot)    │     OAuth 2.1        │  ┌──────────────┐  │              └──────────────┘
└──────────────┘     Authorization     │  │ auth/oauth    │  │
                     Server            │  │ jwt_validator │  │
                                       │  │ permissions   │  │
                                       │  ├──────────────┤  │
                                       │  │ client/       │  │
                                       │  ├──────────────┤  │
                                       │  │ tools/ (14)   │  │
                                       │  └──────────────┘  │
                                       └────────────────────┘
                                                │
                                                ▼
                                       ┌────────────────────┐
                                       │  OIDC Provider     │
                                       │ (Entra/Google/     │
                                       │  Okta/Keycloak)    │
                                       └────────────────────┘
```

## Development

```bash
# Install with dev dependencies
uv sync

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src

# Lint
uv run ruff check src/

# Format
uv run ruff format src/
```

## Project structure

```text
src/
├── server.py               # MCP server entry point, tool definitions
├── config.py               # Environment-based configuration
├── auth/
│   ├── oauth.py            # Entra OAuth 2.1 flow (MSAL)
│   ├── jwt_validator.py    # JWT validation against OIDC provider JWKS
│   ├── permissions.py      # Claims-to-Kestra-permission mapping
│   ├── provider.py         # OAuth Authorization Server provider
│   ├── session.py          # Session management and middleware
│   └── stores.py           # In-memory OAuth stores
├── client/
│   └── kestra_client.py    # Async HTTP client for Kestra REST API
└── tools/                  # 14 MCP tool handlers
    ├── auth_status.py
    ├── register_token.py
    ├── search_namespaces.py
    ├── list_flows.py
    ├── get_flow.py
    ├── create_or_update.py
    ├── execute_flow.py
    ├── get_execution.py
    ├── list_executions.py
    ├── kill_execution.py
    ├── search_triggers.py
    ├── list_apps.py
    ├── get_app.py
    └── create_app.py

tests/
├── conftest.py             # pytest fixtures
├── test_auth/              # Auth module tests
├── test_client/            # Kestra client tests
├── test_tools/             # Tool handler tests
└── test_integration/       # End-to-end MCP tests
```

## Contributing

We welcome contributions. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidelines.

## License

[Apache 2.0](LICENSE) — see the LICENSE file for full text.

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.
