# netmcp vNext Implementation Backlog (Commit-Ready)

Date: 2026-03-05
Source architecture: [VNEXT_BREAKTHROUGH_BLUEPRINT.md](../strategy/VNEXT_BREAKTHROUGH_BLUEPRINT.md)
Docs index: [DOCS_HUB.md](../DOCS_HUB.md)

---

## 1) Backlog intent

This backlog operationalizes the vNext blueprint into implementable, mergeable work units.

Primary objective:

- Evolve `netmcp` from stateless command execution into a confidence-gated closed-loop control system.

Execution constraints:

- Preserve backward compatibility for existing MCP tools.
- Introduce new behavior in reversible phases with kill-switch protection.
- Keep each issue independently testable.

---

## 2) Delivery model

## Branching + merge

- Branch naming: `feat/vnx-<id>-<slug>`
- Commit prefix: `VNX-<id>:`
- Merge policy: squash merge with linked issue ID

## Labels

- `epic`, `phase-0`, `phase-1`, `phase-2`, `phase-3`
- `safety-critical`, `backward-compatible`, `schema-change`, `telemetry`

## Definition of done (global)

- Acceptance criteria satisfied.
- Unit tests added/updated for changed behavior.
- No regression in baseline tools (`net_show`, `net_inventory`, etc.).
- Docs updated when user-visible behavior changes.
- Rollback path documented for schema/runtime changes.

---

## 3) Epic map

| Epic | Goal                                     | Phase | Depends on |
| ---- | ---------------------------------------- | ----- | ---------- |
| E0   | Baseline instrumentation and guardrails  | 0     | none       |
| E1   | Evidence and confidence pipeline         | 0-1   | E0         |
| E2   | Belief graph persistence + query surface | 1     | E1         |
| E3   | Advisory planning and probe ranking      | 2     | E2         |
| E4   | Closed-loop bounded execution tools      | 3     | E3 + E5    |
| E5   | Safety supervisor + kill-switch control  | 0-3   | E0         |
| E6   | Test/CI hardening and release gates      | 0-3   | all        |

---

## 4) Commit-ready issue backlog

## E0 — Baseline instrumentation and guardrails

### VNX-001 — Add run/evidence telemetry envelope

- **Type**: feature
- **Priority**: P0
- **Estimate**: M
- **Dependencies**: none
- **Acceptance criteria**:
  - Every tool response includes correlation metadata (`run_id`, `step_id`, `timestamp`).
  - Telemetry can be toggled with config flag (default on).
  - Existing response payload fields remain backward compatible.
- **Files**:
  - `netmcp/server.py`
  - `netmcp/telemetry.py` (new)

### VNX-002 — Add policy/budget config model

- **Type**: feature
- **Priority**: P0
- **Estimate**: S
- **Dependencies**: VNX-001
- **Acceptance criteria**:
  - Config supports risk budget, probe budget, and concurrency limits.
  - Invalid budget config fails fast at startup.
- **Files**:
  - `netmcp/config.py` (new)
  - `netmcp/server.py`
  - `README.md`

---

## E1 — Evidence and confidence pipeline

### VNX-010 — Introduce EvidenceRecord model

- **Type**: feature
- **Priority**: P0
- **Estimate**: M
- **Dependencies**: VNX-001
- **Acceptance criteria**:
  - Evidence record captures device/vendor/command/raw hash/parsed payload/confidence/ts.
  - Evidence schema version included for future migrations.
- **Files**:
  - `netmcp/models.py` (new)
  - `netmcp/server.py`

### VNX-011 — Implement parser confidence scoring

- **Type**: feature
- **Priority**: P0
- **Estimate**: M
- **Dependencies**: VNX-010
- **Acceptance criteria**:
  - Parser output includes confidence in [0,1].
  - Confidence degrades deterministically for fallback/raw-only results.
  - `net_vendors` reports confidence subsystem availability.
- **Files**:
  - `netmcp/parser_confidence.py` (new)
  - `netmcp/server.py`

### VNX-012 — Add append-only evidence sink

