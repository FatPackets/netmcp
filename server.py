"""
netmcp - Network Engineering MCP Server
Author: 0xFATPKT (rtsegovia18@gmail.com)
GitHub: https://github.com/0xFATPKT/netmcp

Multi-vendor network automation via Model Context Protocol.
Cisco IOS/NX-OS/ASA, F5, Check Point — structured output, not CLI vomit.
"""

import json
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field, field_validator, ConfigDict

try:
    from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
    NETMIKO_AVAILABLE = True
except ImportError:
    NETMIKO_AVAILABLE = False

try:
    from ntc_templates.parse import parse_output
    NTC_AVAILABLE = True
except ImportError:
    NTC_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

VERSION = "0.1.0"
SERVER_NAME = "netmcp"

SUPPORTED_VENDORS = {
    "cisco_ios":    "Cisco IOS (routers, switches)",
    "cisco_nxos":   "Cisco NX-OS (Nexus)",
    "cisco_asa":    "Cisco ASA (firewall)",
    "cisco_ftd":    "Cisco Firepower Threat Defense",
    "cisco_xr":     "Cisco IOS-XR",
    "f5_tmsh":      "F5 BIG-IP (TMSH)",
    "checkpoint":   "Check Point (CLISH/Expert)",
    "juniper_junos":"Juniper JunOS",
    "arista_eos":   "Arista EOS",
    "paloalto_panos":"Palo Alto PAN-OS",
}

DEFAULT_TIMEOUT = 30
DEFAULT_PORT = 22

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(SERVER_NAME)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class VendorType(str, Enum):
    CISCO_IOS    = "cisco_ios"
    CISCO_NXOS   = "cisco_nxos"
    CISCO_ASA    = "cisco_asa"
    CISCO_FTD    = "cisco_ftd"
    CISCO_XR     = "cisco_xr"
    F5_TMSH      = "f5_tmsh"
    CHECKPOINT   = "checkpoint"
    JUNIPER      = "juniper_junos"
    ARISTA       = "arista_eos"
    PALOALTO     = "paloalto_panos"

class ResponseFormat(str, Enum):
    JSON     = "json"
    MARKDOWN = "markdown"
    RAW      = "raw"


# ═══════════════════════════════════════════════════════════════════════════════
# INPUT MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class DeviceTarget(BaseModel):
    """Connection parameters for a network device."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    host: str = Field(..., description="Device IP address or hostname (e.g., '10.0.0.1', 'core-sw-01.lab.local')", min_length=1, max_length=255)
    vendor: VendorType = Field(..., description=f"Device vendor/OS type. Supported: {', '.join(SUPPORTED_VENDORS.keys())}")
    username: str = Field(..., description="SSH username", min_length=1, max_length=64)
    password: str = Field(..., description="SSH password", min_length=1, max_length=128)
    port: int = Field(default=DEFAULT_PORT, description="SSH port (default: 22)", ge=1, le=65535)
    timeout: int = Field(default=DEFAULT_TIMEOUT, description="Connection timeout in seconds (default: 30)", ge=5, le=300)
    secret: Optional[str] = Field(default=None, description="Enable secret (Cisco devices). Required for privileged exec mode.")
    use_keys: bool = Field(default=False, description="Use SSH key authentication instead of password")
    key_file: Optional[str] = Field(default=None, description="Path to SSH private key file (when use_keys=True)")

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Host cannot be empty")
        return v.strip()


class ShowCommandInput(BaseModel):
    """Input for executing show/display commands."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    device: DeviceTarget
    command: str = Field(..., description="Show command to execute (e.g., 'show ip route', 'show version', 'show interfaces')", min_length=1, max_length=512)
    parse: bool = Field(default=True, description="Attempt structured parsing via ntc-templates (True) or return raw output (False)")
    response_format: ResponseFormat = Field(default=ResponseFormat.JSON, description="Output format: json (structured), markdown (human-readable), raw (CLI output)")


