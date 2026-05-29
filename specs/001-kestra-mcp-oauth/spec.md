# Feature Specification: Kestra MCP OAuth MVP

**Feature Branch**: `001-kestra-mcp-oauth`

**Created**: 2026-05-29

**Status**: Draft

**Input**: User description: "Build a Kestra MCP server with OAuth 2.1/Entra authentication, permission-based tool visibility, and MVP tools: auth_status, list_flows, get_flow, create_or_update_flow, execute_flow, get_execution."

## Clarifications

### Session 2026-05-29

- Q: How are Entra identities/permissions mapped to MCP tool permissions? → A: Use Kestra's own permission model — Entra handles authentication (identity), while authorization is delegated to Kestra's existing RBAC/permission system.
- Q: What happens when a token is expired between tool discovery and tool execution? → A: Automatic silent refresh — the server stores a refresh token and transparently renews the access token when expired.
- Q: How does the system handle permission changes during an active session? → A: Per-request validation — every MCP tool call re-checks permissions against the Kestra API in real-time.
- Q: Is the MCP server single-tenant or multi-tenant? How is the tenant determined? → A: Single-tenant — each deployment is bound to one Entra tenant, pre-configured at deployment time.
- Q: What happens when the upstream Kestra API is unavailable or returns errors? → A: Map Kestra API errors to MCP error responses with the original HTTP status code and a sanitized message (no stack traces or internal details exposed).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Verify secure access status (Priority: P1)

As an operator, I can verify whether I am authenticated and what tool permissions
I currently have so I know what actions I am allowed to perform before attempting
flow operations.

**Why this priority**: This is the entry point for trust and safe usage; users must
know access state before making any potentially impactful call.

**Independent Test**: Can be fully tested by signing in, calling `auth_status`, and
confirming the returned access state and permissions accurately reflect the session.

**Acceptance Scenarios**:

1. **Given** a signed-in user with granted permissions, **When** the user requests
   authentication status, **Then** the system returns authenticated state and the
   effective permission set.
2. **Given** a user without a valid session, **When** the user requests
   authentication status, **Then** the system returns unauthenticated state and no
   operational permissions.

---

### User Story 2 - View flows within allowed scope (Priority: P2)

As an authorized user, I can list flows and inspect a specific flow only when I
have read permission, so that I can safely discover and review available workflows.

**Why this priority**: Read-only visibility is the minimum operational capability
needed before users can safely perform write or execute operations.

**Independent Test**: Can be fully tested by calling `list_flows` and `get_flow`
with different permission sets and validating allow/deny behavior plus returned data.

**Acceptance Scenarios**:

1. **Given** a user with flow-read permission, **When** the user lists flows,
   **Then** the system returns flows visible to that user scope.
2. **Given** a user without flow-read permission, **When** the user attempts to
   list or get a flow, **Then** the system denies access with a clear permission
   error.

---

### User Story 3 - Modify and execute flows with explicit permissions (Priority: P3)

As an authorized user, I can create or update flows, execute a flow, and check
execution status only when I hold the required write/execute permissions, so that
changes and runs are controlled and auditable.

**Why this priority**: This delivers core operational value while preserving
security boundaries through permission-gated actions.

**Independent Test**: Can be fully tested by performing create/update, execute,
and execution-status requests with and without required permissions, verifying
both successful and denied paths.

**Acceptance Scenarios**:

1. **Given** a user with flow-write permission, **When** the user submits a
   create/update request, **Then** the flow is saved and a success result is
   returned.
2. **Given** a user with flow-execute permission, **When** the user executes a
   flow and requests execution status, **Then** the system starts the execution and
   returns execution details for that run.

---

### Edge Cases

- Token expiry between tool discovery and tool execution is handled via automatic silent refresh using stored refresh tokens — the user does not need to re-authenticate.
- Permission changes during an active session take effect immediately — each MCP tool call validates permissions against Kestra in real-time, so changed permissions are enforced on the next request without session reset.
- What happens when a user can execute a flow but no longer has permission to read
  that execution afterward?
- How does the system respond when a requested flow identifier does not exist?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide an `auth_status` capability that reports
  whether the current user is authenticated and what effective permissions are
  granted.
- **FR-002**: The system MUST make tool visibility permission-based so users are
  shown only tools they are authorized to use.
- **FR-003**: The system MUST allow authorized users to list flows and deny
  unauthorized users.
- **FR-004**: The system MUST allow authorized users to retrieve a single flow and
  deny unauthorized users.
- **FR-005**: The system MUST allow authorized users to create or update a flow
  and deny unauthorized users.
- **FR-006**: The system MUST allow authorized users to start flow execution and
  deny unauthorized users.
- **FR-007**: The system MUST allow authorized users to retrieve execution details
  and deny unauthorized users.
- **FR-008**: Authentication MUST rely on OAuth 2.1 with Microsoft Entra as the
  identity provider. Authorization (permission evaluation) MUST delegate to
  Kestra's existing RBAC/permission model.
- **FR-009**: Authorization MUST follow deny-by-default behavior where missing or
  ambiguous permissions result in refusal.
- **FR-010**: User-facing security failures MUST return clear reason categories
  (unauthenticated, insufficient permission, invalid or expired session).
- **FR-011**: The MCP server is single-tenant — each deployment is bound to one
  pre-configured Entra tenant. All flow and execution actions operate within that
  tenant scope.
- **FR-012**: Operation outcomes (allowed, denied, succeeded, failed) MUST be
  auditable without exposing sensitive credentials.
- **FR-013**: When the upstream Kestra API is unavailable or returns errors, the MCP
  server MUST respond with an MCP error that includes the mapped HTTP status code and
  a sanitized reason (no raw stack traces or internal details exposed).

### Key Entities *(include if feature involves data)*

- **Authenticated Session**: Active user access context including identity,
  session validity, tenant scope, and granted permissions.
- **Permission Grant**: Allowed capability tied to an action domain (for example:
  read flows, write flows, execute flows, read executions).
- **Flow Descriptor**: Flow reference and metadata used for listing and retrieval.
- **Flow Definition Payload**: Submitted flow content and target identifier for
  create/update operations.
- **Execution Record**: Launched flow execution instance and its current status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of unauthorized requests to MVP capabilities are denied with a
  clear, user-actionable reason.
- **SC-002**: At least 95% of authorized users can complete the full MVP journey
  (check status → list/get flow → execute flow → get execution) on first attempt.
- **SC-003**: 100% of capability discovery results reflect effective permissions
  for the active session (no unauthorized capabilities shown).
- **SC-004**: For valid authorized requests, users receive operation results within
  3 seconds for status/read actions and within 5 seconds for write/execute
  initiation under normal operating conditions.

## Assumptions

- Primary users are platform operators and engineers with existing enterprise
  identities in Microsoft Entra.
- OAuth consent and permission assignment are managed by organization admins
  outside this feature's scope.
- Flow and execution identifiers are unique and already governed by existing
  workspace conventions.
- MVP scope includes only the six named capabilities and excludes broader
  workflow management capabilities.
- Audit output retention is handled by existing organizational logging policies.