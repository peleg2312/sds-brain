"""HPE iLO (4, 5, 6), read-only, through HPE's own Python library (python-ilorest-library, import redfish) and the Redfish
API: a session per call (iLO has few session slots, so every call signs out again), GET only. The library's
connection is wrapped so that nothing but GET, the session sign-in and its sign-out can be sent.

Certificate verification is required: give the inventory a ca_file (a CA that signed the iLO certificates) or the
server's certificate fingerprint (SHA-256), per server or in "defaults". The account: an iLO user with the Read Only
role (the Login privilege only), the same on every server or one per server."""
import re

from . import common as c
from mcp.server.mcpserver import MCPServer

KIND = "ilo"
DENY = re.compile(r"^/redfish/v1/(AccountService|SessionService|CertificateService|Managers/[^/]+/SecurityService)", re.I)

server = MCPServer("ilo", instructions=(
    "Read-only HPE iLO (Redfish). Start with ilo_servers; ilo_summary for model, serial, power, health, BIOS and iLO "
    "firmware; ilo_logs for the IML (hardware events) or IEL (iLO events); ilo_storage for controllers and drives; "
    "ilo_thermal / ilo_power for fans, temperatures and power supplies; ilo_firmware for the firmware inventory; "
    "ilo_get for any other Redfish read. Nothing here changes a server (no power, reset or setting operation exists)."))


def connect(name):
    import urllib3
    import redfish
    settings = c.target(KIND, name)
    host = settings.get("host") or ""
    if not host or "/" in host:
        raise c.ToolFailure(f"ilo '{name}': host must be the iLO's name or address (no scheme)")
    if settings.get("insecure") or settings.get("verify") is False:
        raise c.ToolFailure("certificate verification cannot be switched off")
    ca, pin = c.ca_file(settings), settings.get("fingerprint") or ""
    if not ca and not pin:
        raise c.ToolFailure(f"ilo '{name}': give ca_file or fingerprint (SHA-256 of the iLO certificate) in the inventory: "
                            "the library does not verify the certificate otherwise")
    user, password = c.credentials(KIND, name)
    cert = {"ca_certs": ca} if ca else {"fingerprint": pin}
    cl = redfish.RedfishClient(base_url=f"https://{host}", username=user, password=password, auth="session", ca_cert_data=cert,
                               timeout=urllib3.util.Timeout(connect=10, read=60), retries=urllib3.util.Retry(total=1, redirect=0))
    guard(cl)
    return cl


def guard(cl):
    """every request goes through connection.rest_request: GET, plus POST to the sessions collection (sign-in) and DELETE
    of our own session (sign-out); anything else refused"""
    conn = cl.connection
    send = conn.rest_request

    def read_only(path, method="GET", args=None, body=None, headers=None):
        m, p = method.upper(), str(path).split("?", 1)[0].rstrip("/")
        ok = m == "GET" or (m == "POST" and p.endswith("/SessionService/Sessions")) or \
            (m == "DELETE" and "/SessionService/Sessions/" in p and cl.session_location and p.endswith(str(cl.session_location).rstrip("/").split("/redfish", 1)[-1]))
        if not ok:
            raise c.ReadOnlyViolation(f"{method} {path} refused: this server only reads")
        return send(path, method=method, args=args, body=body, headers=headers)
    conn.rest_request = read_only


def path_only(cl):
    """keep the session's address as a path: the library rebuilds it wrongly when the iLO is not on port 443, and the
    sign-out (which frees one of the iLO's few session slots) would then miss"""
    from urllib.parse import urlparse
    loc = getattr(cl, "_session_location", None)
    if loc and urlparse(loc).path:
        cl._session_location = urlparse(loc).path


def session(name, fn):
    """sign in, read, always sign out"""
    cl = connect(name)
    try:
        cl.login(auth="session")
    except Exception as e:
        raise c.ToolFailure(f"ilo '{name}': sign-in failed ({e.__class__.__name__}: {str(e)[:200]})")
    path_only(cl)
    try:
        return fn(cl)
    finally:
        try:
            cl.logout()
        except Exception:
            pass


def get(cl, path):
    r = cl.get(path)
    if r.status != 200:
        raise c.ToolFailure(f"GET {path}: HTTP {r.status}")
    return r.dict