class MultiCommandInput(BaseModel):
    """Input for executing multiple show commands in sequence."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    device: DeviceTarget
    commands: List[str] = Field(..., description="List of show commands to execute sequentially", min_length=1, max_length=20)
    response_format: ResponseFormat = Field(default=ResponseFormat.JSON, description="Output format for all results")


class DeviceInventoryInput(BaseModel):
    """Input for capturing full device inventory/state snapshot."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    device: DeviceTarget
    include_routing: bool = Field(default=True, description="Include routing table snapshot")
    include_interfaces: bool = Field(default=True, description="Include interface status and counters")
    include_neighbors: bool = Field(default=True, description="Include CDP/LLDP neighbor discovery")
    include_version: bool = Field(default=True, description="Include version and hardware info")
    response_format: ResponseFormat = Field(default=ResponseFormat.JSON, description="Output format")


class PingTestInput(BaseModel):
    """Input for connectivity testing from a device."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    device: DeviceTarget
    target: str = Field(..., description="IP address or hostname to ping from the device", min_length=1, max_length=255)
    count: int = Field(default=5, description="Number of ping packets (default: 5)", ge=1, le=100)
    source: Optional[str] = Field(default=None, description="Source interface or IP for ping (optional)")
    vrf: Optional[str] = Field(default=None, description="VRF name for ping (optional)")


class ConfigBackupInput(BaseModel):
    """Input for capturing device configuration."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    device: DeviceTarget
    config_type: str = Field(default="running", description="Config type: 'running' or 'startup'")
    include_timestamp: bool = Field(default=True, description="Prepend timestamp and device info header to output")

    @field_validator("config_type")
    @classmethod
    def validate_config_type(cls, v: str) -> str:
        if v not in ("running", "startup"):
            raise ValueError("config_type must be 'running' or 'startup'")
        return v


# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _build_netmiko_params(device: DeviceTarget) -> Dict[str, Any]:
    """Build Netmiko connection parameters from DeviceTarget."""
    params: Dict[str, Any] = {
        "device_type": device.vendor.value,
        "host": device.host,
        "username": device.username,
        "password": device.password,
        "port": device.port,
        "timeout": device.timeout,
        "conn_timeout": device.timeout,
        "auth_timeout": device.timeout,
        "banner_timeout": device.timeout,
        "fast_cli": False,
    }
    if device.secret:
        params["secret"] = device.secret
    if device.use_keys and device.key_file:
        params["use_keys"] = True
        params["key_file"] = device.key_file
        params["password"] = ""
    return params


def _attempt_parse(vendor: str, command: str, output: str) -> Optional[List[Dict]]:
    """Attempt ntc-templates structured parsing. Returns None if unavailable or no template."""
    if not NTC_AVAILABLE:
        return None
    try:
        parsed = parse_output(platform=vendor, command=command, data=output)
        if parsed and parsed != [{}]:
            return parsed
    except Exception:
        pass
    return None


def _format_error(e: Exception, host: str) -> str:
    """Consistent error formatting with actionable guidance."""
    if not NETMIKO_AVAILABLE:
        return json.dumps({
            "error": "netmiko not installed",
            "action": "Run: pip install netmiko ntc-templates",
            "host": host
        }, indent=2)
    if isinstance(e, NetmikoAuthenticationException):
        return json.dumps({
            "error": "Authentication failed",
            "host": host,
            "action": "Verify username, password, and enable secret. Check AAA config on device."
        }, indent=2)
    if isinstance(e, NetmikoTimeoutException):
        return json.dumps({
            "error": "Connection timed out",
            "host": host,
            "action": "Verify IP reachability, SSH enabled, ACL permits your source IP, timeout value sufficient."
        }, indent=2)
    if isinstance(e, ConnectionRefusedError):
        return json.dumps({
            "error": "Connection refused",
            "host": host,
            "action": "Verify SSH is enabled (ip ssh version 2), port is correct, device is reachable."
        }, indent=2)
    return json.dumps({
        "error": str(e),
        "error_type": type(e).__name__,
        "host": host,
        "action": "Check device reachability and credentials."
    }, indent=2)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _format_result(data: Any, fmt: ResponseFormat, title: str = "") -> str:
    """Format tool output per requested format."""
    if fmt == ResponseFormat.RAW:
        return str(data) if not isinstance(data, str) else data
    if fmt == ResponseFormat.JSON:
        if isinstance(data, str):
            return json.dumps({"output": data, "timestamp": _timestamp()}, indent=2)
        return json.dumps({"result": data, "timestamp": _timestamp()}, indent=2)
    # Markdown
    lines = [f"## {title}" if title else "## Result", ""]
    if isinstance(data, list):
        for i, item in enumerate(data, 1):
            lines.append(f"### Entry {i}")
            if isinstance(item, dict):
                for k, v in item.items():
                    lines.append(f"- **{k}**: {v}")
            else:
                lines.append(str(item))
            lines.append("")
    elif isinstance(data, dict):
        for k, v in data.items():
            lines.append(f"- **{k}**: {v}")
    else:
        lines.append(f"```\n{data}\n```")
    lines.append(f"\n*Captured: {_timestamp()}*")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# VENDOR COMMAND MAPS
