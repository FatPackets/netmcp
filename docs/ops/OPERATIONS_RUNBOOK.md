# netmcp Operations Runbook (Day 1 / Day 2)

This runbook is for practical operation of `netmcp` in local or team environments.

- Docs index: [DOCS_HUB.md](../DOCS_HUB.md)
- Technical overview: [TECHNICAL_OVERVIEW.md](../strategy/TECHNICAL_OVERVIEW.md)
- Visual architecture: [TECHNICAL_VISUAL_MAP.md](../visuals/TECHNICAL_VISUAL_MAP.md)
- Troubleshooting: [TROUBLESHOOTING_FLOW.md](TROUBLESHOOTING_FLOW.md)

---

## Day 1: Setup and bring-up

### 1) Prerequisites

- Python 3.10+
- SSH reachability from host running `netmcp` to target devices
- Device credentials (and `secret` where needed)

### 2) Install

```bash
git clone https://github.com/0xFATPKT/netmcp
cd netmcp
python -m pip install -e .
```

### 3) Claude Desktop MCP registration

Add to Claude config:

```json
{
  "mcpServers": {
    "netmcp": {
      "command": "python",
      "args": ["-m", "netmcp.server"],
      "cwd": "C:\\path\\to\\netmcp"
    }
  }
}
```

Alternative (editable/pip-installed command):

```json
{
  "mcpServers": {
    "netmcp": {
      "command": "netmcp"
    }
  }
}
```

### 4) Baseline validation

```bash
python -m py_compile netmcp/server.py
python -c "import netmcp.server as s; print(s.VERSION, s.SERVER_NAME, len(s.SUPPORTED_VENDORS))"
python -m pip install -e . --no-deps
```

### 5) Optional command overrides

Create `netmcp.commands.json` in repo root (or set `NETMCP_COMMAND_OVERRIDES`).

Minimal example:

```json
{
  "inventory": {
    "cisco_ios": {
      "neighbors": "show lldp neighbors detail"
    }
  },
  "config": {
    "juniper_junos": {
      "running": "show configuration | display set"
    }
  }
}
```

### 6) First functional checks (from MCP client)

- `net_vendors` → confirm server metadata and override status
- `net_show` with `show version` on a known reachable device
- `net_inventory` on a lab device to validate section captures

---

## Day 2: Ongoing operations

### A) Routine health checks

Run daily/when changing environment:

```bash
python -m py_compile netmcp/server.py
python -c "import netmcp.server as s; print(s.COMMAND_OVERRIDE_STATUS)"
```

Operational checks:

- At least one successful `net_show` per major vendor family in your estate
- Spot-check `parsed=true` on commonly used commands

### B) Override lifecycle management

1. Edit override file
2. Validate JSON syntax
3. Restart MCP host process/client
4. Confirm with `net_vendors` (`command_overrides.loaded/applied`)
5. Run targeted tool call to verify behavior

### C) Recommended weekly checks

- Confirm no drift in command syntax for device OS upgrades
- Re-validate parser coverage for high-value commands
- Keep dependency versions current (in controlled windows)

### D) Incident response pattern

When failures occur:

1. Classify error: auth / timeout / refused / parser miss / map mismatch
2. Follow [TROUBLESHOOTING_FLOW.md](TROUBLESHOOTING_FLOW.md)
3. Capture evidence bundle:
   - vendor key
   - command string
   - raw output (`parse=false`)
   - error payload
   - `COMMAND_OVERRIDE_STATUS`

---

## Operational guardrails

- Treat all credentials as sensitive; do not commit credentials to repo files.
- Prefer narrow command overrides over broad vendor rewrites.
- Keep runbook and override examples in version control.
- Use lab validation before production rollout for new vendor commands.

---

## Suggested SOP add-ons

- Add a `netmcp.commands.example.json` tracked in git
- Add CI smoke job:
  - compile check
  - import check
  - packaging check
- Add minimal unit tests around override merge behavior