def members(cl, path, expand=True):
    """a collection's members, read one by one when $expand is not honoured"""
    col = get(cl, path + ("?$expand=." if expand else ""))
    out = []
    for m in col.get("Members") or []:
        out.append(m if len(m) > 1 else get(cl, m["@odata.id"]))
    return out


def first(cl, collection):
    ms = get(cl, collection).get("Members") or []
    if not ms:
        raise c.ToolFailure(f"{collection} has no members")
    return ms[0]["@odata.id"]


RO = c.read_only()


@server.tool(annotations=RO)
@c.tool
def ilo_servers(name_contains: str = "") -> dict:
    """The servers in the inventory and their iLO addresses (no credentials)."""
    rows = [{"name": n, "ilo": s.get("host")} for n, s in sorted(c.targets(KIND).items()) if name_contains.lower() in n.lower()]
    return {"count": len(rows), "servers": rows[:500]}


@server.tool(annotations=RO)
@c.tool
def ilo_summary(server_name: str) -> dict:
    """Model, serial, power state, health (aggregate and per subsystem), BIOS version, POST state, memory and processors,
    and the iLO's own model and firmware."""
    def read(cl):
        system = get(cl, first(cl, "/redfish/v1/Systems"))
        manager = get(cl, first(cl, "/redfish/v1/Managers"))
        hpe = c.pick(system, "Oem.Hpe") or c.pick(system, "Oem.Hp") or {}
        return {"system": {k: system.get(k) for k in ("Model", "Manufacturer", "SerialNumber", "SKU", "HostName", "PowerState", "BiosVersion", "Status", "IndicatorLED")}
                | {"ProcessorSummary": system.get("ProcessorSummary"), "MemorySummary": system.get("MemorySummary"),
                   "PostState": c.pick(hpe, "PostState"), "AggregateHealthStatus": hpe.get("AggregateHealthStatus")},
                "ilo": {k: manager.get(k) for k in ("Model", "FirmwareVersion", "Status", "DateTime")}}
    return dict(session(server_name, read), server=server_name)


@server.tool(annotations=RO)
@c.tool
def ilo_logs(server_name: str, log: str = "IML", limit: int = 30, only_problems: bool = False) -> dict:
    """The newest log entries: IML (the server's hardware events: drives, memory, fans, power) or IEL (the iLO's own
    events: logins, resets, firmware). only_problems: entries whose severity is not OK."""
    paths = {"IML": "/redfish/v1/Systems/1/LogServices/IML/Entries", "IEL": "/redfish/v1/Managers/1/LogServices/IEL/Entries"}
    if log.upper() not in paths:
        raise c.ToolFailure("log: IML or IEL")

    def read(cl):
        entries = members(cl, paths[log.upper()])
        rows = [{k: e.get(k) for k in ("Created", "Severity", "Message", "EntryType")} | {
                    "Class": c.pick(e, "Oem.Hpe.Class"), "Code": c.pick(e, "Oem.Hpe.Code"), "Count": c.pick(e, "Oem.Hpe.Count"),
                    "Repaired": c.pick(e, "Oem.Hpe.Repaired"), "Updated": c.pick(e, "Oem.Hpe.Updated")} for e in entries]
        if only_problems:
            rows = [r for r in rows if str(r.get("Severity") or "").lower() not in ("ok", "")]
        rows.sort(key=lambda r: str(r.get("Updated") or r.get("Created") or ""), reverse=True)
        return {"log": log.upper(), "total": len(rows), "entries": rows[:c.limit_of(limit, 30)]}
    return dict(session(server_name, read), server=server_name)


