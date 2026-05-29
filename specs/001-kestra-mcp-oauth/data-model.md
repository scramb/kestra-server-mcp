# Data Model: Kestra MCP OAuth MVP

**Date**: 2026-05-29 | **Related**: [plan.md](./plan.md), [spec.md](./spec.md)

## Entities

### Authenticated Session

Active user access context. In-memory only — no persistent storage.

| Field | Type | Description |
|-------|------|-------------|
| `identity` | `str` | User principal name (UPN) or object ID from Entra token `sub` claim |
| `tenant_id` | `str` | Entra tenant ID from token `tid` claim |
| `roles` | `list[str]` | App roles from token `roles` claim (e.g., `kestra.flow.read`) |
| `access_token` | `str` | Entra access token (opaque to MCP user, used for Kestra API calls) |
| `token_expires_at` | `datetime` | Access token expiry (UTC) |
| `refresh_token` | `str` | Refresh token for silent renewal |

**Lifecycle**: Created on OAuth login → refreshed silently → invalidated on logout or expiry.

**Identity rule**: `(identity, tenant_id)` uniquely identifies a session. Only one active session per identity per server instance.

### Permission Grant

Derived from Entra app roles, maps to Kestra tool access.

| Field | Type | Description |
|-------|------|-------------|
| `role` | `str` | Entra app role name (e.g., `kestra.flow.read`) |
| `tools` | `list[str]` | MCP tool names enabled by this role |
| `domain` | `str` | Permission domain: `flow.read`, `flow.write`, `flow.execute` |

**Mapping table**:

| Entra Role | Tools | Kestra API Domain |
|------------|-------|-------------------|
| `kestra.flow.read` | `list_flows`, `get_flow`, `get_execution` | Read flows + executions |
| `kestra.flow.write` | `create_or_update_flow` | Write flows |
| `kestra.flow.execute` | `execute_flow` | Execute flows |

**Default**: No roles → only `auth_status` visible.

### Flow Descriptor

Flow reference returned by `list_flows` and `get_flow`. Mirrors Kestra API response.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Flow ID |
| `namespace` | `str` | Flow namespace |
| `revision` | `int` | Current revision number |
| `disabled` | `bool` | Whether the flow is disabled |
| `deleted` | `bool` | Whether the flow is soft-deleted |
| `source` | `str` (optional) | Flow YAML source (included in `get_flow`, excluded from `list_flows`) |

### Flow Definition Payload

Submitted to `create_or_update_flow`. Wraps the Kestra flow definition.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Flow ID (must match source) |
| `namespace` | `str` | Target namespace |
| `source` | `str` | Flow definition as YAML string |

**Validation**: Source must be valid YAML. `id` and `namespace` extracted from source for routing.

### Execution Record

Returned by `execute_flow` and `get_execution`. Mirrors Kestra API response.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Execution ID |
| `namespace` | `str` | Namespace |
| `flow_id` | `str` | Flow ID |
| `flow_revision` | `int` | Flow revision at execution time |
| `state` | `dict` | State object with `current` (str) and `histories` (list) |
| `inputs` | `dict` | Input values provided at execution |
| `url` | `str` | Link to Kestra UI for this execution |

**State transitions** (Kestra-managed): `CREATED` → `RUNNING` → `SUCCESS` / `FAILED` / `WARNING` / `KILLED`.

## Relationships

```
Authenticated Session (1) ──has──▶ (0..N) Permission Grant
Authenticated Session (1) ──proxies──▶ Kestra API via Access Token
Permission Grant (1) ──enables──▶ Tool visibility
Flow Descriptor ──is a──▶ Kestra API flow resource
Flow Definition Payload ──creates/updates──▶ Kestra API flow resource
Execution Record ──is a──▶ Kestra API execution resource
```
