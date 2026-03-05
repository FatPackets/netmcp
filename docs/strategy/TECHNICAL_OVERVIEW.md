# netmcp Technical Overview and Remediation Notes

Date: 2026-03-05
Scope: `c:\Users\rtseg\__PROJECTS__\netmcp`

Companion docs:

- [DOCS_HUB.md](../DOCS_HUB.md) _(primary navigation)_
- Visuals: [TECHNICAL_VISUAL_MAP.md](../visuals/TECHNICAL_VISUAL_MAP.md), [EXEC_SUMMARY_VISUAL.md](../visuals/EXEC_SUMMARY_VISUAL.md), [PRESENTATION_MODE_DECK.md](../visuals/PRESENTATION_MODE_DECK.md)
- Strategy + delivery: [VNEXT_BREAKTHROUGH_BLUEPRINT.md](VNEXT_BREAKTHROUGH_BLUEPRINT.md), [IMPLEMENTATION_BACKLOG.md](../delivery/IMPLEMENTATION_BACKLOG.md), [ISSUE_DRAFTS/README.md](../delivery/ISSUE_DRAFTS/README.md)
- Operations: [OPERATIONS_RUNBOOK.md](../ops/OPERATIONS_RUNBOOK.md), [TROUBLESHOOTING_FLOW.md](../ops/TROUBLESHOOTING_FLOW.md)

---

## 1) What this project is

`netmcp` is a Python MCP server for network engineering workflows. It acts as a bridge between an MCP client (for example, Claude Desktop) and network devices reachable over SSH.

High-level flow:

1. MCP client calls a tool.
2. `netmcp` validates inputs with Pydantic models.
3. `netmcp` opens an SSH session using Netmiko.
4. Device command output is optionally parsed with `ntc-templates`.
5. Results are returned as JSON / markdown / raw text.

The server is intentionally read-only in this version (no config push).

---

## 2) Directory map (what each item does)

- `pyproject.toml`
  - Packaging/build metadata (Hatchling)
  - Runtime and dev dependencies
  - Console script entrypoint (`netmcp`)
- `README.md`
  - Operator-facing setup, supported vendors, tool descriptions, examples
- `netmcp/server.py`
  - Entire MCP server implementation
  - Input models, command maps, tool handlers, startup lifecycle, entrypoint
- `netmcp/__init__.py`
  - Package marker

Current repo is a flat package layout (`netmcp/`), not `src/` layout.

---

## 3) Technical architecture inside `server.py`

### Core constants and capability registry

- `SUPPORTED_VENDORS`: canonical vendor keys used by inputs and command maps
- `VERSION`, `SERVER_NAME`
- Defaults such as SSH timeout/port

### Input contracts

Pydantic models enforce tool input constraints:

- `DeviceTarget`
- `ShowCommandInput`
- `MultiCommandInput`
- `DeviceInventoryInput`
- `PingTestInput`
- `ConfigBackupInput`

These models are the runtime contract for MCP tools.

### Connection and formatting helpers

- `_build_netmiko_params`: normalized Netmiko connection args
- `_attempt_parse`: ntc-templates parse attempt with safe fallback
- `_format_error`: consistent JSON error envelope
- `_format_result`: output formatter

### Vendor command maps

Three map groups define defaults by vendor:

- `INVENTORY_COMMANDS`
- `PING_COMMANDS`
- `CONFIG_COMMANDS`

These maps are read by `net_inventory`, `net_ping`, and `net_config_backup`.

### Override subsystem (new)

A runtime override layer now supports command customization without code edits.

- Environment variable: `NETMCP_COMMAND_OVERRIDES`
- Default file name in working directory: `netmcp.commands.json`
- Load/validate/merge functions:
  - `_resolve_override_file`
  - `_load_command_overrides`
  - `_apply_inventory_overrides`
  - `_apply_ping_overrides`
  - `_apply_config_overrides`
- Result state: `COMMAND_OVERRIDE_STATUS`

Override status is now visible in:

- startup logs (if an override file is used)
- `net_vendors` tool output (`command_overrides` field)

