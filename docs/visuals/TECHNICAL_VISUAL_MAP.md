# netmcp Visual Technical Map

This is the visual companion to the technical write-up.

- Narrative deep dive: [TECHNICAL_OVERVIEW.md](../strategy/TECHNICAL_OVERVIEW.md)
- Code implementation: [netmcp/server.py](../../netmcp/server.py)

---

## 1) End-to-end architecture

```mermaid
flowchart LR
    Client["MCP Client\n(Claude Desktop, etc.)"] --> ToolCall["Tool Invocation\n(net_show / net_inventory / net_ping / ...) "]
    ToolCall --> Input["Pydantic Input Models\nvalidation + coercion"]
    Input --> Handler["Tool Handler\nin server.py"]
    Handler --> Session["Netmiko ConnectHandler\nSSH session"]
    Session --> Device["Network Device\nCLI command execution"]
    Device --> Raw["Raw CLI Output"]
    Raw --> Parse{"parse=True?\nand template exists?"}
    Parse -->|Yes| Structured["ntc-templates parse_output\nStructured list[dict]"]
    Parse -->|No| Fallback["Raw output fallback"]
    Structured --> Format["Response formatting\nJSON / markdown / raw"]
    Fallback --> Format
    Format --> Client
```

---

## 2) Request lifecycle (sequence)

```mermaid
sequenceDiagram
    autonumber
    participant C as MCP Client
    participant S as netmcp.server
    participant N as Netmiko
    participant D as Network Device
    participant T as ntc-templates

    C->>S: Call tool with params
    S->>S: Validate with Pydantic model
    S->>N: ConnectHandler(**conn_params)
    N->>D: SSH command execution
    D-->>N: CLI output

    alt parse enabled and template found
        N->>T: parse_output(platform, command, data)
        T-->>S: Structured parsed records
    else parse disabled or no template
        N-->>S: Raw CLI output
    end

    S->>S: Build result envelope + timestamp
    S-->>C: JSON / markdown / raw response
```

---

## 3) Command map resolution and override precedence

```mermaid
flowchart TD
    Start["Module import / startup"] --> Env{"NETMCP_COMMAND_OVERRIDES set?"}
    Env -->|Yes| EnvFile["Use env path"]
    Env -->|No| Local{"./netmcp.commands.json exists?"}
    Local -->|Yes| LocalFile["Use local file"]
    Local -->|No| None["No overrides loaded"]

    EnvFile --> Load["Read + JSON decode"]
    LocalFile --> Load

    Load --> Valid{"Top-level JSON object?"}
    Valid -->|No| Err["COMMAND_OVERRIDE_STATUS.error set"]
    Valid -->|Yes| Merge["Merge supported sections:\n inventory / ping / config"]

    Merge --> Apply["Apply vendor-level command overrides\nwith key/type validation"]
    Apply --> Status["COMMAND_OVERRIDE_STATUS\n{loaded, source, applied, error}"]
    None --> Status
    Err --> Status

    Status --> Vendors["Exposed via net_vendors response"]
    Status --> Logs["Shown in startup logs when source exists"]
```

---

## 4) Tool responsibility map

```mermaid
flowchart LR
    NS[net_show] --> SHOW[Single command execution + optional parse]
    NSM[net_show_multi] --> MULTI[Multi-command, one SSH session]
    NI[net_inventory] --> INV[Version / interfaces / routing / neighbors snapshot]
    NP[net_ping] --> PING[On-box ping test with source/VRF options]
    NCB[net_config_backup] --> CFG[Running/startup config capture + metadata header]
    NV[net_vendors] --> META[Server version, vendor registry, override status]
```

---

## 5) Repository structure at a glance

```mermaid
flowchart TD
    Root["netmcp/"] --> PP["pyproject.toml\npackaging + deps + script entrypoint"]
    Root --> RD["README.md\noperator setup + examples"]
    Root --> TO["TECHNICAL_OVERVIEW.md\nfull narrative + remediation notes"]
    Root --> TV["TECHNICAL_VISUAL_MAP.md\nthis visual companion"]
    Root --> PKG["netmcp/"]

    PKG --> SV["server.py\nMCP runtime, models, command maps, tools"]
    PKG --> INIT["__init__.py\npackage marker"]
```

---

## 6) Before vs after remediation

```mermaid
flowchart LR
    subgraph Before[Before]
      B1["Syntax corruption blocked startup"]
      B2["Packaging expected src/ layout"]
      B3["README cwd pointed to wrong path"]
      B4["Vendor map coverage incomplete"]
      B5["No runtime override mechanism"]
    end

    subgraph After[After]
      A1["Server compiles and imports cleanly"]
      A2["Flat package layout builds/install"]
      A3["README matches real directory"]
      A4["Explicit defaults across all advertised vendors"]
      A5["JSON/env command overrides with status reporting"]
    end

    B1 --> A1
    B2 --> A2
    B3 --> A3
    B4 --> A4
    B5 --> A5
```

---

## 7) Quick mental model

- `netmcp` is a read-only MCP orchestration layer over SSH CLI.
- `server.py` owns all runtime behavior: schema validation, command routing, session handling, parsing, formatting.
- Vendor command maps define defaults; override JSON lets you tune behavior without code changes.
- The highest-value operational checks are:
  - import/compile health,
  - command-map correctness per vendor,
  - override load status.