- **Type**: feature
- **Priority**: P0
- **Estimate**: M
- **Dependencies**: VNX-010
- **Acceptance criteria**:
  - Evidence can be persisted to SQLite with append-only semantics.
  - Failed evidence write does not break tool response; error is logged and counted.
- **Files**:
  - `netmcp/evidence_store.py` (new)
  - `netmcp/server.py`

---

## E2 — Belief graph persistence + query surface

### VNX-020 — Implement belief schema (nodes/edges)

- **Type**: feature
- **Priority**: P0
- **Estimate**: L
- **Dependencies**: VNX-012
- **Acceptance criteria**:
  - SQLite schema includes `belief_nodes`, `belief_edges`, and migration version table.
  - Upserts are idempotent and timestamp-aware.
- **Files**:
  - `netmcp/belief_store.py` (new)
  - `netmcp/migrations/001_belief.sql` (new)

### VNX-021 — Add confidence decay + staleness computation

- **Type**: feature
- **Priority**: P1
- **Estimate**: M
- **Dependencies**: VNX-020
- **Acceptance criteria**:
  - Staleness score updates with wall-clock age.
  - Confidence decay function configurable and deterministic.
- **Files**:
  - `netmcp/belief_math.py` (new)
  - `netmcp/belief_store.py`

### VNX-022 — Add `net_belief_snapshot` tool

- **Type**: feature
- **Priority**: P0
- **Estimate**: M
- **Dependencies**: VNX-020
- **Acceptance criteria**:
  - Returns filtered graph slice (device/vendor/entity scope).
  - Includes confidence + staleness metadata in response.
  - Read-only tool annotations set correctly.
- **Files**:
  - `netmcp/server.py`
  - `README.md`

---

## E3 — Advisory planning and probe ranking

### VNX-030 — Build information-gain scoring engine

- **Type**: feature
- **Priority**: P0
- **Estimate**: L
- **Dependencies**: VNX-021
- **Acceptance criteria**:
  - Scores candidate probes by expected information gain / (risk*cost*latency).
  - Score trace is explainable and returned for each candidate.
- **Files**:
  - `netmcp/planner.py` (new)
  - `netmcp/risk_model.py` (new)

### VNX-031 — Add `net_probe_next` advisory tool

- **Type**: feature
- **Priority**: P0
- **Estimate**: M
- **Dependencies**: VNX-030
- **Acceptance criteria**:
  - Returns top-N ranked probe actions with rationale and budget impact.
  - Does not execute commands (advisory only).
- **Files**:
  - `netmcp/server.py`
  - `README.md`

### VNX-032 — Add planner oscillation detector

- **Type**: safety
- **Priority**: P0
- **Estimate**: M
- **Dependencies**: VNX-030
- **Acceptance criteria**:
  - Repeated contradictory recommendations trigger cooldown mode.
  - Cooldown event logged and surfaced in planner status.
- **Files**:
  - `netmcp/planner.py`
  - `netmcp/safety.py` (new)

---

## E4 — Closed-loop bounded execution tools

### VNX-040 — Add `net_goal_start`

- **Type**: feature
- **Priority**: P0
- **Estimate**: M
- **Dependencies**: VNX-031 + VNX-050
- **Acceptance criteria**:
  - Initializes goal run with objectives, confidence target, budgets.
  - Returns goal ID and initial status.
- **Files**:
  - `netmcp/server.py`
  - `netmcp/goal_store.py` (new)

### VNX-041 — Add `net_goal_step` (bounded one-step loop)

- **Type**: feature
- **Priority**: P0
- **Estimate**: L
- **Dependencies**: VNX-040 + VNX-030 + VNX-051
- **Acceptance criteria**:
  - Executes exactly one plan→probe→update cycle.
  - Enforces risk/probe budget at step boundary.
  - Returns updated confidence and residual uncertainty.
- **Files**:
  - `netmcp/server.py`
  - `netmcp/loop_controller.py` (new)

### VNX-042 — Add `net_goal_status`

- **Type**: feature
- **Priority**: P1
- **Estimate**: S
- **Dependencies**: VNX-040
- **Acceptance criteria**:
  - Reports convergence, stop reason, budget utilization, oscillation flags.
