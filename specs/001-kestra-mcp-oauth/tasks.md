# Tasks: Kestra MCP OAuth MVP

**Input**: Design documents from `/specs/001-kestra-mcp-oauth/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included per user request for automated test coverage.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Mirrors plan.md structure: `src/auth/`, `src/client/`, `src/tools/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependency management, and configuration scaffolding

- [ ] T001 Create `pyproject.toml` with uv project config: Python 3.11+, dependencies (mcp>=1.0, httpx, pyjwt, msal), dev dependencies (pytest, pytest-asyncio, pytest-httpx, pytest-mock, ruff), and `[project.scripts]` entry point `kestra-mcp = "src.server:main"`
- [ ] T002 [P] Create `src/__init__.py`, `src/auth/__init__.py`, `src/client/__init__.py`, `src/tools/__init__.py`, `tests/__init__.py` and `tests/conftest.py` placeholder files
- [ ] T003 [P] Implement environment configuration in `src/config.py`: load from env vars (ENTRA_TENANT_ID, ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET, KESTRA_API_URL, KESTRA_API_TOKEN, KESTRA_MCP_TRANSPORT, KESTRA_MCP_HOST, KESTRA_MCP_PORT, MCP_REDIRECT_URI) with validation and defaults
- [ ] T004 [P] Create `.env.example` with all required env vars documented
- [ ] T005 [P] Configure ruff linting with `[tool.ruff]` section in pyproject.toml
- [ ] T006 Run `uv lock` to generate `uv.lock` and verify dependencies resolve

**Checkpoint**: Project builds, dependencies installed, configuration loads without errors

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Auth Infrastructure

- [ ] T007 Implement Entra OAuth 2.1 authorization code flow (MSAL) in `src/auth/oauth.py`: `acquire_token()`, `refresh_token_silent()`, `build_auth_url()`, `get_entra_config()` returning `{tenant_id, client_id, client_secret, authority, redirect_uri}` from config
- [ ] T008 [P] Implement JWT validation against Entra JWKS in `src/auth/jwt_validator.py`: `validate_token(token)` fetching JWKS from `https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys`, caching keys with 60-min TTL, validating `aud`, `iss`, `exp`, `nbf` claims, returning parsed claims dict
- [ ] T009 [P] Implement claims-to-permissions mapping in `src/auth/permissions.py`: `map_claims_to_tools(claims)` extracting `roles` claim, mapping `kestra.flow.read` → `[list_flows, get_flow, get_execution]`, `kestra.flow.write` → `[create_or_update_flow]`, `kestra.flow.execute` → `[execute_flow]`; `is_authenticated(claims)` for session validity; `get_identity(claims)` returning `{sub, name, tid}`
- [ ] T010 Implement `SessionManager` class in `src/auth/oauth.py`: `create_session(claims, tokens)`, `get_session(identity)`, `remove_session(identity)`, in-memory storage dict, handles token expiry and silent refresh via `refresh_token_silent`

### Kestra API Client

- [ ] T011 Implement async Kestra REST client in `src/client/kestra_client.py`: `KestraClient` class with `httpx.AsyncClient`, methods `list_flows(namespace?)`, `get_flow(namespace, flow_id)`, `create_or_update_flow(source_yaml)`, `execute_flow(namespace, flow_id, inputs?)`, `get_execution(execution_id)`; all return parsed JSON, map non-2xx responses to MCP-friendly errors with status code and sanitized message per FR-013

### MCP Server Skeleton

- [ ] T012 Implement MCP server entry point in `src/server.py`: `main()` function detecting transport mode from `KESTRA_MCP_TRANSPORT` env var, starting SSE/HTTP server on `KESTRA_MCP_HOST:KESTRA_MCP_PORT` or stdio server; `create_server()` factory registering all tools from `src/tools/`; OAuth callback endpoint for SSE mode

### Test Infrastructure

