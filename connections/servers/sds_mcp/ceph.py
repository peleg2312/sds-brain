"""Ceph (Red Hat Ceph Storage 8 and 9, upstream Squid and Tentacle), read-only, through the Ceph Dashboard REST API of
the active manager: POST /api/auth for a token, then GET with the endpoint's media version
(Accept: application/vnd.ceph.api.v<x.y>+json, from ceph_api.json, generated from Ceph's own OpenAPI descriptions).

The account: a dashboard user with the built-in read-only role (`ceph dashboard ac-user-create <user> -i <file>
read-only`), reaching the manager's dashboard address (https, port 8443 by default)."""
import json
import os
import re
import threading
import time
from typing import Annotated

from . import common as c
from mcp.server.mcpserver import MCPServer

KIND = "ceph"
API = json.load(open(os.path.join(c.HERE, "ceph_api.json"), encoding="utf-8"))["paths"]
_TEMPLATES = [(re.compile("^" + re.sub(r"\\\{[^}]+\\\}", "[^/]+", re.escape(p)) + "$"), p) for p in API]

server = MCPServer("ceph", instructions=(
    "Read-only Ceph (Red Hat Ceph Storage 8 / 9) through the dashboard REST API of the active manager. Start with "
    "ceph_overview (one call: release, health checks, OSDs down or out, daemons not running, OSD flags, pools above 80%, "
    "capacity, active alerts, recent warnings in the cluster log), then narrow down: ceph_status, ceph_osds / ceph_osd, "
    "ceph_smart and ceph_devices for disks, ceph_pools, ceph_daemons, ceph_services, ceph_logs, ceph_alerts, ceph_metrics "
    "(Prometheus), ceph_perf_counters, the ceph_rgw_* tools for the object gateway, ceph_config for one option, "
    "ceph_api_get for any other dashboard read. Cluster names come from ceph_clusters. RGW keys are never returned. "
    "Nothing here changes the cluster. RHCS 8 is the Squid family."))
_sessions, _lock = {}, threading.Lock()


def template_of(path):
    """the API template a concrete path matches ("/api/osd/3" -> "/api/osd/{svc_id}"), or None"""
    return next((t for rx, t in _TEMPLATES if rx.match(path)), None)


class Cluster:
    def __init__(self, name):
        self.name, self.settings = name, c.target(KIND, name)
        url = self.settings.get("url") or ""
        if not url.startswith("https://"):
            raise c.ToolFailure(f"ceph '{name}': url must be https://<active manager>:8443 (the dashboard's address)")
        self.token = None
        self.client = c.ReadOnlyClient(url, self.settings)

    def login(self):
        user, password = c.credentials(KIND, self.name)
        self.client.allow = {("POST", "/api/auth")}
        r = self.client.request("POST", "/api/auth", json={"username": user, "password": password},
                                headers={"Accept": "application/vnd.ceph.api.v1.0+json", "Content-Type": "application/json"})
        self.client.allow = set()
        if r.status_code not in (200, 201) or not r.json().get("token"):
            raise c.api_error(r, f"ceph '{self.name}': sign-in failed")
        self.token = r.json()["token"]

    def get(self, path, params=None):
        if re.search(r"\.\.|%2e|%2f|%5c|\\", path, re.I):
            raise c.ToolFailure(f"{path}: no dot segments or encoded slashes")
        tpl = template_of(path.split("?", 1)[0])
        if not tpl:
            raise c.ToolFailure(f"{path} is not a dashboard read this server offers (ceph_api_get lists the families)")
        accept = f"application/vnd.ceph.api.v{API[tpl]['version']}+json"
        for attempt in (1, 2):
            if not self.token:
                self.login()
            r = self.client.request("GET", path, params=params, headers={"Accept": accept, "Authorization": "Bearer " + self.token})
            if r.status_code == 401 and attempt == 1:
                self.token = None
                continue
            if r.status_code != 200:
                raise c.api_error(r, f"ceph '{self.name}' GET {path}")
            return r.json() if r.content else None


