# VNX-050 — Implement safety supervisor core

## Metadata

- Type: safety-critical
- Priority: P0
- Estimate: L
- Epic: E5 (Safety supervisor + kill-switch control)
- Phase: 0-3
- Dependencies: VNX-002
- Labels: `epic`, `safety-critical`, `phase-0`, `phase-1`, `phase-2`, `phase-3`

## Summary

Implement a central safety supervisor that evaluates and enforces policy constraints before planner-driven actions execute.

## Problem Statement

vNext introduces stateful planning and closed-loop behavior. Without a hard policy gate, failure propagation can cause probe storms, budget overruns, and unsafe automation drift.

## Goals

1. Enforce allow/deny policy for every planner-suggested action.
2. Guarantee fail-closed behavior when policy evaluation is uncertain.
3. Provide machine-readable safety decisions for auditability.

## Scope

- Add `netmcp/safety.py` with:
  - policy evaluation engine
  - budget/rate-limit checks
  - allow/deny decision object
  - fail-closed fallback path
- Integrate supervisor hook into planner and step-execution path.
- Expose supervisor decision trace in status outputs.
- Prepare extension points for kill-switch triggers (VNX-051).

## Out of Scope

- Full kill-switch threshold engine (VNX-051).
- Counterfactual twin preflight (VNX-052).

## Acceptance Criteria

- [ ] Every planner-driven action passes through supervisor evaluation.
- [ ] Policy evaluation errors force deny (fail-closed).
- [ ] Decision object includes: `decision`, `reasons[]`, `policy_version`, `budget_state`.
- [ ] Supervisor emits audit log entries with run/step correlation.
- [ ] Unit tests cover allow, deny, and fail-closed scenarios.

## Implementation Notes

- Decision contract (suggested):
  ```json
  {
    "decision": "allow|deny",
    "reasons": ["..."],
    "policy_version": "v1",
    "risk_score": 0.0,
    "budget_remaining": { "risk": 0.0, "probe": 0 },
    "timestamp": "..."
  }
  ```
- Keep supervisor pure and deterministic where possible.
- Make policy source pluggable (static file/config to start).

## Test Plan

- Unit tests:
  - allow path under budget and policy match
  - deny path on budget exceeded
  - fail-closed on evaluator exception
- Integration test:
  - planner recommendation denied by supervisor, step not executed

## Risks

- Risk: overly strict defaults block useful actions.
  - Mitigation: explicit policy profiles (`strict`, `balanced`, `observe-only`).
- Risk: non-deterministic policy behavior.
  - Mitigation: deterministic evaluator + versioned policy artifacts.

## Rollback Plan

- Run in `observe-only` mode if enforcement causes disruption.
- Revert execution hard-block while retaining decision logs for diagnostics.

## Definition of Done

- [ ] Acceptance criteria complete
- [ ] Tests pass locally
- [ ] Safety decision schema documented in `README.md`
- [ ] Linked to [IMPLEMENTATION_BACKLOG.md](../IMPLEMENTATION_BACKLOG.md)
