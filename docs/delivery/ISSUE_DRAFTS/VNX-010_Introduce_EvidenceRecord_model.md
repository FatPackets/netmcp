# VNX-010 — Introduce EvidenceRecord model

## Metadata

- Type: feature
- Priority: P0
- Estimate: M
- Epic: E1 (Evidence and confidence pipeline)
- Phase: 0-1
- Dependencies: VNX-001
- Labels: `epic`, `phase-0`, `schema-change`, `backward-compatible`

## Summary

Create a canonical `EvidenceRecord` data contract to capture normalized execution evidence from every command path.

## Problem Statement

Evidence is currently embedded in per-tool responses with inconsistent shape. Closed-loop control and confidence logic require a stable, versioned evidence schema.

## Goals

1. Define one schema for command evidence across all tools.
2. Include parser/confidence-ready fields for downstream components.
3. Version the schema for migration safety.

## Scope

- Add `EvidenceRecord` model in `netmcp/models.py` with fields:
  - `schema_version`
  - `run_id`
  - `step_id`
  - `tool_name`
  - `host`
  - `vendor`
  - `command`
  - `raw_hash`
  - `raw_output` (or reference)
  - `parsed_output`
  - `parse_confidence`
  - `timestamp`
  - `status`
  - `error_type` (optional)
  - `error_message` (optional)
- Integrate model generation into command execution paths.
- Preserve existing response payloads while adding normalized record path.

## Out of Scope

- Persistent storage engine implementation (handled in VNX-012).
- Planning or belief graph updates.

## Acceptance Criteria

- [ ] `EvidenceRecord` model exists with explicit schema versioning.
- [ ] At least `net_show` and `net_inventory` produce valid `EvidenceRecord` objects.
- [ ] Invalid records fail validation deterministically with clear errors.
- [ ] Existing response formats remain backward compatible.
- [ ] Unit tests cover record creation for success/error paths.

## Implementation Notes

- Use Pydantic model with strict field typing.
- Use deterministic hashing for `raw_hash` (e.g., SHA-256).
- Keep `raw_output` optional if size exceeds threshold (reference pointer allowed).

## Test Plan

- Unit tests:
  - valid record construction
  - missing required fields rejected
  - schema version included
  - error path record shape
- Contract test:
  - serialize/deserialize without field loss.

## Risks

- Risk: oversized evidence payloads.
  - Mitigation: optional raw payload truncation/reference strategy.
- Risk: downstream coupling to early schema.
  - Mitigation: explicit `schema_version` and changelog discipline.

## Rollback Plan

- Keep model additive; if needed, disable emission path and continue current outputs.
- Revert integration points in handlers without changing user-facing APIs.

## Definition of Done

- [ ] Acceptance criteria complete
- [ ] Tests pass locally
- [ ] Model documented in [VNEXT_BREAKTHROUGH_BLUEPRINT.md](../../strategy/VNEXT_BREAKTHROUGH_BLUEPRINT.md)
- [ ] Linked to [IMPLEMENTATION_BACKLOG.md](../IMPLEMENTATION_BACKLOG.md)