@server.tool(annotations=RO)
@c.tool
def ilo_storage(server_name: str) -> dict:
    """Storage controllers, their volumes and drives: model, firmware, health, drive serial, capacity, media,
    location (bay) and predicted failure. Redfish Storage (iLO 6, newer iLO 5) and SmartStorage (iLO 5)."""
    def read(cl):
        system = first(cl, "/redfish/v1/Systems")
        out = {"controllers": []}
        try:
            for st in members(cl, system + "/Storage"):
                drives = [get(cl, d["@odata.id"]) for d in (st.get("Drives") or [])]
                out["controllers"].append({
                    "Id": st.get("Id"), "Name": st.get("Name"), "Status": st.get("Status"),
                    "Controllers": [{k: x.get(k) for k in ("Model", "FirmwareVersion", "Status", "SerialNumber")} for x in (st.get("StorageControllers") or [])],
                    "Drives": [{k: d.get(k) for k in ("Id", "Model", "SerialNumber", "CapacityBytes", "MediaType", "Protocol", "Status", "FailurePredicted", "PhysicalLocation")} for d in drives]})
        except c.ToolFailure:
            pass
        if not out["controllers"]:                                    # iLO 5 without Redfish Storage: SmartStorage
            for ac in members(cl, system + "/SmartStorage/ArrayControllers"):
                pds = members(cl, ac["@odata.id"].rstrip("/") + "/DiskDrives") if ac.get("@odata.id") else []
                out["controllers"].append({
                    "Model": ac.get("Model"), "Location": ac.get("Location"), "FirmwareVersion": c.pick(ac, "FirmwareVersion.Current.VersionString"),
                    "Status": ac.get("Status"),
                    "Drives": [{k: d.get(k) for k in ("Location", "Model", "SerialNumber", "CapacityMiB", "MediaType", "Status", "FirmwareVersion", "SSDEnduranceUtilizationPercentage")} for d in pds]})
        return out
    return dict(session(server_name, read), server=server_name)


@server.tool(annotations=RO)
@c.tool
def ilo_thermal(server_name: str, only_problems: bool = False) -> dict:
    """Fans and temperature sensors with readings, thresholds and health."""
    def read(cl):
        th = get(cl, first(cl, "/redfish/v1/Chassis") + "/Thermal")
        fans = [{k: f.get(k) for k in ("Name", "FanName", "Reading", "ReadingUnits", "Status")} for f in th.get("Fans") or []]
        temps = [{k: t.get(k) for k in ("Name", "ReadingCelsius", "UpperThresholdCritical", "UpperThresholdFatal", "PhysicalContext", "Status")} for t in th.get("Temperatures") or []]
        if only_problems:
            bad = lambda x: str(c.pick(x, "Status.Health") or "OK") != "OK"
            fans, temps = [f for f in fans if bad(f)], [t for t in temps if bad(t)]
        return {"fans": fans, "temperatures": temps}
    return dict(session(server_name, read), server=server_name)


@server.tool(annotations=RO)
@c.tool
def ilo_power(server_name: str) -> dict:
    """Power supplies (model, serial, firmware, capacity, health) and the current power draw."""
    def read(cl):
        pw = get(cl, first(cl, "/redfish/v1/Chassis") + "/Power")
        return {"power_control": [{k: p.get(k) for k in ("PowerConsumedWatts", "PowerCapacityWatts")} for p in pw.get("PowerControl") or []],
                "supplies": [{k: s.get(k) for k in ("Name", "Model", "SerialNumber", "FirmwareVersion", "PowerCapacityWatts", "LastPowerOutputWatts", "LineInputVoltage", "Status")} for s in pw.get("PowerSupplies") or []]}
    return dict(session(server_name, read), server=server_name)


@server.tool(annotations=RO)
@c.tool
def ilo_firmware(server_name: str) -> dict:
    """The firmware inventory: every component's name and version (BIOS, iLO, controllers, drives, NICs, power)."""
    def read(cl):
        items = members(cl, "/redfish/v1/UpdateService/FirmwareInventory")
        return {"firmware": [{k: i.get(k) for k in ("Name", "Version", "Updateable", "Status")} | {"DeviceContext": c.pick(i, "Oem.Hpe.DeviceContext")} for i in items]}
    return dict(session(server_name, read), server=server_name)


@server.tool(annotations=RO)
@c.tool
def ilo_get(server_name: str, path: str) -> dict:
    """Any other Redfish read under /redfish/v1/ (e.g. /redfish/v1/Systems/1/Memory, /redfish/v1/Chassis/1/NetworkAdapters).
    Accounts, sessions, certificates and security settings are not offered."""
    path = "/" + (path or "").strip().lstrip("/")
    if not path.startswith("/redfish/v1") or re.search(r"\.\.|%2e|%2f|\\", path, re.I) or DENY.match(path):
        raise c.ToolFailure("path: a Redfish resource under /redfish/v1/ (not accounts, sessions, certificates or security)")
    return {"server": server_name, "path": path, "data": session(server_name, lambda cl: get(cl, path))}