### MCP lifecycle and tools

- `app_lifespan`: startup/shutdown logging and capability status
- `mcp = FastMCP(...)`: server instance
- Registered tools:
  - `net_show`
  - `net_show_multi`
  - `net_inventory`
  - `net_ping`
  - `net_config_backup`
  - `net_vendors`
- Entrypoint:
  - `main()`
  - `if __name__ == "__main__": main()`

---

## 4) What was missing or broken before remediation

1. **Syntax corruption in server startup path**
   - A stray trailing character caused Python parse failure.
   - Impact: server could not start.

2. **Corrupted server init token (previous state)**
   - `FastMCP` constructor line had been malformed in an earlier state.
   - Impact: runtime initialization failure.

3. **Packaging/layout mismatch**
   - Wheel package path pointed to `src/netmcp` while repository uses flat `netmcp/` package.
   - Impact: unreliable package build/install behavior.

4. **Console script target was brittle**
   - Entry script referenced `netmcp.server:mcp.run` directly.
   - Impact: less robust than explicit callable wrapper.

5. **README launch path mismatch**
   - Claude config sample used `...\netmcp\src` path.
   - Impact: confusing startup/config errors for operators.

6. **Advertised-vendor vs map-coverage gap**
   - Vendor list included platforms without explicit command map entries for inventory/ping/config in earlier state.
   - Impact: fallback behavior instead of explicit per-vendor defaults.

7. **No operator-safe command override layer**
   - Command tuning required direct code edits.
   - Impact: higher risk and slower operations.

---

## 5) What was fixed

1. **Server parse/startup repaired**
   - Removed syntax corruption and restored clean startup flow.

2. **Packaging corrected**
   - `pyproject.toml` updated to flat package layout:
     - wheel packages now point to `netmcp`
   - Console script now points to explicit `main()` callable.

3. **README corrected**
   - Claude Desktop `cwd` example aligned to repo root (`...\netmcp`).

4. **Vendor command maps expanded**
   - Added explicit map entries for:
     - `cisco_ftd`
     - `cisco_xr`
     - `checkpoint`
     - `paloalto_panos`
   - Added coverage across inventory, ping, and config maps.

5. **Override subsystem implemented**
   - JSON-driven command overrides via env var or local file.
   - Validation and guarded merge semantics.
   - Status surfaced in logs and `net_vendors` output.

---

## 6) Validation performed

The following checks were run after fixes:

- `python -m py_compile netmcp/server.py`
  - Confirms syntax validity.
- `python -c "import netmcp.server as s; ..."`
  - Confirms import/startup state and vendor registry.
- `python -m pip install -e . --no-deps`
  - Confirms packaging metadata/build/install path.
- Override simulation with temporary JSON + `NETMCP_COMMAND_OVERRIDES`
  - Confirmed `COMMAND_OVERRIDE_STATUS` loads and applies entries.

---

## 7) Current state and remaining gaps

### Stable now

- Server imports and compiles.
- Tool set is intact and callable.
- Packaging and launch docs align with directory structure.
- Command overrides provide operational flexibility.

### Still missing / future hardening

- No automated test suite in this folder yet.
- No CI workflow visible in this repo snapshot.
- Ping success detection is heuristic text matching.
- No credential vault integration (credentials are request-scoped only).
- No write/change tools (intentional for current read-only scope).
- No committed sample override file yet (README has examples).

---

## 8) How to navigate this repo quickly

If you are learning this directory, inspect in this order:

1. `README.md` (operator behavior)
2. `pyproject.toml` (runtime dependencies + entrypoint)
3. `netmcp/server.py`
   - models
   - command maps
   - override loader
   - tool handlers
   - `main()`

That gives you the full control path from MCP call to SSH command execution and response shaping.

---

## 9) Recommended next actions (optional)

1. Add `netmcp.commands.example.json` to repo root.
2. Add minimal unit tests for:
   - override loader validation/merge
   - command map resolution behavior
3. Add a smoke test for tool registration and import.
4. Add a short `docs/` note for deployment patterns (local desktop vs service-hosted MCP).