def cluster(name):
    with _lock:
        if name not in _sessions:
            _sessions[name] = Cluster(name)
        return _sessions[name]


RO = c.read_only
ClusterName = Annotated[str, c.arg("The cluster's name in the inventory (ceph_clusters lists them), e.g. prod-a.")]
Limit = Annotated[int, c.arg("The most items to return.", ge=1, le=2000)]
OnlyProblems = Annotated[bool, c.arg("Only the items that are not healthy.")]
_LOGPRI = re.compile(r"WRN|ERR|warn|error", re.I)


@server.tool(title="List the clusters", annotations=RO("List the clusters"))
@c.tool
def ceph_clusters() -> dict:
    """The Ceph clusters in the inventory: names and dashboard addresses (no credentials). Use a name with every other tool."""
    return {"clusters": [{"name": n, "url": s.get("url")} for n, s in sorted(c.targets(KIND).items())]}


@server.tool(title="Cluster overview (triage)", annotations=RO("Cluster overview (triage)"))
@c.tool
def ceph_overview(cluster_name: ClusterName) -> dict:
    """One call for the state of a cluster, for a first look or a daily check: release, health status and checks, OSDs
    down or out, daemons not running, OSD flags (noout, norebalance...), pools above 80% used, raw capacity, active
    Prometheus alerts, and the last warnings and errors of the cluster log. A part that cannot be read says why."""
    cl = cluster(cluster_name)

    def health():
        h = cl.get("/api/health/minimal") or {}
        return {"health": h.get("health"), "pg_info": h.get("pg_info"), "scrub_status": h.get("scrub_status")}

    def osds():
        bad = [{"id": o.get("osd", o.get("id")), "host": c.pick(o, "host.name"), "up": o.get("up"), "in": o.get("in")}
               for o in cl.get("/api/osd") or [] if not (o.get("up") and o.get("in"))]
        return {"count": len(bad), "osds": bad[:50]}

    def daemons():
        ds = [d for d in cl.get("/api/daemon") or [] if d.get("status") != 1 and d.get("status_desc") != "running"]
        return {"count": len(ds), "daemons": c.project(ds[:50], ["daemon_name", "hostname", "status_desc", "version"])}

    def pools():
        rows = cl.get("/api/pool", params={"stats": "true"}) or []
        full = [{"pool": p.get("pool_name"), "percent_used": c.pick(p, "stats.percent_used.latest")} for p in rows
                if isinstance(c.pick(p, "stats.percent_used.latest"), (int, float)) and c.pick(p, "stats.percent_used.latest") >= 0.8]
        return sorted(full, key=lambda x: -x["percent_used"])

    def alerts():
        rows = cl.get("/api/prometheus") or []
        return {"count": len(rows), "alerts": c.project(rows[:20], ["labels.alertname", "labels.severity", "annotations.summary", "startsAt"])}

    def log():
        lines = (cl.get("/api/logs/all") or {}).get("clog") or []
        return [l for l in lines if _LOGPRI.search(str(l.get("priority", "")) if isinstance(l, dict) else str(l))][-20:]
    out = c.gather({"version": lambda: (cl.get("/api/summary") or {}).get("version"), "health": health, "osds_down_or_out": osds,
                    "daemons_not_running": daemons, "osd_flags": lambda: cl.get("/api/osd/flags"), "pools_over_80_percent": pools,
                    "capacity": lambda: cl.get("/api/health/get_cluster_capacity"), "active_alerts": alerts,
                    "recent_log_warnings": log})
    return {"cluster": cluster_name, **out}


@server.tool(title="Release and health checks", annotations=RO("Release and health checks"))
@c.tool
def ceph_status(cluster_name: ClusterName) -> dict:
    """Release, health status and each health check with its message (PG_DEGRADED, OSD_NEARFULL...), monitor quorum,
    OSD map, PG states and scrub status."""
    cl = cluster(cluster_name)
    summary = cl.get("/api/summary") or {}
    health = cl.get("/api/health/minimal") or {}
    return {"cluster": cluster_name, "version": summary.get("version"), "health": health.get("health"),
            "mon_status": c.pick(health, "mon_status"), "osd_map": c.pick(health, "osd_map"), "pg_info": health.get("pg_info"),
            "scrub_status": health.get("scrub_status"), "mgr_map": c.pick(health, "mgr_map")}


