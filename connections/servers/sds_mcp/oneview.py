"""HPE OneView, read-only, through HPE's own Python SDK (hpeOneView, github.com/HewlettPackard/oneview-python): the SDK
signs in (POST /rest/login-sessions) and reads; its connection is wrapped so that nothing but GET, the sign-in and the
sign-out can be sent, whatever SDK method is called.

The account: a OneView user with the Read only role (a directory group mapped to it works the same way)."""
import re
import threading
from typing import Annotated

from . import common as c
from mcp.server.mcpserver import MCPServer

KIND = "oneview"
LOGIN = "/rest/login-sessions"

server = MCPServer("oneview", instructions=(
    "Read-only HPE OneView. Start with ov_overview (one call: active critical and warning alerts, servers, enclosures and "
    "interconnects not OK, profiles not compliant, recent failed tasks), then narrow down: ov_alerts (with corrective "
    "actions), ov_server_hardware / ov_server (model, serial, health, power, firmware, the iLO address), ov_server_firmware, "
    "ov_environment and ov_utilization (power, temperature, CPU over time), ov_enclosures, ov_interconnects, "
    "ov_server_profiles, ov_tasks (what was done recently). Appliance names come from ov_appliances. Nothing here changes "
    "OneView or a server: no power, profile, firmware or console operation exists in this server."))
_clients, _lock = {}, threading.Lock()


def guard(conn):
    """wrap the SDK connection: GET, plus the sign-in and sign-out of /rest/login-sessions; anything else refused"""
    do_http = conn.do_http

    def read_only(method, path, body, custom_headers=None):
        if method.upper() != "GET" and not (path.split("?", 1)[0] == LOGIN and method.upper() in ("POST", "DELETE")):
            raise c.ReadOnlyViolation(f"{method} {path} refused: this server only reads")
        return do_http(method, path, body, custom_headers=custom_headers)
    conn.do_http = read_only
    return conn


def client(name):
    with _lock:
        if name in _clients:
            return _clients[name]
        from hpeOneView.oneview_client import OneViewClient
        settings = c.target(KIND, name)
        host = settings.get("host") or ""
        if not host or "/" in host:
            raise c.ToolFailure(f"oneview '{name}': host must be the appliance's name or address (host[:port], no scheme)")
        skip = c.unverified(settings)                                      # "verify": false: encrypted, not checked
        if skip:
            c.warn_unverified(KIND, name)
        user, password = c.credentials(KIND, name)
        cred = {"userName": user, "password": password, **({"authLoginDomain": settings["login_domain"]} if settings.get("login_domain") else {})}
        cfg = {"ip": host, "credentials": cred, "ssl_certificate": False if skip else (c.ca_file(settings) or False),
               "trust_all_certs": skip, "timeout": 60}
        if settings.get("api_version"):
            cfg["api_version"] = int(settings["api_version"])
        ov = OneViewClient(cfg)                                            # signs in (POST /rest/login-sessions)
        guard(ov.connection)
        _clients[name] = ov
        return ov


def items(result):
    """the SDK returns a list of resource dicts (get_all) or a resource object (get_by_name)"""
    if result is None:
        return []
    if isinstance(result, list):
        return result
    return [getattr(result, "data", result)]


def call(name, fn):
    """one SDK read; signs in again once when the session expired"""
    for attempt in (1, 2):
        try:
            return fn(client(name))
        except Exception as e:
            if attempt == 1 and ("401" in str(e) or "Unauthorized" in str(e) or "Session" in str(e)):
                with _lock:
                    _clients.pop(name, None)
                continue
            raise


RO = c.read_only
Appliance = Annotated[str, c.arg("The OneView appliance's name in the inventory (ov_appliances lists them), e.g. ov-1.")]
Limit = Annotated[int, c.arg("The most items to return.", ge=1, le=500)]
OnlyProblems = Annotated[bool, c.arg("Only the items whose status is not OK.")]
SERVER_FIELDS = ["name", "serverName", "model", "serialNumber", "status", "state", "powerState", "position", "processorCount",
                 "processorType", "memoryMb", "romVersion", "mpModel", "mpFirmwareVersion", "mpHostInfo.mpHostName",
                 "mpHostInfo.mpIpAddresses", "locationUri", "serverProfileUri", "uri"]