- **Files**:
  - `netmcp/server.py`
  - `netmcp/goal_store.py`

---

## E5 — Safety supervisor + kill-switch

### VNX-050 — Implement safety supervisor core

- **Type**: safety-critical
- **Priority**: P0
- **Estimate**: L
- **Dependencies**: VNX-002
- **Acceptance criteria**:
  - Evaluates allow/deny for every planner-suggested action.
  - Supports fail-closed mode on policy evaluation errors.
- **Files**:
  - `netmcp/safety.py` (new)
  - `netmcp/server.py`

### VNX-051 — Implement kill-switch triggers

- **Type**: safety-critical
- **Priority**: P0
- **Estimate**: M
- **Dependencies**: VNX-050 + VNX-001
- **Acceptance criteria**:
  - Triggers on configured confidence/latency/budget/oscillation thresholds.
  - On trigger, planner-driven tools disable, read-only tools remain available.
  - Trigger reason persisted and visible in status tool.
- **Files**:
  - `netmcp/safety.py`
  - `netmcp/server.py`
  - `README.md`

### VNX-052 — Add selective counterfactual gate hook

- **Type**: feature
- **Priority**: P2
- **Estimate**: M
- **Dependencies**: VNX-050
- **Acceptance criteria**:
  - Optional preflight hook for high-risk categories.
  - If unavailable, supervisor degrades gracefully to policy-only mode.
- **Files**:
  - `netmcp/counterfactual.py` (new)
  - `netmcp/safety.py`

---

## E6 — Test/CI hardening and release gates

### VNX-060 — Add unit tests for parser confidence + evidence sink

- **Type**: test
- **Priority**: P0
- **Estimate**: M
- **Dependencies**: VNX-011 + VNX-012
- **Acceptance criteria**:
  - Coverage for confidence boundary cases and sink write failures.
- **Files**:
  - `tests/test_parser_confidence.py` (new)
  - `tests/test_evidence_store.py` (new)

### VNX-061 — Add unit tests for belief math + planner scoring

- **Type**: test
- **Priority**: P0
- **Estimate**: M
- **Dependencies**: VNX-021 + VNX-030
- **Acceptance criteria**:
  - Deterministic score outputs for fixed inputs.
  - Oscillation detector test cases included.
- **Files**:
  - `tests/test_belief_math.py` (new)
  - `tests/test_planner.py` (new)

### VNX-062 — Add smoke tests for new MCP tools

- **Type**: test
- **Priority**: P0
- **Estimate**: M
- **Dependencies**: VNX-022 + VNX-031 + VNX-040 + VNX-041 + VNX-042
- **Acceptance criteria**:
  - Tool registration checks pass.
  - Basic request/response schema checks pass.
- **Files**:
  - `tests/test_tools_smoke.py` (new)

### VNX-063 — Add CI workflow with staged gates

- **Type**: infra
- **Priority**: P1
- **Estimate**: S
- **Dependencies**: VNX-060 + VNX-061 + VNX-062
- **Acceptance criteria**:
  - Pipeline stages: lint → unit → smoke → package.
  - Merge blocked on failed tests.
- **Files**:
  - `.github/workflows/ci.yml` (new)

---

## 5) File-level change map (vNext)