@server.tool(title="Raw capacity", annotations=RO("Raw capacity"))
@c.tool
def ceph_capacity(cluster_name: ClusterName) -> dict:
    """Raw cluster capacity: total, used and available bytes, and object counts (per pool: ceph_pools)."""
    return {"cluster": cluster_name, "capacity": cluster(cluster_name).get("/api/health/get_cluster_capacity")}


@server.tool(title="OSDs", annotations=RO("OSDs"))
@c.tool
def ceph_osds(cluster_name: ClusterName, only_problems: OnlyProblems = False,
              host: Annotated[str, c.arg("Only this host's OSDs.")] = "", limit: Limit = 200) -> dict:
    """OSDs: id, host, up / in, device class, state, capacity and use, read / write operations and latency."""
    rows = []
    for o in cluster(cluster_name).get("/api/osd") or []:
        row = {"id": o.get("osd", o.get("id")), "host": c.pick(o, "host.name"), "up": o.get("up"), "in": o.get("in"),
               "device_class": c.pick(o, "tree.device_class"), "state": o.get("state"),
               "stats": {k: c.pick(o, "stats." + k) for k in ("stat_bytes", "stat_bytes_used", "op_r", "op_w", "op_r_latency", "op_w_latency")}}
        if (only_problems and row["up"] and row["in"]) or (host and row["host"] != host):
            continue
        rows.append(row)
    return {"cluster": cluster_name, "count": len(rows), "osds": rows[:c.limit_of(limit, 200, 2000)]}


@server.tool(title="One OSD", annotations=RO("One OSD"))
@c.tool
def ceph_osd(cluster_name: ClusterName, osd_id: Annotated[int, c.arg("The OSD's id, e.g. 12.", ge=0)]) -> dict:
    """One OSD in detail: metadata (device, host, version), its place in the CRUSH tree, operation histograms."""
    return {"cluster": cluster_name, "osd": cluster(cluster_name).get(f"/api/osd/{int(osd_id)}")}


@server.tool(title="Disk SMART data", annotations=RO("Disk SMART data"))
@c.tool
def ceph_smart(cluster_name: ClusterName,
               osd_id: Annotated[int, c.arg("An OSD id: the SMART data of its device(s); -1 to use hostname instead.", ge=-1)] = -1,
               hostname: Annotated[str, c.arg("A host: the SMART data of all its devices (when osd_id is -1).")] = "") -> dict:
    """SMART data of an OSD's device or of every device on a host, as the manager's device health collects it:
    reallocated / pending sectors, wear, temperature, errors. A failing disk before Ceph marks it down."""
    if osd_id >= 0:
        return {"cluster": cluster_name, "osd": osd_id, "smart": cluster(cluster_name).get(f"/api/osd/{int(osd_id)}/smart")}
    if not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", hostname or ""):
        raise c.ToolFailure("give osd_id, or hostname (a host name)")
    return {"cluster": cluster_name, "host": hostname, "smart": cluster(cluster_name).get(f"/api/host/{hostname}/smart")}


@server.tool(title="A host's devices", annotations=RO("A host's devices"))
@c.tool
def ceph_devices(cluster_name: ClusterName, hostname: Annotated[str, c.arg("The host's name as the orchestrator knows it (ceph_hosts).")]) -> dict:
    """A host's storage devices: device id, the daemons on it, location, life expectancy where known."""
    if not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", hostname or ""):
        raise c.ToolFailure("hostname: a host name")
    return {"cluster": cluster_name, "host": hostname, "devices": cluster(cluster_name).get(f"/api/host/{hostname}/devices")}