- [ ] T013 [P] Create `tests/conftest.py` with shared pytest fixtures: `mock_config` (monkeypatched env vars), `mock_jwks_client` (pytest-httpx for JWKS endpoint), `mock_kestra_api` (pytest-httpx for Kestra API), `valid_token` (generated test JWT), `expired_token` (expired test JWT), `session_manager` (pre-populated SessionManager)
- [ ] T014 [P] Create test auth fixtures in `tests/test_auth/conftest.py`: reusable mock Entra token responses, test JWKS key pair generation helper, sample claims dicts with various role combinations

**Checkpoint**: Foundation ready — auth flows work, Kestra client communicates, MCP server starts with both transports, test fixtures in place

---

## Phase 3: User Story 1 - Verify Secure Access Status (Priority: P1)

**Goal**: Users can call `auth_status` to see authentication state and available tool permissions. Unauthenticated users see no operational permissions. This is the entry point for all MCP interactions.

**Independent Test**: Start server, call `auth_status` without auth → returns `authenticated: false` and no tools. Authenticate via OAuth, call `auth_status` → returns `authenticated: true` with correct identity and permission list matching Entra roles.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T015 [P] [US1] Unit test for auth_status tool (unauthenticated path) in `tests/test_tools/test_auth_status.py`: verify returns `authenticated: false`, empty permissions, only `auth_status` in available_tools
- [ ] T016 [P] [US1] Unit test for auth_status tool (authenticated path with roles) in `tests/test_tools/test_auth_status.py`: verify returns `authenticated: true`, correct identity, matched permissions and tools from claims
- [ ] T017 [P] [US1] Unit test for OAuth session creation flow in `tests/test_auth/test_oauth.py`: test `acquire_token()` success, `build_auth_url()` correctness, `refresh_token_silent()` with expired token, token cache behavior
- [ ] T018 [P] [US1] Unit test for JWT validation in `tests/test_auth/test_jwt_validator.py`: test valid token passes, expired token fails, wrong issuer fails, wrong audience fails, JWKS key not found retry behavior
- [ ] T019 [P] [US1] Unit test for permissions mapping in `tests/test_auth/test_permissions.py`: test `map_claims_to_tools` with no roles, with `kestra.flow.read`, with all three roles, with unknown role (ignored), empty claims dict

### Implementation for User Story 1

- [ ] T020 [P] [US1] Implement `auth_status` MCP tool in `src/tools/auth_status.py`: `@server.tool()` decorator, checks session from request context, returns `{authenticated: bool, identity: str|null, tenant_id: str|null, permissions: list[str], available_tools: list[str]}` per contract `contracts/auth_status.json`
- [ ] T021 [US1] Wire auth_status tool into server in `src/server.py`: register tool from `src/tools/auth_status.py`, pass SessionManager and KestraClient via tool context/dependency injection
- [ ] T022 [US1] Implement permission-gated tool listing in `src/server.py`: `list_tools()` filtering based on session roles, so unauthenticated users see only `auth_status`, authorized users see all their mapped tools

**Checkpoint**: User Story 1 fully functional — `auth_status` reports correct auth state and tool visibility for any session state

---

## Phase 4: User Story 2 - View Flows Within Allowed Scope (Priority: P2)

**Goal**: Authorized users can list flows and inspect specific flows with YAML source. Users without `kestra.flow.read` role are denied with clear permission error. Users without any session get unauthenticated error.

