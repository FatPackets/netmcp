# netmcp Presentation Mode Deck

A single scrollable deck that stitches architecture, remediation, troubleshooting, and operations into one page.

Source docs:

- [TECHNICAL_OVERVIEW.md](../strategy/TECHNICAL_OVERVIEW.md)
- [TECHNICAL_VISUAL_MAP.md](TECHNICAL_VISUAL_MAP.md)
- [EXEC_SUMMARY_VISUAL.md](EXEC_SUMMARY_VISUAL.md)
- [TROUBLESHOOTING_FLOW.md](../ops/TROUBLESHOOTING_FLOW.md)
- [OPERATIONS_RUNBOOK.md](../ops/OPERATIONS_RUNBOOK.md)

---

## Slide 1 — Mission and Scope

**What this is**

- Read-only MCP server for network operations over SSH.
- Converts CLI output into structured data when parser coverage exists.
- Supports multi-vendor workflows with command-map defaults and runtime overrides.

**Current posture**

- Startup and packaging issues remediated.
- Explicit command coverage expanded for all advertised vendors.
- Operator override mechanism added (`NETMCP_COMMAND_OVERRIDES` or local JSON file).

---

## Slide 2 — End-to-End Architecture

```mermaid
flowchart LR
    Client["MCP Client\n(Claude Desktop)"] --> Tool["netmcp tool call"]
    Tool --> Validate["Pydantic validation\n(input models)"]
    Validate --> SSH["Netmiko ConnectHandler\nSSH session"]
    SSH --> Device["Network device CLI"]
    Device --> Output["Raw command output"]
    Output --> Parse{"parse enabled\nand template available?"}
    Parse -->|Yes| Structured["ntc-templates\nstructured records"]
    Parse -->|No| Raw["raw fallback"]
    Structured --> Format["JSON / markdown / raw"]
    Raw --> Format
    Format --> Client

    Maps["Inventory/Ping/Config maps"] --> Tool
    Overrides["JSON/env overrides"] --> Maps
```

---

## Slide 3 — Request Lifecycle (Sequence)

```mermaid
sequenceDiagram
    autonumber
    participant C as MCP Client
    participant S as netmcp.server
    participant N as Netmiko
    participant D as Device
    participant T as ntc-templates

    C->>S: Invoke tool(params)
    S->>S: Validate input model
    S->>N: ConnectHandler(**conn_params)
    N->>D: Execute command(s)
    D-->>N: CLI output

    alt Template exists and parse requested
        N->>T: parse_output(platform, command, data)
        T-->>S: Structured list[dict]
    else Parse disabled or no template
        N-->>S: Raw text
    end

    S->>S: Build response envelope + timestamp
    S-->>C: Return JSON/markdown/raw
```

---

## Slide 4 — Tool Surface Area

| Tool                | Primary Job                                           | Notes                            |
| ------------------- | ----------------------------------------------------- | -------------------------------- |
| `net_show`          | Single command execution                              | Optional parse via ntc-templates |
| `net_show_multi`    | Multi-command in one SSH session                      | More efficient for bundles       |
| `net_inventory`     | State snapshot (version/interfaces/routing/neighbors) | Uses vendor map                  |
| `net_ping`          | On-device ping test                                   | Supports source/VRF fields       |
| `net_config_backup` | Running/startup capture                               | Adds metadata header             |
| `net_vendors`       | Capability metadata                                   | Includes override status         |

---

## Slide 5 — What Was Broken Before

- Syntax corruption blocked clean startup in `server.py`.
- Packaging metadata expected `src/` layout while repo is flat package layout.
- Script entrypoint was brittle.
- README launch path pointed to incorrect `cwd`.
- Advertised vendor list exceeded explicit command-map coverage.
- No runtime-safe override mechanism for command tuning.

---

## Slide 6 — What Was Fixed

- Repaired startup parse/runtime blockers in server initialization path.
- Updated `pyproject.toml` package target to `netmcp` (flat layout).
- Updated script entrypoint to explicit callable (`netmcp.server:main`).
- Corrected README `cwd` example to repo root.
- Expanded explicit command maps for:
  - `cisco_ftd`
  - `cisco_xr`
  - `checkpoint`
  - `paloalto_panos`
- Added validated override loader and merge logic with status reporting.

---

## Slide 7 — Override Precedence and Behavior

```mermaid
flowchart TD
    Start["Module import"] --> Env{"NETMCP_COMMAND_OVERRIDES set?"}
    Env -->|Yes| UseEnv["Use env file path"]
    Env -->|No| Local{"./netmcp.commands.json exists?"}
    Local -->|Yes| UseLocal["Use local file"]
    Local -->|No| None["No overrides"]

    UseEnv --> Load["Read + JSON decode"]
    UseLocal --> Load

    Load --> Valid{"Top-level object valid?"}
    Valid -->|No| Err["Set status.error"]
    Valid -->|Yes| Merge["Merge inventory/ping/config\nwith key validation"]

    Merge --> Status["COMMAND_OVERRIDE_STATUS\n{loaded, source, applied, error}"]
    None --> Status
    Err --> Status

    Status --> Vendors["Exposed via net_vendors"]
```

---

## Slide 8 — Troubleshooting Decision Flow

```mermaid
flowchart TD
    S["Failure or unexpected output"] --> E{"Error class"}
    E -->|Authentication failed| A["Check username/password/secret/AAA"]
    E -->|Connection timed out| T["Check reachability, SSH, ACL, timeout"]
    E -->|Connection refused| R["Confirm SSH service + port"]
    E -->|No explicit error| O{"Output issue"}

    O -->|parsed=false| P["Parser miss: inspect raw output, adjust command/override"]
    O -->|wrong command behavior| M["Map mismatch: apply vendor override"]
    O -->|looks right| N["No action"]

    A --> End["Re-run call"]
    T --> End
    R --> End
    P --> End
    M --> End
```

---

## Slide 9 — Operations Cadence

**Day 1 (bring-up)**

1. Install and register MCP server.
2. Run compile/import/package checks.
3. Validate `net_vendors`, then one known-good `net_show`.
4. Optionally add `netmcp.commands.json`.

**Day 2 (steady state)**

1. Daily health checks (`py_compile`, import, override status).
2. Weekly parser/command drift checks across vendor OS versions.
3. Controlled updates of dependencies and command overrides.
4. Capture evidence bundle on incidents (vendor, command, raw output, error payload, override status).

---

## Slide 10 — Current Gaps and Next Moves

**Gaps**

- No automated tests in repo yet.
- No CI pipeline in this snapshot.
- Ping success detection is heuristic.
- No secrets-provider integration yet.

**Next moves**

1. Add `netmcp.commands.example.json`.
2. Add minimal unit tests (override merge/map resolution/import smoke).
3. Add CI smoke checks (build + import + package).
4. Add short deployment profiles doc (local desktop vs hosted MCP runtime).

---

## Appendix — Presenter Notes

- Emphasize read-only safety model first.
- Show override layer as the key operational flexibility feature.
- Position parser misses as expected edge-cases, not failures.
- Close with test/CI and evidence-capture improvements as next maturity step.
