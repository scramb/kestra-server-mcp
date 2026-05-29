# Permission Matrix: Kestra MCP OAuth MVP

**Date**: 2026-05-29 | **Related**: [plan.md](./plan.md)

## Tool Permissions

| Tool | Required Entra Role | No Role Behavior | Failure Mode |
|------|--------------------| -----------------|--------------|
| `auth_status` | none | Always visible, reports unauthenticated | N/A (always succeeds) |
| `list_flows` | `kestra.flow.read` | Hidden from tool list; call returns INSUFFICIENT_PERMISSION | Deny |
| `get_flow` | `kestra.flow.read` | Hidden from tool list; call returns INSUFFICIENT_PERMISSION | Deny |
| `create_or_update_flow` | `kestra.flow.write` | Hidden from tool list; call returns INSUFFICIENT_PERMISSION | Deny |
| `execute_flow` | `kestra.flow.execute` | Hidden from tool list; call returns INSUFFICIENT_PERMISSION | Deny |
| `get_execution` | `kestra.flow.read` | Hidden from tool list; call returns INSUFFICIENT_PERMISSION | Deny |

## Error Codes

| Code | Trigger | User-Actionable Message |
|------|---------|------------------------|
| `UNAUTHENTICATED` | No valid session or expired refresh token | "Please sign in with your Entra account" |
| `INSUFFICIENT_PERMISSION` | Missing required Entra role | "Tool '{name}' requires role '{role}'" |
| `NOT_FOUND` | Flow or execution ID not found (Kestra 404) | "Resource '{id}' not found" |
| `INVALID_YAML` | Flow source is not valid YAML | "Source is not valid YAML: {error}" |
| `UPSTREAM_ERROR` | Kestra API returned non-2xx (not 404) | "Kestra API error {status_code}: {reason}" |

## Authorization Flow

```
MCP Client Request
  │
  ├─ 1. Extract JWT from Authorization header
  ├─ 2. Validate JWT signature against Entra JWKS
  ├─ 3. Check token expiry → expired → UNAUTHENTICATED
  ├─ 4. Extract roles claim
  ├─ 5. Map roles to tool visibility
  │     ├─ No matching role → tool hidden (deny-by-default)
  │     └─ Match found → tool visible
  ├─ 6. On tool call: re-validate role (per-request)
  │     ├─ Missing role → INSUFFICIENT_PERMISSION
  │     └─ Role present → proceed
  ├─ 7. Proxy request to Kestra API
  │     ├─ 2xx → return result
  │     ├─ 404 → NOT_FOUND
  │     └─ non-2xx → UPSTREAM_ERROR (sanitized)
  └─ Response to MCP Client
```

## Security Guarantees

- **Deny-by-default**: No tool operates without explicit role check
- **Per-request validation**: Permission changes take effect on next call
- **No secrets in logs**: Access tokens, refresh tokens, client secrets never logged
- **Sanitized errors**: Upstream Kestra errors expose status codes but not internal stack traces
- **Single-tenant isolation**: Each deployment bound to one Entra tenant
