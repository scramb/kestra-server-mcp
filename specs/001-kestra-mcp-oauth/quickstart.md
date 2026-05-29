# Quickstart: Kestra MCP OAuth MVP

## Prerequisites

- Python 3.11+
- uv (https://docs.astral.sh/uv/getting-started/installation/)
- Access to a Kestra instance (OSS or Enterprise) with API access
- An Entra ID app registration with authorized redirect URIs

## Setup

### 1. Clone and enter project

```bash
git clone <repo-url> && cd kestra-server-mcp
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure environment

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```ini
# Entra OAuth
ENTRA_TENANT_ID=your-tenant-id
ENTRA_CLIENT_ID=your-client-id
ENTRA_CLIENT_SECRET=your-client-secret

# Kestra API
KESTRA_API_URL=https://your-kestra-instance/api/v1
KESTRA_API_TOKEN=your-kestra-api-token

# Transport mode: "sse" for remote HTTPS, "stdio" for local
KESTRA_MCP_TRANSPORT=sse
KESTRA_MCP_PORT=8081
KESTRA_MCP_HOST=127.0.0.1

# Optional: redirect URI for OAuth callback
MCP_REDIRECT_URI=http://127.0.0.1:8081/oauth/callback
```

### 4. Run the server

**HTTPS/SSE transport** (remote access):

```bash
uv run kestra-mcp
# Server starts on http://127.0.0.1:8081
# In production, run behind nginx/caddy with TLS
```

**stdio transport** (local IDE integration):

```bash
KESTRA_MCP_TRANSPORT=stdio uv run kestra-mcp
```

### 5. Connect an MCP client

Add to your MCP client configuration (e.g., Claude Code):

```json
{
  "mcpServers": {
    "kestra": {
      "url": "http://127.0.0.1:8081/sse"
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

### 6. Authenticate

1. Call `auth_status` — it will tell you to authenticate
2. Visit the OAuth URL returned by the server
3. Sign in with your Entra account
4. Call `auth_status` again — you should be authenticated with your role-based permissions

## Verify

```bash
# Run tests
uv run pytest

# Run with specific test file
uv run pytest tests/test_tools/test_auth_status.py -v
```

## Project commands

| Command | Description |
|---------|-------------|
| `uv run kestra-mcp` | Start the MCP server |
| `uv run pytest` | Run all tests |
| `uv run pytest -v` | Verbose test output |
| `uv run pytest --cov=src` | Run with coverage |
| `uv run ruff check src/` | Lint source code |
| `uv sync --extra dev` | Install dev dependencies |

## Architecture overview

```
MCP Client ──HTTP/SSE──▶ MCP Server ──httpx──▶ Kestra API
                           │
                           ├── auth/ (Entra OAuth, JWT validation, permissions)
                           ├── client/ (Kestra REST client)
                           └── tools/ (6 MCP tool handlers)
```
