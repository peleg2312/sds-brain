"""HPE OneView, read-only, through HPE's own Python SDK (hpeOneView, github.com/HewlettPackard/oneview-python): the SDK
signs in (POST /rest/login-sessions) and reads; its connection is wrapped so that nothing but GET, the sign-in and the
sign-out can be sent, whatever SDK method is called.

The account: a OneView user with the Read only role (a directory group mapped to it works the same way)."""
import threading

from . import common as c
from mcp.server.mcpserver import MCPServer

KIND = "oneview"
LOGIN = "/rest/login-sessions"

server = MCPServer("oneview", instructions=(
    "Read-only HPE OneView. Start with ov_appliances; ov_alerts for active alerts (with corrective actions), "
    "ov_server_hardware for servers (model, serial, power, health, firmware, the iLO address), ov_server for one server, "
    "ov_enclosures, ov_interconnects, ov_server_profiles, ov_tasks for what was done recently. Nothing here changes "
    "OneView or a server (no power, profile or firmware operation exists in this server)."))
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
        c.tls_context(settings)                                            # refuses insecure settings
        user, password = c.credentials(KIND, name)
        cred = {"userName": user, "password": password, **({"authLoginDomain": settings["login_domain"]} if settings.get("login_domain") else {})}
        cfg = {"ip": host, "credentials": cred, "ssl_certificate": c.ca_file(settings) or False, "timeout": 60}
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


RO = c.read_only()
SERVER_FIELDS = ["name", "serverName", "model", "serialNumber", "status", "state", "powerState", "position", "processorCount",
                 "processorType", "memoryMb", "romVersion", "mpModel", "mpFirmwareVersion", "mpHostInfo.mpHostName",
                 "mpHostInfo.mpIpAddresses", "locationUri", "serverProfileUri", "uri"]


@server.tool(annotations=RO)
@c.tool
def ov_appliances() -> dict:
    """The OneView appliances in the inventory (names and addresses only)."""
    return {"appliances": [{"name": n, "host": s.get("host")} for n, s in sorted(c.targets(KIND).items())]}


@server.tool(annotations=RO)
@c.tool
def ov_version(appliance: str) -> dict:
    """The appliance's API version range and software version."""
    def read(ov):
        out = {"api": ov.connection.get("/rest/version")}
        try:
            out["appliance"] = ov.connection.get("/rest/appliance/nodeinfo/version")
        except Exception:
            pass
        return out
    return dict(call(appliance, read), appliance=appliance)


@server.tool(annotations=RO)
@c.tool
def ov_alerts(appliance: str, state: str = "Active", severity: str = "", limit: int = 50) -> dict:
    """Alerts, newest first: severity, state, description, corrective action, the resource it concerns.
    state: Active (default), Locked, Cleared or "" for all; severity: Critical, Warning, OK or "" for all."""
    flt = []
    if state:
        flt.append(f"alertState='{state}'")
    if severity:
        flt.append(f"severity='{severity}'")
    if any("'" in x for x in (state, severity)):
        raise c.ToolFailure("state / severity: a single word")
    rows = call(appliance, lambda ov: ov.alerts.get_all(start=0, count=c.limit_of(limit), filter=flt, sort="created:descending"))
    return {"appliance": appliance, "count": len(rows), "alerts": c.project(items(rows), [
        "severity", "alertState", "description", "correctiveAction", "created", "modified", "healthCategory",
        "physicalResourceType", "associatedResource.resourceName", "associatedResource.resourceCategory", "alertTypeID"])}