@server.tool(title="Pools", annotations=RO("Pools"))
@c.tool
def ceph_pools(cluster_name: ClusterName) -> dict:
    """Pools: name, type, size / min_size, PGs and autoscale, CRUSH rule, erasure-code profile, application, quotas,
    bytes used, available, percent used (0 to 1), objects."""
    pools = cluster(cluster_name).get("/api/pool", params={"stats": "true"}) or []
    keep = ["pool_name", "type", "size", "min_size", "pg_num", "pg_placement_num", "pg_autoscale_mode", "crush_rule",
            "erasure_code_profile", "application_metadata", "quota_max_bytes", "quota_max_objects",
            "stats.bytes_used.latest", "stats.max_avail.latest", "stats.percent_used.latest", "stats.objects.latest"]
    return {"cluster": cluster_name, "count": len(pools), "pools": c.project(pools, keep)}


@server.tool(title="Hosts", annotations=RO("Hosts"))
@c.tool
def ceph_hosts(cluster_name: ClusterName) -> dict:
    """Hosts the orchestrator manages: name, address, labels, status, the services on each, Ceph version."""
    hosts = cluster(cluster_name).get("/api/host") or []
    return {"cluster": cluster_name, "count": len(hosts),
            "hosts": c.project(hosts, ["hostname", "addr", "labels", "status", "service_type", "services", "ceph_version", "sources"])}


@server.tool(title="Orchestrator services", annotations=RO("Orchestrator services"))
@c.tool
def ceph_services(cluster_name: ClusterName,
                  service_name: Annotated[str, c.arg("Only this service, e.g. rgw.main.")] = "") -> dict:
    """cephadm services: name, type, placement, daemons running of expected, image and last refresh."""
    svcs = cluster(cluster_name).get("/api/service", params={"service_name": service_name} if service_name else None) or []
    return {"cluster": cluster_name, "count": len(svcs),
            "services": c.project(svcs, ["service_name", "service_type", "placement", "status.running", "status.size", "status.last_refresh",
                                         "status.container_image_name", "status.container_image_id"])}


@server.tool(title="Daemons", annotations=RO("Daemons"))
@c.tool
def ceph_daemons(cluster_name: ClusterName,
                 daemon_type: Annotated[str, c.arg("Only this type: osd, mon, mgr, rgw, mds, crash, node-exporter...")] = "",
                 only_problems: OnlyProblems = False, limit: Limit = 200) -> dict:
    """cephadm daemons: name, host, status, version, image and digest, last refresh, start time."""
    ds = cluster(cluster_name).get("/api/daemon", params={"daemon_types": daemon_type} if daemon_type else None) or []
    rows = c.project(ds, ["daemon_name", "daemon_type", "hostname", "status", "status_desc", "version", "container_image_name",
                          "container_image_digests", "last_refresh", "started"])
    if only_problems:
        rows = [r for r in rows if r.get("status") != 1 and r.get("status_desc") != "running"]
    return {"cluster": cluster_name, "count": len(rows), "daemons": rows[:c.limit_of(limit, 200, 2000)]}


@server.tool(title="Cluster or audit log", annotations=RO("Cluster or audit log"))
@c.tool
def ceph_logs(cluster_name: ClusterName,
              which: Annotated[str, c.arg("clog: the cluster log (default); audit: who ran which command.", pattern="^(clog|audit)$")] = "clog",
              only_warnings: Annotated[bool, c.arg("Only warning and error entries.")] = False,
              limit: Limit = 50) -> dict:
    """The newest entries of the cluster log or the audit log (the audit log shows commands run against the cluster:
    what changed before an incident)."""
    lines = (cluster(cluster_name).get("/api/logs/all") or {}).get("clog" if which == "clog" else "audit_log") or []
    if only_warnings:
        lines = [l for l in lines if _LOGPRI.search(str(l.get("priority", "")) if isinstance(l, dict) else str(l))]
    return {"cluster": cluster_name, "log": which, "entries": lines[-c.limit_of(limit, 50, 1000):]}