def by_name(ov, kind, name):
    res = (ov.server_hardware if kind == "server" else ov.enclosures).get_by_name(name)
    if res is None:
        raise c.ToolFailure(f"no {kind} named '{name}' (ov_server_hardware / ov_enclosures list them)")
    return res


@server.tool(title="List the appliances", annotations=RO("List the appliances"))
@c.tool
def ov_appliances() -> dict:
    """The OneView appliances in the inventory: names and addresses (no credentials). Use a name with every other tool."""
    return {"appliances": [{"name": n, "host": s.get("host")} for n, s in sorted(c.targets(KIND).items())]}


@server.tool(title="Appliance overview (triage)", annotations=RO("Appliance overview (triage)"))
@c.tool
def ov_overview(appliance: Appliance) -> dict:
    """One call for the state of everything a OneView appliance manages, for a first look or a daily check: active
    critical and warning alerts (newest first), servers, enclosures and interconnects whose status is not OK, server
    profiles not compliant with their template, tasks that failed recently. A part that cannot be read says why."""
    def alerts(sev):
        rows = call(appliance, lambda ov: ov.alerts.get_all(start=0, count=25, filter=["alertState='Active'", f"severity='{sev}'"], sort="created:descending"))
        return c.project(items(rows), ["severity", "description", "correctiveAction", "created", "associatedResource.resourceName"])
    not_ok = lambda res, fields: (lambda: c.project(items(call(appliance, lambda ov: getattr(ov, res).get_all(start=0, count=50, filter=["status<>'OK'"]))), fields))
    out = c.gather({
        "critical_alerts": lambda: alerts("Critical"), "warning_alerts": lambda: alerts("Warning"),
        "servers_not_ok": not_ok("server_hardware", ["name", "model", "status", "powerState", "mpHostInfo.mpIpAddresses"]),
        "enclosures_not_ok": not_ok("enclosures", ["name", "status", "state"]),
        "interconnects_not_ok": not_ok("interconnects", ["name", "status", "state", "enclosureName"]),
        "profiles_not_compliant": lambda: c.project(items(call(appliance, lambda ov: ov.server_profiles.get_all(
            start=0, count=50, filter=["templateCompliance='NonCompliant'"]))), ["name", "status", "templateCompliance"]),
        "failed_tasks": lambda: c.project(items(call(appliance, lambda ov: ov.tasks.get_all(
            start=0, count=20, filter=["taskState='Error'"], sort="created:descending"))), ["name", "owner", "created", "associatedResource.resourceName"]),
    })
    return {"appliance": appliance, **out}


@server.tool(title="Appliance version", annotations=RO("Appliance version"))
@c.tool
def ov_version(appliance: Appliance) -> dict:
    """The appliance's API version range and software version."""
    def read(ov):
        out = {"api": ov.connection.get("/rest/version")}
        try:
            out["appliance"] = ov.connection.get("/rest/appliance/nodeinfo/version")
        except Exception:
            pass
        return out
    return dict(call(appliance, read), appliance=appliance)


@server.tool(title="Alerts", annotations=RO("Alerts"))
@c.tool
def ov_alerts(appliance: Appliance,
              state: Annotated[str, c.arg("Active (default), Locked, Cleared, or empty for all.", pattern="^(Active|Locked|Cleared|)$")] = "Active",
              severity: Annotated[str, c.arg("Critical, Warning, OK, or empty for all.", pattern="^(Critical|Warning|OK|Disabled|Unknown|)$")] = "",
              limit: Limit = 50) -> dict:
    """Alerts, newest first: severity, state, description, corrective action, health category, the resource it concerns."""
    flt = ([f"alertState='{state}'"] if state else []) + ([f"severity='{severity}'"] if severity else [])
    rows = call(appliance, lambda ov: ov.alerts.get_all(start=0, count=c.limit_of(limit), filter=flt, sort="created:descending"))
    return {"appliance": appliance, "count": len(rows), "alerts": c.project(items(rows), [
        "severity", "alertState", "description", "correctiveAction", "created", "modified", "healthCategory",
        "physicalResourceType", "associatedResource.resourceName", "associatedResource.resourceCategory", "alertTypeID"])}