**Independent Test**: Authenticate with `kestra.flow.read` role → call `list_flows` → returns flow list. Call `get_flow` with valid namespace/id → returns flow with source. Authenticate without `kestra.flow.read` → both tools hidden from discovery, call returns insufficient permission error.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T023 [P] [US2] Unit test for list_flows tool (authorized) in `tests/test_tools/test_list_flows.py`: mock Kestra API returns flow list, verify tool returns flows array correctly
- [ ] T024 [P] [US2] Unit test for list_flows tool (denied — no role) in `tests/test_tools/test_list_flows.py`: verify `INSUFFICIENT_PERMISSION` error with clear message
- [ ] T025 [P] [US2] Unit test for list_flows tool (denied — unauthenticated) in `tests/test_tools/test_list_flows.py`: verify `UNAUTHENTICATED` error
- [ ] T026 [P] [US2] Unit test for get_flow tool (authorized) in `tests/test_tools/test_get_flow.py`: mock Kestra API returns flow with source, verify tool returns full flow object
- [ ] T027 [P] [US2] Unit test for get_flow tool (not found) in `tests/test_tools/test_get_flow.py`: mock Kestra API 404, verify `NOT_FOUND` error
- [ ] T028 [P] [US2] Unit test for get_flow tool (denied — no role) in `tests/test_tools/test_get_flow.py`: verify `INSUFFICIENT_PERMISSION` error
- [ ] T029 [P] [US2] Unit test for Kestra API client methods in `tests/test_client/test_kestra_client.py`: test `list_flows()` with/without namespace filter, `get_flow()` success and 404, verify correct URL construction and auth header

### Implementation for User Story 2

- [ ] T030 [P] [US2] Implement `list_flows` MCP tool in `src/tools/list_flows.py`: `@server.tool()` decorator, checks `kestra.flow.read` role via permissions module, calls `KestraClient.list_flows(namespace)`, returns `{flows: [...]}` per contract `contracts/list_flows.json`
- [ ] T031 [P] [US2] Implement `get_flow` MCP tool in `src/tools/get_flow.py`: `@server.tool()` decorator, checks `kestra.flow.read` role, validates required inputs (namespace, flow_id), calls `KestraClient.get_flow(namespace, flow_id)`, returns flow object with source per contract `contracts/get_flow.json`
- [ ] T032 [US2] Register list_flows and get_flow tools in `src/server.py`'s `create_server()` factory

**Checkpoint**: User Stories 1 AND 2 both work — users with flow.read can discover and inspect flows, users without are denied

---

## Phase 5: User Story 3 - Modify and Execute Flows with Explicit Permissions (Priority: P3)

**Goal**: Authorized users can create/update flows (flow.write) and execute flows + check execution status (flow.execute, flow.read). All operations are permission-gated per-request against Entra roles.

**Independent Test**: With `kestra.flow.write` → create a flow, verify success. With `kestra.flow.execute` → execute a flow, get execution ID. With `kestra.flow.read` → retrieve execution details. Without appropriate roles → each tool denies with clear permission error.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T033 [P] [US3] Unit test for create_or_update_flow tool (authorized) in `tests/test_tools/test_create_or_update.py`: mock Kestra API success response, verify tool returns flow with new revision
- [ ] T034 [P] [US3] Unit test for create_or_update_flow tool (invalid YAML) in `tests/test_tools/test_create_or_update.py`: verify `INVALID_YAML` error on malformed source
- [ ] T035 [P] [US3] Unit test for create_or_update_flow tool (denied — no role) in `tests/test_tools/test_create_or_update.py`: verify `INSUFFICIENT_PERMISSION` error
- [ ] T036 [P] [US3] Unit test for create_or_update_flow tool (denied — unauthenticated) in `tests/test_tools/test_create_or_update.py`: verify `UNAUTHENTICATED` error
- [ ] T037 [P] [US3] Unit test for execute_flow tool (authorized) in `tests/test_tools/test_execute_flow.py`: mock Kestra API execution response, verify tool returns execution with state and URL
- [ ] T038 [P] [US3] Unit test for execute_flow tool (with inputs) in `tests/test_tools/test_execute_flow.py`: verify inputs are passed as form data to Kestra API
- [ ] T039 [P] [US3] Unit test for execute_flow tool (denied — no role) in `tests/test_tools/test_execute_flow.py`: verify `INSUFFICIENT_PERMISSION` error
- [ ] T040 [P] [US3] Unit test for execute_flow tool (flow not found) in `tests/test_tools/test_execute_flow.py`: mock Kestra API 404, verify `NOT_FOUND` error
- [ ] T041 [P] [US3] Unit test for get_execution tool (authorized) in `tests/test_tools/test_get_execution.py`: mock Kestra API returns execution with task runs and outputs, verify tool returns full execution record
- [ ] T042 [P] [US3] Unit test for get_execution tool (denied — no role) in `tests/test_tools/test_get_execution.py`: verify `INSUFFICIENT_PERMISSION` error
- [ ] T043 [P] [US3] Unit test for get_execution tool (execution not found) in `tests/test_tools/test_get_execution.py`: mock Kestra API 404, verify `NOT_FOUND` error
- [ ] T044 [P] [US3] Unit test for Kestra client write methods in `tests/test_client/test_kestra_client.py`: test `create_or_update_flow()` valid YAML and server error, `execute_flow()` with/without inputs, `get_execution()` success and 404