@server.tool(title="Active alerts", annotations=RO("Active alerts"))
@c.tool
def ceph_alerts(cluster_name: ClusterName) -> dict:
    """Active Prometheus alerts as the dashboard sees them: name, severity, instance, summary, description, since when
    (needs the dashboard's Alertmanager address set). Ceph's own health checks: ceph_status."""
    alerts = cluster(cluster_name).get("/api/prometheus") or []
    return {"cluster": cluster_name, "count": len(alerts),
            "alerts": c.project(alerts, ["labels.alertname", "labels.severity", "labels.instance", "annotations.summary",
                                         "annotations.description", "status.state", "startsAt"])}


@server.tool(title="Prometheus query", annotations=RO("Prometheus query"))
@c.tool
def ceph_metrics(cluster_name: ClusterName,
                 query: Annotated[str, c.arg("A Prometheus expression, e.g. ceph_health_status, ceph_osd_apply_latency_ms, "
                                             "rate(ceph_rgw_req[5m]), ceph_pool_percent_used.", max_length=1000)],
                 minutes: Annotated[int, c.arg("0: the value now; N: a series over the last N minutes.", ge=0, le=10080)] = 0,
                 step_seconds: Annotated[int, c.arg("Seconds between points of a series.", ge=15, le=3600)] = 60,
                 limit: Annotated[int, c.arg("The most series to return.", ge=1, le=500)] = 50) -> dict:
    """A Prometheus query through the dashboard (the cluster's own Prometheus, the one the dashboard's graphs use), now
    or over a period; at most 1000 points per series. Needs the dashboard's Prometheus address set
    (ceph dashboard set-prometheus-api-host)."""
    if not query.strip():
        raise c.ToolFailure("query: a Prometheus expression")
    minutes, step = int(minutes or 0), int(step_seconds or 60)
    if minutes and minutes * 60 / step > 1000:
        step = int(minutes * 60 / 1000) + 1
    end = int(time.time())
    data = cluster(cluster_name).get("/api/prometheus/data", params={"params": query, "start": end - minutes * 60, "end": end, "step": step})
    result = (data or {}).get("result", data) if isinstance(data, dict) else data
    result = result if isinstance(result, list) else [result]
    return {"cluster": cluster_name, "query": query, "minutes": minutes, "step_seconds": step, "series": len(result),
            "result": result[:c.limit_of(limit, 50)]}


@server.tool(title="A daemon's performance counters", annotations=RO("A daemon's performance counters"))
@c.tool
def ceph_perf_counters(cluster_name: ClusterName,
                       daemon_type: Annotated[str, c.arg("osd, mon, mgr, rgw, mds, rbd-mirror or tcmu-runner.",
                                                         pattern="^(osd|mon|mgr|rgw|mds|rbd-mirror|tcmu-runner)$")],
                       daemon_id: Annotated[str, c.arg("The daemon's id: 12 for osd.12, the name for rgw / mds.", pattern=r"^[A-Za-z0-9_.-]{1,100}$")]) -> dict:
    """One daemon's performance counters (operation counts, latencies, queue lengths), as the dashboard reads them."""
    return {"cluster": cluster_name, "daemon": f"{daemon_type}.{daemon_id}",
            "counters": cluster(cluster_name).get(f"/api/perf_counters/{daemon_type}/{daemon_id}")}


@server.tool(title="RGW daemons", annotations=RO("RGW daemons"))
@c.tool
def ceph_rgw_daemons(cluster_name: ClusterName) -> dict:
    """RGW daemons: id, host, zone / zonegroup / realm, version and port."""
    return {"cluster": cluster_name, "daemons": cluster(cluster_name).get("/api/rgw/daemon")}


@server.tool(title="RGW multisite sync", annotations=RO("RGW multisite sync"))
@c.tool
def ceph_rgw_sync_status(cluster_name: ClusterName) -> dict:
    """RGW multisite sync status: metadata and data sync per zone, shards behind, oldest change not applied."""
    return {"cluster": cluster_name, "sync_status": cluster(cluster_name).get("/api/rgw/multisite/sync_status")}