# ═══════════════════════════════════════════════════════════════════════════════

INVENTORY_COMMANDS: Dict[str, Dict[str, str]] = {
    "cisco_ios": {
        "version":    "show version",
        "interfaces": "show interfaces",
        "routing":    "show ip route",
        "neighbors":  "show cdp neighbors detail",
    },
    "cisco_nxos": {
        "version":    "show version",
        "interfaces": "show interface",
        "routing":    "show ip route",
        "neighbors":  "show cdp neighbors detail",
    },
    "cisco_asa": {
        "version":    "show version",
        "interfaces": "show interface",
        "routing":    "show route",
        "neighbors":  "show arp",
    },
    "f5_tmsh": {
        "version":    "show sys version",
        "interfaces": "show net interface",
        "routing":    "show net route",
        "neighbors":  "show net arp",
    },
    "arista_eos": {
        "version":    "show version",
        "interfaces": "show interfaces",
        "routing":    "show ip route",
        "neighbors":  "show lldp neighbors detail",
    },
    "juniper_junos": {
        "version":    "show version",
        "interfaces": "show interfaces",
        "routing":    "show route",
        "neighbors":  "show lldp neighbors",
    },
}

PING_COMMANDS: Dict[str, str] = {
    "cisco_ios":    "ping {target} repeat {count}{source}{vrf}",
    "cisco_nxos":   "ping {target} count {count}{source}{vrf}",
    "cisco_asa":    "ping {target}",
    "f5_tmsh":      "ping -c {count} {target}",
    "arista_eos":   "ping {target} repeat {count}",
    "juniper_junos":"ping {target} count {count}",
}

CONFIG_COMMANDS: Dict[str, Dict[str, str]] = {
    "cisco_ios":    {"running": "show running-config", "startup": "show startup-config"},
    "cisco_nxos":   {"running": "show running-config", "startup": "show startup-config"},
    "cisco_asa":    {"running": "show running-config", "startup": "show startup-config"},
    "f5_tmsh":      {"running": "list", "startup": "list"},
    "arista_eos":   {"running": "show running-config", "startup": "show startup-config"},
    "juniper_junos":{"running": "show configuration", "startup": "show configuration"},
}


# ═══════════════════════════════════════════════════════════════════════════════
# LIFESPAN
# ═══════════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def app_lifespan():
    logger.info("═" * 60)
    logger.info(f"  netmcp v{VERSION} starting")
    logger.info(f"  netmiko available : {NETMIKO_AVAILABLE}")
    logger.info(f"  ntc-templates     : {NTC_AVAILABLE}")
    logger.info(f"  vendors supported : {len(SUPPORTED_VENDORS)}")
    logger.info("═" * 60)
    yield {}
    logger.info("netmcp shutdown complete")


# ═══════════════════════════════════════════════════════════════════════════════
# SERVER INIT
# ═══════════════════════════════════════════════════════════════════════════════

