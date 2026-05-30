# Security Policy

## Reporting a vulnerability

If you discover a security vulnerability, please **do not** open a public issue. Instead, email the maintainers at hello@kestra.io with details.

We will acknowledge your report within 48 hours and aim to provide a timeline for a fix within 5 business days.

## Supported versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | :white_check_mark: |

## Security model

The Kestra MCP Server handles authentication and authorization at every layer:

- **Transport**: Streamable HTTP with OAuth 2.1 bearer tokens, or local stdio (trusted environment).
- **Identity**: User authentication via OIDC providers (Entra ID, Google, Okta, Keycloak). JWTs are validated against the provider's JWKS endpoint on every request.
- **Authorization**: Deny-by-default. Identity provider claims are mapped to Kestra permission domains. Each tool invocation checks permissions before calling the Kestra API.
- **Secrets**: All secrets (client secrets, encryption keys, API tokens) are configured via environment variables only. Never commit `.env` files or hard-code credentials.
- **Token storage**: Kestra API tokens are encrypted at rest using Fernet symmetric encryption. The encryption key is derived from the `ENCRYPTION_KEY` environment variable.

## Best practices for deployment

1. Always run behind a TLS-terminating reverse proxy (nginx, Caddy) in production.
2. Rotate the `ENCRYPTION_KEY` periodically.
3. Restrict the `OIDC_REDIRECT_URI` to your server's public URL.
4. Run with least-privilege service accounts.
5. Keep dependencies updated: `uv sync --upgrade` regularly.