@server.tool(title="Servers", annotations=RO("Servers"))
@c.tool
def ov_server_hardware(appliance: Appliance,
                       name_contains: Annotated[str, c.arg("Only servers whose name contains this text.", pattern=r"^[A-Za-z0-9 ._-]{0,100}$")] = "",
                       only_problems: OnlyProblems = False, limit: Limit = 100) -> dict:
    """Servers: name, model, serial, health status, power state, ROM and iLO firmware, the iLO address, enclosure bay."""
    flt = (["status<>'OK'"] if only_problems else []) + ([f"name matches '%{name_contains}%'"] if name_contains else [])
    rows = call(appliance, lambda ov: ov.server_hardware.get_all(start=0, count=c.limit_of(limit), filter=flt))
    return {"appliance": appliance, "count": len(rows), "servers": c.project(items(rows), SERVER_FIELDS)}


@server.tool(title="One server", annotations=RO("One server"))
@c.tool
def ov_server(appliance: Appliance, server_name: Annotated[str, c.arg("The server's name in OneView (ov_server_hardware).")]) -> dict:
    """One server in detail: hardware, firmware, health, the iLO address, the profile assigned, memory, processors and
    local storage summaries."""
    data = call(appliance, lambda ov: items(by_name(ov, "server", server_name))[0])
    return {"appliance": appliance, "server": c.project([data], SERVER_FIELDS + [
        "partNumber", "formFactor", "generation", "intelligentProvisioningVersion", "licensingIntent", "uidState",
        "portMap", "subResources.LocalStorage", "subResources.Memory", "subResources.Processors"])[0]}


@server.tool(title="A server's firmware", annotations=RO("A server's firmware"))
@c.tool
def ov_server_firmware(appliance: Appliance, server_name: Annotated[str, c.arg("The server's name in OneView.")]) -> dict:
    """A server's firmware inventory as OneView reads it: every component (system ROM, iLO, controllers, drives,
    adapters, power) with its installed version."""
    return {"appliance": appliance, "server": server_name, "firmware": call(appliance, lambda ov: by_name(ov, "server", server_name).get_firmware())}


@server.tool(title="Power and thermal configuration", annotations=RO("Power and thermal configuration"))
@c.tool
def ov_environment(appliance: Appliance, name: Annotated[str, c.arg("The server's or enclosure's name in OneView.")],
                   resource: Annotated[str, c.arg("server (default) or enclosure.", pattern="^(server|enclosure)$")] = "server") -> dict:
    """A server's or enclosure's environmental configuration: calibrated maximum power, power capping, the metrics
    OneView collects for it and at which rate (then ov_utilization for the values)."""
    return {"appliance": appliance, resource: name,
            "environment": call(appliance, lambda ov: by_name(ov, resource, name).get_environmental_configuration())}


