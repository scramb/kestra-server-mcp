<!--
Sync Impact Report
- Version change: 0.0.0-template -> 1.0.0
- Modified principles:
  - Template Principle 1 -> I. Kestra API as MCP Source of Truth
  - Template Principle 2 -> II. Security First by Design
  - Template Principle 3 -> III. OAuth 2.1 + Microsoft Entra Required
  - Template Principle 4 -> IV. Deny-by-Default Authorization and Permission-Scoped Tools
  - Template Principle 5 -> V. HTTPS Primary, uv Fallback Only
- Added sections:
  - Security & Access Constraints
  - Development & Review Workflow
- Removed sections:
  - None
- Templates requiring updates:
  - ✅ .specify/templates/plan-template.md
  - ✅ .specify/templates/spec-template.md
  - ✅ .specify/templates/tasks-template.md
  - ⚠ pending .specify/templates/commands/*.md (directory not present in repository)
  - ⚠ pending README.md and docs/quickstart.md (files not present in repository)
- Follow-up TODOs:
  - None
-->

# Kestra Server MCP Constitution

## Core Principles

### I. Kestra API as MCP Source of Truth

This project MUST implement MCP tools against the Kestra API and not against
documentation scraping workflows. New MCP capabilities MUST map to explicit API
operations, request/response contracts, and stable error handling semantics.

Rationale: API-grounded behavior is testable, versionable, and operationally
reliable in production.

### II. Security First by Design

Security constraints are non-negotiable and MUST be designed before feature
expansion. Every tool-facing change MUST define trust boundaries, input
validation, secret handling, and failure behavior under attack assumptions.

Rationale: Security controls are most effective when designed up front rather
than retrofitted after feature delivery.

### III. OAuth 2.1 + Microsoft Entra Required

Authentication MUST use OAuth 2.1 patterns integrated with Microsoft Entra.
Any alternative identity flow requires explicit constitutional amendment.
Token acquisition, refresh, and scope usage MUST be documented in plan and
tested in implementation.

Rationale: A single standardized identity model reduces auth drift and
misconfiguration risk across tools.

### IV. Deny-by-Default Authorization and Permission-Scoped Tools

Authorization MUST fail closed. Every MCP tool MUST require explicit
permission scope mapping and MUST refuse execution when required permissions
are missing, ambiguous, or unverifiable.

Rationale: Deny-by-default minimizes blast radius and prevents accidental
privilege escalation.

### V. HTTPS Primary, uv Fallback Only

All network communication MUST use HTTPS by default. uv-based fallback paths
MAY be used only when HTTPS-primary flow is unavailable, and fallback behavior
MUST preserve equivalent auth and authorization guarantees.

Rationale: Transport guarantees are core to confidentiality and integrity;
fallbacks are acceptable only when they do not weaken security posture.

## Security & Access Constraints

- Tool design MUST produce a permission matrix: tool name, required scopes,
  denied scopes, and expected failure mode.
- Secrets MUST never be logged, echoed, or persisted in plain text artifacts.
- Plans and specs MUST include explicit handling for token expiration,
  insufficient scope, and tenant boundary errors.
- Any proposal that broadens default permissions is blocked until reviewed.

## Development & Review Workflow

- `/speckit-plan` outputs MUST pass Constitution Check gates before research
  is considered complete.
- `/speckit-specify` outputs MUST include security and access requirements,
  including OAuth 2.1 + Entra and deny-by-default behavior.
- `/speckit-tasks` outputs MUST include tasks for permission checks,
  transport enforcement, and negative-path security tests.
- Reviews MUST reject changes that introduce undocumented auth flows,
  implicit permissions, or non-HTTPS primary transport behavior.

## Governance

This constitution overrides conflicting local workflow preferences and template
defaults. Amendments require: (1) a documented rationale, (2) explicit impact
analysis across templates, and (3) semantic version updates in this file.

Versioning policy:
- MAJOR: Breaking governance changes, principle removals, or redefinitions.
- MINOR: New principle or materially expanded mandatory guidance.
- PATCH: Clarifications, editorial improvements, and non-semantic refinements.

Compliance review policy:
- Every plan, spec, and task artifact MUST include a constitution compliance
  check before implementation begins.
- Non-compliance MUST be tracked and resolved before merge.

**Version**: 1.0.0 | **Ratified**: 2026-05-29 | **Last Amended**: 2026-05-29