### Implementation for User Story 3

- [ ] T045 [P] [US3] Implement `create_or_update_flow` MCP tool in `src/tools/create_or_update.py`: `@server.tool()` decorator, checks `kestra.flow.write` role, validates source is non-empty and parsable YAML, calls `KestraClient.create_or_update_flow(source)`, returns flow object per contract `contracts/create_or_update_flow.json`
- [ ] T046 [P] [US3] Implement `execute_flow` MCP tool in `src/tools/execute_flow.py`: `@server.tool()` decorator, checks `kestra.flow.execute` role, validates namespace and flow_id, calls `KestraClient.execute_flow(namespace, flow_id, inputs)`, returns execution object per contract `contracts/execute_flow.json`
- [ ] T047 [P] [US3] Implement `get_execution` MCP tool in `src/tools/get_execution.py`: `@server.tool()` decorator, checks `kestra.flow.read` role, validates execution_id, calls `KestraClient.get_execution(execution_id)`, returns full execution record per contract `contracts/get_execution.json`
- [ ] T048 [US3] Register create_or_update_flow, execute_flow, and get_execution tools in `src/server.py`'s `create_server()` factory

**Checkpoint**: All 6 MCP tools functional — users can check auth status, browse flows, inspect flows, create/update flows, execute flows, and check execution results, all permission-gated

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Integration testing, transport validation, security hardening, and documentation