@server.tool(title="Power, temperature and CPU over time", annotations=RO("Power, temperature and CPU over time"))
@c.tool
def ov_utilization(appliance: Appliance, name: Annotated[str, c.arg("The server's or enclosure's name in OneView.")],
                   resource: Annotated[str, c.arg("server (default) or enclosure.", pattern="^(server|enclosure)$")] = "server",
                   metrics: Annotated[str, c.arg("Comma-separated metric names. server: CpuUtilization, CpuAverageFreq, AveragePower, "
                                                 "PeakPower, PowerCap, AmbientTemperature; enclosure: AveragePower, PeakPower, PowerCap, "
                                                 "AmbientTemperature.", pattern=r"^[A-Za-z,]{1,200}$")] = "CpuUtilization,AveragePower,AmbientTemperature",
                   limit: Annotated[int, c.arg("The most samples per metric (newest first).", ge=1, le=1000)] = 60) -> dict:
    """A server's or enclosure's utilization as OneView has collected it from the iLO (CPU, power, temperature), newest
    samples first. Reads what OneView already has; nothing is asked of the iLO."""
    data = call(appliance, lambda ov: by_name(ov, resource, name).get_utilization(fields=metrics, refresh=False)) or {}
    data = getattr(data, "data", data) if not isinstance(data, dict) else data
    out = {"appliance": appliance, resource: name}
    out.update({k: v for k, v in data.items() if k != "metricList" and not isinstance(v, (list, dict))})   # as OneView names them
    if isinstance(data.get("metricList"), list):
        out["metrics"] = {m.get("metricName"): {"capacity": m.get("metricCapacity"), "samples": (m.get("metricSamples") or [])[:c.limit_of(limit, 60, 1000)]}
                          for m in data["metricList"] if isinstance(m, dict)}
    else:
        out["data"] = data
    return out


@server.tool(title="Enclosures", annotations=RO("Enclosures"))
@c.tool
def ov_enclosures(appliance: Appliance, limit: Limit = 50) -> dict:
    """Enclosures: name, model, serial, status, state, firmware baseline, device and interconnect bays."""
    rows = call(appliance, lambda ov: ov.enclosures.get_all(start=0, count=c.limit_of(limit)))
    return {"appliance": appliance, "count": len(rows), "enclosures": c.project(items(rows), [
        "name", "model", "serialNumber", "status", "state", "enclosureType", "fwBaselineName", "isFwManaged",
        "deviceBayCount", "interconnectBayCount", "uidState", "uri"])}


@server.tool(title="Interconnects", annotations=RO("Interconnects"))
@c.tool
def ov_interconnects(appliance: Appliance, only_problems: OnlyProblems = False, limit: Limit = 100) -> dict:
    """Interconnect modules: name, model, status, state, firmware, enclosure and bay."""
    rows = call(appliance, lambda ov: ov.interconnects.get_all(start=0, count=c.limit_of(limit), filter=["status<>'OK'"] if only_problems else []))
    return {"appliance": appliance, "count": len(rows), "interconnects": c.project(items(rows), [
        "name", "model", "productName", "status", "state", "firmwareVersion", "enclosureName", "interconnectLocation", "uri"])}


@server.tool(title="Server profiles", annotations=RO("Server profiles"))
@c.tool
def ov_server_profiles(appliance: Appliance, only_problems: OnlyProblems = False, limit: Limit = 100) -> dict:
    """Server profiles: name, status, state, compliance with their template, the server assigned, firmware baseline."""
    rows = call(appliance, lambda ov: ov.server_profiles.get_all(start=0, count=c.limit_of(limit), filter=["status<>'OK'"] if only_problems else []))
    return {"appliance": appliance, "count": len(rows), "profiles": c.project(items(rows), [
        "name", "status", "state", "templateCompliance", "serverHardwareUri", "serverProfileTemplateUri",
        "firmware.firmwareBaselineUri", "firmware.manageFirmware", "modified"])}


@server.tool(title="Recent tasks", annotations=RO("Recent tasks"))
@c.tool
def ov_tasks(appliance: Appliance, limit: Annotated[int, c.arg("The most tasks to return.", ge=1, le=500)] = 30,
             only_errors: Annotated[bool, c.arg("Only tasks that ended in error.")] = False) -> dict:
    """What was done on the appliance recently, newest first: task, state, owner, resource, times. What changed before an
    incident."""
    rows = call(appliance, lambda ov: ov.tasks.get_all(start=0, count=c.limit_of(limit, 30), filter=["taskState='Error'"] if only_errors else [], sort="created:descending"))
    return {"appliance": appliance, "count": len(rows), "tasks": c.project(items(rows), [
        "name", "taskState", "percentComplete", "owner", "created", "modified", "associatedResource.resourceName",
        "associatedResource.resourceCategory", "taskErrors"])}