@server.tool(title="RGW buckets", annotations=RO("RGW buckets"))
@c.tool
def ceph_rgw_buckets(cluster_name: ClusterName,
                     uid: Annotated[str, c.arg("Only this RGW user's buckets (tenant$user for a tenanted user).")] = "",
                     limit: Annotated[int, c.arg("The most buckets to return.", ge=1, le=2000)] = 100) -> dict:
    """RGW buckets with usage: bucket, tenant, owner, zonegroup, placement, shards, objects, size, quota, versioning,
    object lock, creation time."""
    params = {"stats": "true", **({"uid": uid} if uid else {})}
    buckets = cluster(cluster_name).get("/api/rgw/bucket", params=params) or []
    rows = c.project(buckets if isinstance(buckets, list) else [buckets], [
        "bucket", "tenant", "owner", "zonegroup", "placement_rule", "num_shards", "usage.rgw.main.num_objects",
        "usage.rgw.main.size_actual", "bucket_quota", "versioning", "lock_enabled", "creation_time"])
    return {"cluster": cluster_name, "count": len(rows), "buckets": rows[:c.limit_of(limit, 100, 2000)]}


@server.tool(title="One RGW bucket", annotations=RO("One RGW bucket"))
@c.tool
def ceph_rgw_bucket(cluster_name: ClusterName,
                    bucket: Annotated[str, c.arg("The bucket's name.", pattern=r"^[A-Za-z0-9._-]{3,255}$")]) -> dict:
    """One RGW bucket in detail: owner, placement, index shards, usage per category, quota, versioning, object lock,
    lifecycle and policy where the dashboard returns them."""
    return {"cluster": cluster_name, "bucket": cluster(cluster_name).get(f"/api/rgw/bucket/{bucket}")}


@server.tool(title="One RGW user", annotations=RO("One RGW user"))
@c.tool
def ceph_rgw_user(cluster_name: ClusterName,
                  uid: Annotated[str, c.arg("The RGW user id (tenant$user for a tenanted user).", pattern=r"^[A-Za-z0-9_.@$:-]{1,128}$")]) -> dict:
    """One RGW user's settings: suspended, max buckets, user and bucket quotas, caps, default placement. Keys are never
    returned."""
    user = cluster(cluster_name).get(f"/api/rgw/user/{uid}") or {}
    for k in ("keys", "swift_keys", "access_keys"):
        user.pop(k, None)
    return {"cluster": cluster_name, "user": user}


@server.tool(title="One configuration option", annotations=RO("One configuration option"))
@c.tool
def ceph_config(cluster_name: ClusterName,
                option: Annotated[str, c.arg("A configuration option name, e.g. osd_max_backfills.", pattern=r"^[a-z0-9_]{2,100}$")]) -> dict:
    """One configuration option: its value per section (global, osd, client.rgw...), default and description."""
    return {"cluster": cluster_name, "option": cluster(cluster_name).get(f"/api/cluster_conf/{option}")}


@server.tool(title="Other dashboard reads", annotations=RO("Other dashboard reads"))
@c.tool
def ceph_api_get(cluster_name: ClusterName,
                 path: Annotated[str, c.arg("A dashboard API read, e.g. /api/crush_rule, /api/osd/flags, /api/rgw/zonegroup, "
                                            "/api/monitor, /api/cluster/upgrade/status. Empty: the list of families.")] = "",
                 limit: Limit = 100) -> dict:
    """Any other read of the dashboard API, among those Ceph's API description lists (credential holders excluded).
    Lists are cut to limit; key material is never returned."""
    if not path:
        return {"families": sorted({"/".join(p.split("/")[:3]) for p in API}), "note": "pass a full path, e.g. /api/crush_rule or /api/osd/3"}
    path = "/" + path.strip().lstrip("/")
    data = cluster(cluster_name).get(path)
    if isinstance(data, list):
        return {"cluster": cluster_name, "path": path, "count": len(data), "items": data[:c.limit_of(limit, 100, 2000)]}
    return {"cluster": cluster_name, "path": path, "data": data}