- [ ] T049 [P] Integration test for full MCP server in `tests/test_integration/test_mcp_server.py`: start server with stdio transport, test full MVP journey (auth_status → list_flows → get_flow → create_or_update → execute_flow → get_execution), verify tool visibility updates with permission changes
- [ ] T050 [P] Integration test for upstream Kestra API errors in `tests/test_integration/test_mcp_server.py`: mock Kestra API returning 503, verify MCP error response maps status code and sanitizes message (no stack traces)
- [ ] T051 [P] Integration test for token expiry and silent refresh in `tests/test_integration/test_mcp_server.py`: use expired token fixture, verify tool call triggers silent refresh and succeeds, verify truly expired (no refresh token) returns `UNAUTHENTICATED`
- [ ] T052 [P] Integration test for permission changes mid-session in `tests/test_integration/test_mcp_server.py`: authenticate with `kestra.flow.read`, verify list_flows works, simulate role removal, verify next list_flows call returns `INSUFFICIENT_PERMISSION` (per-request validation)
- [ ] T053 Verify stdio transport fallback in `src/server.py`: ensure `KESTRA_MCP_TRANSPORT=stdio` starts stdio server with identical tool set and auth chain
- [ ] T054 Validate constitution gate: define and document permission matrix (tool name, required roles, denied behavior, failure mode) in `specs/001-kestra-mcp-oauth/permission-matrix.md`
- [ ] T055 Validate constitution gate: verify all 6 tools enforce deny-by-default (no tool operates without explicit role check)
- [ ] T056 Validate constitution gate: confirm no secrets logged, echoed, or persisted in plain text anywhere in the codebase
- [ ] T057 Run full test suite with `uv run pytest -v` and verify all tests pass
- [ ] T058 Run `uv run ruff check src/ tests/` and fix any linting issues
- [ ] T059 Validate quickstart.md instructions: follow the quickstart steps end-to-end on a clean checkout
- [ ] T060 Run `uv run pytest --cov=src --cov-report=term-missing` and verify test coverage meets reasonable threshold

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — P1, core auth flow
- **User Story 2 (Phase 4)**: Depends on Foundational — P2, depends on KestraClient and permission infrastructure from Phase 2; independent of US1 completion
- **User Story 3 (Phase 5)**: Depends on Foundational — P3, depends on KestraClient; independent of US1 and US2 completion
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational — No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational — Independent of US1 (uses shared auth/KestraClient from Phase 2)
- **User Story 3 (P3)**: Can start after Foundational — Independent of US1/US2 (uses shared auth/KestraClient from Phase 2)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Tool implementation after tests
- Server registration after tool implementation
- Story complete before moving to next priority (sequential) or all three can proceed in parallel after Foundational

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002, T003, T004, T005)
- All Foundational tasks marked [P] can run in parallel: T008, T009, T013, T014
- Once Foundational completes, all three user stories can start in parallel
- Within US1: all 5 test tasks (T015-T019) can run in parallel; T020 can run in parallel with T021
- Within US2: all 7 test tasks (T023-T029) can run in parallel; T030 and T031 can run in parallel
- Within US3: all 12 test tasks (T033-T044) can run in parallel; T045, T046, T047 can run in parallel
- Polish: all integration tests (T049-T052) can run in parallel on completion of all user stories

---

## Parallel Example: User Story 2

```bash
# Launch all US2 tests together (tests written first, expected to fail):
Task: "Unit test for list_flows tool (authorized) in tests/test_tools/test_list_flows.py"
Task: "Unit test for list_flows tool (denied - no role) in tests/test_tools/test_list_flows.py"
Task: "Unit test for list_flows tool (denied - unauthenticated) in tests/test_tools/test_list_flows.py"
Task: "Unit test for get_flow tool (authorized) in tests/test_tools/test_get_flow.py"
Task: "Unit test for get_flow tool (not found) in tests/test_tools/test_get_flow.py"
Task: "Unit test for get_flow tool (denied - no role) in tests/test_tools/test_get_flow.py"
Task: "Unit test for Kestra API client methods in tests/test_client/test_kestra_client.py"

# Then launch both tool implementations in parallel:
Task: "Implement list_flows MCP tool in src/tools/list_flows.py"
Task: "Implement get_flow MCP tool in src/tools/get_flow.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 2: Foundational (T007-T014)
3. Complete Phase 3: User Story 1 (T015-T022)
4. **STOP and VALIDATE**: Start server, call `auth_status` with and without auth
5. Deploy/demo — MCP server provides auth awareness

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (auth, client, server skeleton)
2. Add User Story 1 → `auth_status` works → **MVP: users can verify access**
3. Add User Story 2 → `list_flows` + `get_flow` work → **Read-only flow browsing**
4. Add User Story 3 → `create_or_update_flow` + `execute_flow` + `get_execution` work → **Full MVP**
5. Complete Phase 6 → Integration tests, security audit, polished delivery

### Parallel Team Strategy

With multiple developers on a single phase:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (auth_status) — 8 tasks
   - Developer B: User Story 2 (read flows) — 10 tasks
   - Developer C: User Story 3 (write+execute) — 16 tasks
3. All three stories integrate independently into shared server factory

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests are written FIRST and expected to fail before tool implementation
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All 6 MCP tools follow the same pattern: check session → validate roles → call KestraClient → return mapped response
- Error codes per spec: UNAUTHENTICATED, INSUFFICIENT_PERMISSION, NOT_FOUND, INVALID_YAML, UPSTREAM_ERROR