mcp = FastMCP(SERVER_NAME, lifespan=app_lifespan)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS — READ / DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool(
    name="net_show",
    annotations={
        "title": "Execute Show Command",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def net_show(params: ShowCommandInput, ctx: Context) -> str:
    """Execute a single show/display command on a network device and return structured output.

    Connects via SSH using Netmiko, executes the command, and attempts structured
    parsing via ntc-templates when parse=True. Returns raw CLI output as fallback.

    Supports: Cisco IOS/NX-OS/ASA/XR, F5 BIG-IP, Check Point, Juniper, Arista, Palo Alto.

    Args:
        params (ShowCommandInput): Device connection parameters and command details.
            - device (DeviceTarget): Host, vendor, credentials, port, timeout
            - command (str): Show command (e.g., 'show ip route', 'show version')
            - parse (bool): Attempt ntc-templates structured parsing (default: True)
            - response_format (ResponseFormat): json | markdown | raw

    Returns:
        str: JSON with parsed structured data or raw output, plus metadata.
             Schema: {"host": str, "command": str, "parsed": bool,
                      "data": list|str, "timestamp": str}
    """
    if not NETMIKO_AVAILABLE:
        return _format_error(Exception("netmiko not installed"), params.device.host)

    await ctx.report_progress(0.1, f"Connecting to {params.device.host}...")

    try:
        conn_params = _build_netmiko_params(params.device)
        loop = asyncio.get_event_loop()

        def _execute():
            with ConnectHandler(**conn_params) as conn:
                if params.device.secret:
                    conn.enable()
                return conn.send_command(params.command, read_timeout=params.device.timeout)

        await ctx.report_progress(0.4, "Executing command...")
        output = await loop.run_in_executor(None, _execute)

        await ctx.report_progress(0.7, "Parsing output...")
        parsed_data = None
        parsed = False
        if params.parse:
            parsed_data = _attempt_parse(params.device.vendor.value, params.command, output)
            if parsed_data:
                parsed = True

        await ctx.report_progress(0.95, "Formatting result...")

        result = {
            "host": params.device.host,
            "vendor": params.device.vendor.value,
            "command": params.command,
            "parsed": parsed,
            "data": parsed_data if parsed else output,
            "timestamp": _timestamp(),
        }

        if params.response_format == ResponseFormat.JSON:
            return json.dumps(result, indent=2)
        if params.response_format == ResponseFormat.RAW:
            return output
        return _format_result(parsed_data or output, ResponseFormat.MARKDOWN, f"`{params.command}` on {params.device.host}")

    except Exception as e:
        ctx.log_error(f"net_show failed on {params.device.host}: {e}")
        return _format_error(e, params.device.host)


@mcp.tool(
    name="net_show_multi",
    annotations={
        "title": "Execute Multiple Show Commands",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def net_show_multi(params: MultiCommandInput, ctx: Context) -> str:
    """Execute multiple show commands on a device in a single SSH session.

    More efficient than multiple net_show calls — opens one connection, runs all
    commands, closes. Useful for state snapshots, troubleshooting bundles, or
    collecting related show outputs together.

    Args:
        params (MultiCommandInput): Device target and list of commands.
            - device (DeviceTarget): Connection parameters
            - commands (List[str]): Up to 20 show commands
            - response_format (ResponseFormat): json | markdown | raw

    Returns:
        str: JSON array of results per command.
             Schema: {"host": str, "results": [{"command": str, "output": str,
                      "parsed": bool, "data": list|str}], "timestamp": str}
    """
    if not NETMIKO_AVAILABLE:
        return _format_error(Exception("netmiko not installed"), params.device.host)

    await ctx.report_progress(0.1, f"Connecting to {params.device.host}...")

    try:
        conn_params = _build_netmiko_params(params.device)
        loop = asyncio.get_event_loop()
        commands = params.commands

        def _execute_all():
            results = []
            with ConnectHandler(**conn_params) as conn:
                if params.device.secret:
                    conn.enable()
                for cmd in commands:
                    try:
                        out = conn.send_command(cmd, read_timeout=params.device.timeout)
                        parsed_data = _attempt_parse(params.device.vendor.value, cmd, out)
                        results.append({
                            "command": cmd,
                            "parsed": bool(parsed_data),
                            "data": parsed_data if parsed_data else out,
                            "error": None,
                        })
                    except Exception as cmd_err:
                        results.append({
                            "command": cmd,
                            "parsed": False,
                            "data": None,
                            "error": str(cmd_err),
                        })
            return results

        total = len(commands)
        await ctx.report_progress(0.3, f"Executing {total} commands...")
        results = await loop.run_in_executor(None, _execute_all)
        await ctx.report_progress(0.95, "Done")

        response = {
            "host": params.device.host,
            "vendor": params.device.vendor.value,
            "command_count": total,
            "results": results,
            "timestamp": _timestamp(),
        }
        return json.dumps(response, indent=2)

    except Exception as e:
        ctx.log_error(f"net_show_multi failed on {params.device.host}: {e}")
        return _format_error(e, params.device.host)


@mcp.tool(
    name="net_inventory",
    annotations={
        "title": "Capture Device Inventory Snapshot",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def net_inventory(params: DeviceInventoryInput, ctx: Context) -> str:
    """Capture a comprehensive state snapshot of a network device.

    Runs version, interface, routing, and neighbor commands in one session.
    All output is parsed where ntc-templates support exists. Useful for
    documentation, baselining, change verification, and audit captures.

    Args:
        params (DeviceInventoryInput): Device target and snapshot options.
            - device (DeviceTarget): Connection parameters
            - include_routing (bool): Capture routing table (default: True)
            - include_interfaces (bool): Capture interface state (default: True)
            - include_neighbors (bool): Run CDP/LLDP discovery (default: True)
            - include_version (bool): Capture version/hardware info (default: True)
            - response_format (ResponseFormat): json | markdown | raw

    Returns:
        str: JSON snapshot with all requested sections.
             Schema: {"host": str, "vendor": str, "snapshot": {"version": ...,
                      "interfaces": ..., "routing": ..., "neighbors": ...},
                      "timestamp": str}
    """
    if not NETMIKO_AVAILABLE:
        return _format_error(Exception("netmiko not installed"), params.device.host)

    vendor = params.device.vendor.value
    cmd_map = INVENTORY_COMMANDS.get(vendor, INVENTORY_COMMANDS["cisco_ios"])

    commands_to_run = {}
    if params.include_version:
        commands_to_run["version"] = cmd_map.get("version")
    if params.include_interfaces:
        commands_to_run["interfaces"] = cmd_map.get("interfaces")
    if params.include_routing:
        commands_to_run["routing"] = cmd_map.get("routing")
    if params.include_neighbors:
        commands_to_run["neighbors"] = cmd_map.get("neighbors")

    commands_to_run = {k: v for k, v in commands_to_run.items() if v}

    await ctx.report_progress(0.1, f"Connecting to {params.device.host} for inventory...")

    try:
        conn_params = _build_netmiko_params(params.device)
        loop = asyncio.get_event_loop()
        sections = list(commands_to_run.items())

        def _capture():
            snapshot = {}
            with ConnectHandler(**conn_params) as conn:
                if params.device.secret:
                    conn.enable()
                for section, cmd in sections:
                    try:
                        out = conn.send_command(cmd, read_timeout=params.device.timeout)
                        parsed = _attempt_parse(vendor, cmd, out)
                        snapshot[section] = {
                            "command": cmd,
                            "parsed": bool(parsed),
                            "data": parsed if parsed else out,
                        }
                    except Exception as e:
                        snapshot[section] = {"command": cmd, "error": str(e)}
            return snapshot

        await ctx.report_progress(0.4, f"Capturing {len(sections)} inventory sections...")
        snapshot = await loop.run_in_executor(None, _capture)
        await ctx.report_progress(0.95, "Inventory complete")

        result = {
            "host": params.device.host,
            "vendor": vendor,
            "sections_captured": list(snapshot.keys()),
            "snapshot": snapshot,
            "timestamp": _timestamp(),
        }
        return json.dumps(result, indent=2)

    except Exception as e:
        ctx.log_error(f"net_inventory failed on {params.device.host}: {e}")
        return _format_error(e, params.device.host)


@mcp.tool(
    name="net_ping",
    annotations={
        "title": "Connectivity Test from Device",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
async def net_ping(params: PingTestInput, ctx: Context) -> str:
    """Execute a ping test FROM a network device to a target destination.

    Useful for validating routing paths, VRF reachability, and sourcing pings
    from specific interfaces for policy verification. Not a ping TO the device.

    Args:
        params (PingTestInput): Device, target, and ping options.
            - device (DeviceTarget): The device to ping FROM
            - target (str): Destination IP or hostname
            - count (int): Packet count (default: 5)
            - source (str): Source interface or IP (optional)
            - vrf (str): VRF name (optional)

    Returns:
        str: JSON with raw ping output and success assessment.
             Schema: {"host": str, "target": str, "output": str,
                      "success": bool, "timestamp": str}
    """
    if not NETMIKO_AVAILABLE:
        return _format_error(Exception("netmiko not installed"), params.device.host)

    vendor = params.device.vendor.value
    ping_template = PING_COMMANDS.get(vendor, "ping {target} repeat {count}")

    source_str = f" source {params.source}" if params.source else ""
    vrf_str = f" vrf {params.vrf}" if params.vrf else ""
    cmd = ping_template.format(
        target=params.target,
        count=params.count,
        source=source_str,
        vrf=vrf_str,
    )

    await ctx.report_progress(0.1, f"Connecting to {params.device.host}...")

    try:
        conn_params = _build_netmiko_params(params.device)
        loop = asyncio.get_event_loop()

        def _ping():
            with ConnectHandler(**conn_params) as conn:
                if params.device.secret:
                    conn.enable()
                return conn.send_command(cmd, read_timeout=60, expect_string=r"#")

        await ctx.report_progress(0.4, f"Pinging {params.target} from {params.device.host}...")
        output = await loop.run_in_executor(None, _ping)

        success = any(indicator in output.lower() for indicator in [
            "success rate is 100", "success rate is 8", "success rate is 6",
            "0% packet loss", "bytes from"
        ])

        result = {
            "host": params.device.host,
            "target": params.target,
            "command": cmd,
            "output": output,
            "success": success,
            "source": params.source,
            "vrf": params.vrf,
            "timestamp": _timestamp(),
        }
        return json.dumps(result, indent=2)

    except Exception as e:
        ctx.log_error(f"net_ping failed on {params.device.host}: {e}")
        return _format_error(e, params.device.host)


@mcp.tool(
    name="net_config_backup",
    annotations={
        "title": "Capture Device Configuration",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def net_config_backup(params: ConfigBackupInput, ctx: Context) -> str:
    """Capture the running or startup configuration from a network device.

    Returns the full configuration text with optional header metadata.
    Use for documentation, audit, change management baselines, or diff comparisons.
    This is a READ-ONLY operation — it does not modify the device.

    Args:
        params (ConfigBackupInput): Device target and config options.
            - device (DeviceTarget): Connection parameters
            - config_type (str): 'running' or 'startup'
            - include_timestamp (bool): Add metadata header (default: True)

    Returns:
        str: JSON with configuration text and metadata.
             Schema: {"host": str, "config_type": str, "config": str,
                      "char_count": int, "line_count": int, "timestamp": str}
    """
    if not NETMIKO_AVAILABLE:
        return _format_error(Exception("netmiko not installed"), params.device.host)

    vendor = params.device.vendor.value
    cmd_map = CONFIG_COMMANDS.get(vendor, {"running": "show running-config", "startup": "show startup-config"})
    cmd = cmd_map.get(params.config_type, "show running-config")

    await ctx.report_progress(0.1, f"Connecting to {params.device.host}...")

    try:
        conn_params = _build_netmiko_params(params.device)
        loop = asyncio.get_event_loop()

        def _get_config():
            with ConnectHandler(**conn_params) as conn:
                if params.device.secret:
                    conn.enable()
                return conn.send_command(cmd, read_timeout=120)

        await ctx.report_progress(0.4, f"Capturing {params.config_type} config...")
        config_text = await loop.run_in_executor(None, _get_config)

        ts = _timestamp()
        header = ""
        if params.include_timestamp:
            header = (
                f"! netmcp config backup\n"
                f"! host      : {params.device.host}\n"
                f"! vendor    : {vendor}\n"
                f"! type      : {params.config_type}\n"
                f"! captured  : {ts}\n"
                f"!\n"
            )

        full_config = header + config_text
        result = {
            "host": params.device.host,
            "vendor": vendor,
            "config_type": params.config_type,
            "config": full_config,
            "char_count": len(full_config),
            "line_count": full_config.count("\n"),
            "timestamp": ts,
        }
        return json.dumps(result, indent=2)

    except Exception as e:
        ctx.log_error(f"net_config_backup failed on {params.device.host}: {e}")
        return _format_error(e, params.device.host)


@mcp.tool(
    name="net_vendors",
    annotations={
        "title": "List Supported Vendors",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def net_vendors() -> str:
    """List all supported network device vendors and their vendor type strings.

    Use this to find the correct vendor value for the DeviceTarget.vendor field
    before connecting to a device. Returns vendor keys and human-readable descriptions.

    Returns:
        str: JSON with supported vendors and server version info.
             Schema: {"version": str, "vendors": {"key": "description"}, "count": int}
    """
    return json.dumps({
        "version": VERSION,
        "netmiko_available": NETMIKO_AVAILABLE,
        "ntc_templates_available": NTC_AVAILABLE,
        "vendors": SUPPORTED_VENDORS,
        "count": len(SUPPORTED_VENDORS),
        "timestamp": _timestamp(),
    }, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    mcp.run()
