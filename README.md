# netmcp

**Multi-vendor network engineering MCP server for Claude.**

`netmcp` removes the tedious execution layer so you can focus on the decisions that actually require your expertise.

Built by and for network engineers.

Technical docs and delivery artifacts are organized under `docs/`:

- [Docs Hub](docs/DOCS_HUB.md)

---

## What it does

Connect Claude to your network devices over SSH. Get structured, parsed output — not walls of CLI text. Run multi-device workflows, capture state snapshots, and let Claude reason over real network data.

```
Claude → netmcp → Netmiko SSH → Your devices
                ↓
         ntc-templates parsing
                ↓
         Structured JSON output
```

---

## Supported vendors

| Vendor key       | Platform                       |
| ---------------- | ------------------------------ |
| `cisco_ios`      | Cisco IOS (routers, switches)  |
| `cisco_nxos`     | Cisco NX-OS (Nexus)            |
| `cisco_asa`      | Cisco ASA (firewall)           |
| `cisco_ftd`      | Cisco Firepower Threat Defense |
| `cisco_xr`       | Cisco IOS-XR                   |
| `f5_tmsh`        | F5 BIG-IP (TMSH)               |
| `checkpoint`     | Check Point (CLISH/Expert)     |
| `juniper_junos`  | Juniper JunOS                  |
| `arista_eos`     | Arista EOS                     |
| `paloalto_panos` | Palo Alto PAN-OS               |

---

## Tools

| Tool                | What it does                                                  |
| ------------------- | ------------------------------------------------------------- |
| `net_show`          | Execute any show command, parse output via ntc-templates      |
| `net_show_multi`    | Run multiple commands in a single SSH session                 |
| `net_inventory`     | Full state snapshot — version, interfaces, routing, neighbors |
| `net_ping`          | Ping FROM a device (source interface, VRF support)            |
| `net_config_backup` | Capture running/startup config with metadata header           |
| `net_vendors`       | List supported vendors and server info                        |

---

## Install

```bash
# Clone
git clone https://github.com/0xFATPKT/netmcp
cd netmcp

# Install
pip install -e .

# Or install dependencies directly
pip install mcp netmiko ntc-templates pydantic
```

---

## Claude Desktop config

Add to `%APPDATA%\Claude\claude_desktop_config.json` (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

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

Or if installed via pip:

```json
{
  "mcpServers": {
    "netmcp": {
      "command": "netmcp"
    }
  }
}
```

Restart Claude Desktop after updating the config.

---

## Vendor command overrides (optional)

You can override built-in inventory/ping/config commands without editing code.

- Option 1: create `netmcp.commands.json` in the server working directory
- Option 2: set `NETMCP_COMMAND_OVERRIDES` to an absolute path

Example:

```json
{
  "inventory": {
    "cisco_ios": {
      "neighbors": "show lldp neighbors detail"
    },
    "paloalto_panos": {
      "routing": "show routing route virtual-router default"
    }
  },
  "ping": {
    "checkpoint": "ping -c {count} {target}"
  },
  "config": {
    "juniper_junos": {
      "running": "show configuration | display set"
    }
  }
}
```

Supported keys:

- `inventory`: vendor -> `{ version | interfaces | routing | neighbors }`
- `ping`: vendor -> command template string
- `config`: vendor -> `{ running | startup }`

Invalid keys are ignored with a startup warning in logs.

---

## Example prompts

```
Show me the routing table on 10.0.0.1 (cisco_ios, admin/password)

Run a full inventory snapshot on the core switch at 192.168.1.1

Ping 8.8.8.8 from core-rtr-01 using the Loopback0 interface

Back up the running config from the ASA at 10.1.1.254

What interfaces are down on 172.16.0.1?
```

---

## Why structured output matters

Raw `show ip route` output is 200 lines. Parsed output is a JSON array Claude can actually reason over — filter by protocol, find specific prefixes, identify missing routes, compare before/after a change.

```json
[
  {
    "protocol": "O",
    "network": "10.0.0.0",
    "mask": "8",
    "nexthop_ip": "192.168.1.1",
    "nexthop_if": "GigabitEthernet0/1",
    "metric": "110/20"
  }
]
```

ntc-templates handles the parsing. You get the analysis.

---

## Security notes

- Credentials are passed per-request — netmcp does not store them
- All tools are read-only in v0.1 — no config push, no write operations
- SSH only — no SNMP, no REST (yet)
- Enable secret supported for Cisco privileged exec

Config push tools (with confirmation gates) are on the roadmap.

---

## Roadmap

- [ ] Config push with diff preview and confirmation
- [ ] Multi-device parallel execution
- [ ] NAPALM integration for vendor-agnostic ops
- [ ] RESTCONF/NETCONF support
- [ ] Device inventory YAML/CSV import
- [ ] Baseline compare (before/after change)
- [ ] BGP neighbor state monitoring
- [ ] Interface utilization trending

---

## Author

**0xFATPKT** — Division Network Engineer, 14+ years enterprise infrastructure.
Cisco, F5, Firepower, Check Point. Now also AI/automation.

GitHub: [@0xFATPKT](https://github.com/0xFATPKT)

---

## License

MIT
