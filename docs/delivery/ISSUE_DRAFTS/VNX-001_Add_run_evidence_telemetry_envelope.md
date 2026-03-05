# VNX-001 — Add run/evidence telemetry envelope

## Metadata

- Type: feature
- Priority: P0
- Estimate: M
- Epic: E0 (Baseline instrumentation and guardrails)
- Phase: 0
- Dependencies: none
- Labels: `epic`, `phase-0`, `telemetry`, `backward-compatible`

## Summary

Add a uniform telemetry envelope to all MCP tool responses so every execution can be traced across runs and future control-loop components.

## Problem Statement

Current responses are useful but not uniformly correlated across tool calls. vNext planning/safety components require consistent run-level and step-level traceability.

## Goals

1. Add correlation metadata to every tool response.
2. Preserve current response payload semantics (no breaking changes).
3. Make telemetry opt-in/out via config flag (default on).

## Scope

- Add telemetry envelope fields to all tool outputs:
  - `run_id`
  - `step_id`
  - `timestamp`
  - `tool_name`
  - `duration_ms`
  - `status` (`ok`/`error`)
- Centralize envelope assembly in one helper module.
- Ensure error responses also include correlation fields.

## Out of Scope

- External metrics backend integration.
- Distributed tracing/export (OpenTelemetry, etc.).
- Planner/belief graph logic.

## Acceptance Criteria

- [ ] Every existing tool response includes telemetry envelope fields.
- [ ] Existing top-level payload keys are preserved and remain parse-compatible.
- [ ] Envelope can be disabled via config flag; default behavior is enabled.
- [ ] Error responses include the same correlation metadata fields.
- [ ] Unit tests cover success and error envelope generation.

## Implementation Notes

- Create `netmcp/telemetry.py`:
  - `start_span(tool_name) -> context`
  - `finish_span(context, status, payload) -> dict`
- Update `netmcp/server.py` tool handlers to call telemetry helper.
- Add config toggle in `netmcp/config.py`.

## Test Plan

- Unit tests:
  - envelope present on success
  - envelope present on error
  - toggle disables envelope
- Smoke test:
  - call `net_vendors`, verify envelope fields and original payload coexist.

## Risks

- Risk: consumers may rely on exact response shape.
  - Mitigation: only additive fields; no field renames/removals.
- Risk: inconsistent wrapping across tools.
  - Mitigation: single helper used by all handlers.

## Rollback Plan

- Revert `telemetry.py` integration in tool handlers.
- Disable envelope by config flag if partial rollback needed.

## Definition of Done

- [ ] Acceptance criteria complete
- [ ] Tests pass locally
- [ ] `README.md` updated with envelope schema section
- [ ] Linked to [IMPLEMENTATION_BACKLOG.md](../IMPLEMENTATION_BACKLOG.md)
