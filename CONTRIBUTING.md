# Contributing to Kestra MCP Server

Thanks for your interest in contributing. This document outlines the process for contributing code, docs, and other improvements.

## Getting started

1. **Fork** the repository and clone it locally.
2. **Install** dependencies with `uv sync`.
3. **Copy** `.env.example` to `.env` and configure it for local development.
4. **Run tests** with `uv run pytest` to make sure everything works.

## Development workflow

```bash
# Create a branch for your changes
git checkout -b feature/my-change

# Make changes and run tests
uv run pytest

# Lint your code
uv run ruff check src/ tests/

# Format your code
uv run ruff format src/ tests/
```

### Running the server locally

```bash
# Streamable HTTP mode (full OAuth)
uv run kestra-mcp

# stdio mode (local IDE integration)
KESTRA_MCP_TRANSPORT=stdio uv run kestra-mcp
```

## Code conventions

- **Python 3.11+** with type hints on public APIs.
- Format with **ruff**, line length 100.
- Tests with **pytest** and **pytest-asyncio**.
- Follow the existing project structure: `src/auth/`, `src/client/`, `src/tools/`.
- Deny-by-default authorization — every tool handler checks permissions.

## Pull request process

1. Ensure tests pass and new features include test coverage.
2. Update the README if your change affects user-facing behavior.
3. Use a descriptive PR title and fill out the PR template.
4. All contributions are licensed under Apache 2.0 (see [LICENSE](LICENSE)).

## Reporting bugs

Open an issue using the **Bug Report** template. Include:
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, Kestra version, OIDC provider)
- Relevant logs or error messages

## Feature requests

Open an issue using the **Feature Request** template. Describe:
- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered

## Security

See [SECURITY.md](SECURITY.md) for our security policy and how to report vulnerabilities.

## Code of Conduct

All contributors must follow our [Code of Conduct](CODE_OF_CONDUCT.md).