@server.tool(annotations=RO)
@c.tool
def ov_server_hardware(appliance: str, name_contains: str = "", only_problems: bool = False, limit: int = 100) -> dict:
    """Servers: name, model, serial, health status, power state, ROM and iLO firmware, the iLO address, enclosure bay.
    only_problems: the ones whose status is not OK."""
    flt = [f"status<>'OK'"] if only_problems else []
    if name_contains:
        if "'" in name_contains:
            raise c.ToolFailure("name_contains: no quotes")
        flt.append(f"name matches '%{name_contains}%'")
    rows = call(appliance, lambda ov: ov.server_hardware.get_all(start=0, count=c.limit_of(limit), filter=flt))
    return {"appliance": appliance, "count": len(rows), "servers": c.project(items(rows), SERVER_FIELDS)}


@server.tool(annotations=RO)
@c.tool
def ov_server(appliance: str, server_name: str) -> dict:
    """One server in detail: hardware, firmware, health, the iLO address, the profile assigned."""
    def read(ov):
        sh = ov.server_hardware.get_by_name(server_name)
        if sh is None:
            raise c.ToolFailure(f"no server named '{server_name}' on {appliance} (ov_server_hardware lists them)")
        return items(sh)[0]
    data = call(appliance, read)
    return {"appliance": appliance, "server": c.project([data], SERVER_FIELDS + [
        "partNumber", "formFactor", "generation", "intelligentProvisioningVersion", "licensingIntent", "uidState",
        "portMap", "subResources.LocalStorage", "subResources.Memory", "subResources.Processors"])[0]}


@server.tool(annotations=RO)
@c.tool
def ov_enclosures(appliance: str, limit: int = 50) -> dict:
    """Enclosures: name, model, serial, status, state, firmware, device bays and interconnect bays in use."""
    rows = call(appliance, lambda ov: ov.enclosures.get_all(start=0, count=c.limit_of(limit)))
    return {"appliance": appliance, "count": len(rows), "enclosures": c.project(items(rows), [
        "name", "model", "serialNumber", "status", "state", "enclosureType", "fwBaselineName", "isFwManaged",
        "deviceBayCount", "interconnectBayCount", "uidState", "uri"])}


@server.tool(annotations=RO)
@c.tool
def ov_interconnects(appliance: str, only_problems: bool = False, limit: int = 100) -> dict:
    """Interconnect modules: name, model, status, state, firmware, enclosure and bay."""
    flt = ["status<>'OK'"] if only_problems else []
    rows = call(appliance, lambda ov: ov.interconnects.get_all(start=0, count=c.limit_of(limit), filter=flt))
    return {"appliance": appliance, "count": len(rows), "interconnects": c.project(items(rows), [
        "name", "model", "productName", "status", "state", "firmwareVersion", "enclosureName", "interconnectLocation", "uri"])}


@server.tool(annotations=RO)
@c.tool
def ov_server_profiles(appliance: str, only_problems: bool = False, limit: int = 100) -> dict:
    """Server profiles: name, status, state, template compliance, the server it is assigned to, firmware baseline."""
    flt = ["status<>'OK'"] if only_problems else []
    rows = call(appliance, lambda ov: ov.server_profiles.get_all(start=0, count=c.limit_of(limit), filter=flt))
    return {"appliance": appliance, "count": len(rows), "profiles": c.project(items(rows), [
        "name", "status", "state", "templateCompliance", "serverHardwareUri", "serverProfileTemplateUri",
        "firmware.firmwareBaselineUri", "firmware.manageFirmware", "modified"])}


@server.tool(annotations=RO)
@c.tool
def ov_tasks(appliance: str, limit: int = 30, only_errors: bool = False) -> dict:
    """What was done recently on the appliance, newest first: task name, state, owner, resource, times
    (what changed before an incident)."""
    flt = ["taskState='Error'"] if only_errors else []
    rows = call(appliance, lambda ov: ov.tasks.get_all(start=0, count=c.limit_of(limit, 30), filter=flt, sort="created:descending"))
    return {"appliance": appliance, "count": len(rows), "tasks": c.project(items(rows), [
        "name", "taskState", "percentComplete", "owner", "created", "modified", "associatedResource.resourceName",
        "associatedResource.resourceCategory", "taskErrors"])}