| File                               | Change type                                            | Issues                                               |
| ---------------------------------- | ------------------------------------------------------ | ---------------------------------------------------- |
| `netmcp/server.py`                 | extend tools, integrate telemetry/safety/planner hooks | VNX-001, 011, 012, 022, 031, 040, 041, 042, 050, 051 |
| `netmcp/config.py`                 | new runtime config schemas                             | VNX-002                                              |
| `netmcp/models.py`                 | evidence/goal/belief contracts                         | VNX-010                                              |
| `netmcp/telemetry.py`              | correlation IDs + metrics envelope                     | VNX-001                                              |
| `netmcp/parser_confidence.py`      | parser confidence scoring                              | VNX-011                                              |
| `netmcp/evidence_store.py`         | append-only evidence persistence                       | VNX-012                                              |
| `netmcp/belief_store.py`           | belief node/edge persistence + queries                 | VNX-020, 021                                         |
| `netmcp/belief_math.py`            | confidence decay + staleness                           | VNX-021                                              |
| `netmcp/planner.py`                | candidate scoring + ranking                            | VNX-030, 032                                         |
| `netmcp/risk_model.py`             | risk/cost/latency estimators                           | VNX-030                                              |
| `netmcp/safety.py`                 | policy enforcement + kill-switch                       | VNX-032, 050, 051, 052                               |
| `netmcp/goal_store.py`             | goal run lifecycle persistence                         | VNX-040, 042                                         |
| `netmcp/loop_controller.py`        | one-step loop orchestration                            | VNX-041                                              |
| `netmcp/counterfactual.py`         | optional twin preflight hook                           | VNX-052                                              |
| `netmcp/migrations/001_belief.sql` | schema migration                                       | VNX-020                                              |
| `tests/*`                          | unit + smoke coverage                                  | VNX-060, 061, 062                                    |
| `.github/workflows/ci.yml`         | CI gates                                               | VNX-063                                              |
| `README.md`                        | tool and operations docs updates                       | VNX-002, 022, 031, 051                               |
| `VNEXT_BREAKTHROUGH_BLUEPRINT.md`  | architecture baseline reference                        | tracking                                             |

---

## 6) Milestone plan (sequenced)

## Milestone M1 (Phase 0, 1-2 weeks)

- VNX-001, 002, 010, 011, 012
- Exit criteria:
  - evidence persisted for >99% tool runs
  - no p95 latency regression >10%

## Milestone M2 (Phase 1, 2-3 weeks)

- VNX-020, 021, 022
- Exit criteria:
  - belief snapshots available for target entities
  - confidence/staleness visible and consistent

## Milestone M3 (Phase 2, 2-4 weeks)

- VNX-030, 031, 032
- Exit criteria:
  - advisory probes reduce median diagnosis time by >=25% in trial scenarios

## Milestone M4 (Phase 3, 3-5 weeks)

- VNX-040, 041, 042, 050, 051
- Exit criteria:
  - bounded closed-loop step stable
  - kill-switch tested and verified

## Milestone M5 (Hardening)

- VNX-052, 060, 061, 062, 063
- Exit criteria:
  - CI enforces quality gates
  - regression suite green

---

## 7) Risk register + mitigation hooks

| Risk                             | Impact                | Mitigation                              | Owner          |
| -------------------------------- | --------------------- | --------------------------------------- | -------------- |
| Parser confidence miscalibration | false certainty       | calibration tests + confidence floor    | planner/safety |
| Planner oscillation              | probe storms          | oscillation detector + cooldown         | planner        |
| Budget breaches                  | resource exhaustion   | hard caps + reservation buckets         | safety         |
| State drift/staleness            | wrong recommendations | decay + staleness weighting             | belief store   |
| Backward-compat breaks           | client failures       | schema versioning + compatibility tests | server         |

---

## 8) Ready-to-create issue templates (copy/paste)

## Template — Feature Issue

**Title**: `VNX-XXX <short title>`
**Labels**: `epic:<E#>`, `phase-#`, `backward-compatible`
**Summary**:
**Scope**:
**Out of scope**:
**Dependencies**:
**Acceptance criteria**:

- [ ] AC1
- [ ] AC2
- [ ] AC3
      **Files expected**:
      **Validation**:
- [ ] unit tests
- [ ] smoke tests
- [ ] docs updated

## Template — Safety-Critical Issue

**Title**: `VNX-XXX <short title>`
**Labels**: `safety-critical`, `phase-#`
**Failure mode addressed**:
**Policy constraints**:
**Acceptance criteria**:

- [ ] fail-closed behavior validated
- [ ] kill-switch interaction validated
- [ ] rollback procedure documented

---

## 9) First three issues to open immediately

1. **VNX-001** Add run/evidence telemetry envelope
2. **VNX-010** Introduce EvidenceRecord model
3. **VNX-050** Implement safety supervisor core

Reason: these three establish observability + data contract + control boundary, which all later epics depend on.
