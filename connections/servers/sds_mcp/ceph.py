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

from . import common as c
from mcp.server.mcpserver import MCPServer

KIND = "ceph"
API = json.load(open(os.path.join(c.HERE, "ceph_api.json"), encoding="utf-8"))["paths"]
_TEMPLATES = [(re.compile("^" + re.sub(r"\\\{[^}]+\\\}", "[^/]+", re.escape(p)) + "$"), p) for p in API]

server = MCPServer("ceph", instructions=(
    "Read-only Ceph through the dashboard REST API of the active manager. Start with ceph_clusters, then ceph_status "
    "(release, health status and checks); ceph_alerts (Prometheus alerts), ceph_metrics (Prometheus queries); ceph_osds, ceph_pools, ceph_capacity, ceph_hosts, ceph_services and the "
    "ceph_rgw_* tools narrow it down; ceph_logs gives the cluster log; ceph_api_get reaches any other dashboard read. "
    "RGW user keys are never returned. Nothing here changes the cluster. RHCS 8 is the Squid family."))
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


RO = c.read_only()


@server.tool(annotations=RO)
@c.tool
def ceph_clusters() -> dict:
    """The Ceph clusters in the inventory (names and dashboard addresses only)."""
    return {"clusters": [{"name": n, "url": s.get("url")} for n, s in sorted(c.targets(KIND).items())]}


@server.tool(annotations=RO)
@c.tool
def ceph_status(cluster_name: str) -> dict:
    """Release, health status and the health checks with their messages (the first look at a warning)."""
    cl = cluster(cluster_name)
    summary = cl.get("/api/summary") or {}
    health = cl.get("/api/health/minimal") or {}
    return {"cluster": cluster_name, "version": summary.get("version"), "health": health.get("health"),
            "mon_status": c.pick(health, "mon_status"), "osd_map": c.pick(health, "osd_map"), "pg_info": health.get("pg_info"),
            "scrub_status": health.get("scrub_status"), "mgr_map": c.pick(health, "mgr_map")}


@server.tool(annotations=RO)
@c.tool
def ceph_capacity(cluster_name: str) -> dict:
    """Raw cluster capacity: total, used and available bytes and objects."""
    return {"cluster": cluster_name, "capacity": cluster(cluster_name).get("/api/health/get_cluster_capacity")}


@server.tool(annotations=RO)
@c.tool
def ceph_osds(cluster_name: str, only_problems: bool = False, host: str = "", limit: int = 200) -> dict:
    """OSDs: id, host, up / in, device class, usage and latency. only_problems: the OSDs that are down or out."""
    osds = cluster(cluster_name).get("/api/osd") or []
    rows = []
    for o in osds:
        row = {"id": o.get("osd", o.get("id")), "host": c.pick(o, "host.name"), "up": o.get("up"), "in": o.get("in"),
               "device_class": c.pick(o, "tree.device_class"), "state": o.get("state"),
               "stats": {k: c.pick(o, "stats." + k) for k in ("stat_bytes", "stat_bytes_used", "op_r", "op_w", "op_r_latency", "op_w_latency")}}
        if only_problems and row["up"] and row["in"]:
            continue
        if host and row["host"] != host:
            continue
        rows.append(row)
    return {"cluster": cluster_name, "count": len(rows), "osds": rows[:c.limit_of(limit, 200, 2000)]}


@server.tool(annotations=RO)
@c.tool
def ceph_osd(cluster_name: str, osd_id: int) -> dict:
    """One OSD in detail (metadata, histogram summaries, smart data where the dashboard has them)."""
    return {"cluster": cluster_name, "osd": cluster(cluster_name).get(f"/api/osd/{int(osd_id)}")}


@server.tool(annotations=RO)
@c.tool
def ceph_pools(cluster_name: str) -> dict:
    """Pools: name, type, size / min_size, PGs and autoscale, CRUSH rule, application, usage."""
    pools = cluster(cluster_name).get("/api/pool", params={"stats": "true"}) or []
    keep = ["pool_name", "type", "size", "min_size", "pg_num", "pg_placement_num", "pg_autoscale_mode", "crush_rule",
            "erasure_code_profile", "application_metadata", "quota_max_bytes", "quota_max_objects",
            "stats.bytes_used.latest", "stats.max_avail.latest", "stats.percent_used.latest", "stats.objects.latest"]
    return {"cluster": cluster_name, "count": len(pools), "pools": c.project(pools, keep)}


@server.tool(annotations=RO)
@c.tool
def ceph_hosts(cluster_name: str) -> dict:
    """Hosts known to the orchestrator, with their labels, status and services."""
    hosts = cluster(cluster_name).get("/api/host") or []
    return {"cluster": cluster_name, "count": len(hosts),
            "hosts": c.project(hosts, ["hostname", "addr", "labels", "status", "service_type", "services", "ceph_version", "sources"])}


@server.tool(annotations=RO)
@c.tool
def ceph_services(cluster_name: str, service_name: str = "") -> dict:
    """Orchestrator services (cephadm): name, type, placement and how many daemons run of how many expected."""
    svcs = cluster(cluster_name).get("/api/service", params={"service_name": service_name} if service_name else None) or []
    return {"cluster": cluster_name, "count": len(svcs),
            "services": c.project(svcs, ["service_name", "service_type", "placement", "status.running", "status.size", "status.last_refresh", "status.container_image_name", "status.container_image_id"])}


@server.tool(annotations=RO)
@c.tool
def ceph_daemons(cluster_name: str, daemon_type: str = "", only_problems: bool = False, limit: int = 200) -> dict:
    """Daemons (cephadm): name, host, status, version and image; only_problems: the ones not running."""
    ds = cluster(cluster_name).get("/api/daemon", params={"daemon_types": daemon_type} if daemon_type else None) or []
    rows = c.project(ds, ["daemon_name", "daemon_type", "hostname", "status", "status_desc", "version", "container_image_name", "container_image_digests", "last_refresh", "started"])
    if only_problems:
        rows = [r for r in rows if r.get("status") != 1 and r.get("status_desc") != "running"]
    return {"cluster": cluster_name, "count": len(rows), "daemons": rows[:c.limit_of(limit, 200, 2000)]}


@server.tool(annotations=RO)
@c.tool
def ceph_logs(cluster_name: str, which: str = "clog", limit: int = 50) -> dict:
    """The newest entries of the cluster log (clog) or the audit log (audit)."""
    logs = cluster(cluster_name).get("/api/logs/all") or {}
    key = {"clog": "clog", "audit": "audit_log"}.get(which)
    if not key:
        raise c.ToolFailure("which: clog or audit")
    lines = logs.get(key) or []
    return {"cluster": cluster_name, "log": which, "entries": lines[-c.limit_of(limit, 50, 1000):]}


@server.tool(annotations=RO)
@c.tool
def ceph_alerts(cluster_name: str) -> dict:
    """Active Prometheus alerts as the dashboard sees them (needs Alertmanager configured for the dashboard)."""
    alerts = cluster(cluster_name).get("/api/prometheus") or []
    return {"cluster": cluster_name, "count": len(alerts),
            "alerts": c.project(alerts, ["labels.alertname", "labels.severity", "labels.instance", "annotations.summary", "annotations.description", "status.state", "startsAt"])}


@server.tool(annotations=RO)
@c.tool
def ceph_rgw_daemons(cluster_name: str) -> dict:
    """RGW daemons: id, host, zone / zonegroup / realm, version and port."""
    return {"cluster": cluster_name, "daemons": cluster(cluster_name).get("/api/rgw/daemon")}


@server.tool(annotations=RO)
@c.tool
def ceph_rgw_sync_status(cluster_name: str) -> dict:
    """RGW multisite sync status (metadata and data sync per zone)."""
    return {"cluster": cluster_name, "sync_status": cluster(cluster_name).get("/api/rgw/multisite/sync_status")}


@server.tool(annotations=RO)
@c.tool
def ceph_rgw_buckets(cluster_name: str, uid: str = "", limit: int = 100) -> dict:
    """RGW buckets with usage (bucket, owner, zonegroup, objects, size, quota, versioning, lock); uid: one user's only."""
    params = {"stats": "true", **({"uid": uid} if uid else {})}
    buckets = cluster(cluster_name).get("/api/rgw/bucket", params=params) or []
    rows = c.project(buckets if isinstance(buckets, list) else [buckets], [
        "bucket", "tenant", "owner", "zonegroup", "placement_rule", "num_shards", "usage.rgw.main.num_objects",
        "usage.rgw.main.size_actual", "bucket_quota", "versioning", "lock_enabled", "creation_time"])
    return {"cluster": cluster_name, "count": len(rows), "buckets": rows[:c.limit_of(limit, 100, 2000)]}


@server.tool(annotations=RO)
@c.tool
def ceph_rgw_user(cluster_name: str, uid: str) -> dict:
    """One RGW user's settings (suspended, max buckets, quotas, caps, placement); keys are never returned."""
    if not re.fullmatch(r"[A-Za-z0-9_.@$:-]{1,128}", uid or ""):
        raise c.ToolFailure("uid: the RGW user id (tenant$user for a tenanted user)")
    user = cluster(cluster_name).get(f"/api/rgw/user/{uid}") or {}
    for k in ("keys", "swift_keys", "access_keys"):
        user.pop(k, None)
    return {"cluster": cluster_name, "user": user}


@server.tool(annotations=RO)
@c.tool
def ceph_config(cluster_name: str, option: str) -> dict:
    """One configuration option: its value per section (global, osd, client.rgw...) and its description."""
    if not re.fullmatch(r"[a-z0-9_]{2,100}", option or ""):
        raise c.ToolFailure("option: a configuration option name, e.g. osd_max_backfills")
    return {"cluster": cluster_name, "option": cluster(cluster_name).get(f"/api/cluster_conf/{option}")}


@server.tool(annotations=RO)
@c.tool
def ceph_api_get(cluster_name: str, path: str = "", limit: int = 100) -> dict:
    """Any other read of the dashboard API (e.g. /api/crush_rule, /api/rgw/zonegroup, /api/monitor, /api/osd/flags).
    Without a path: the families of reads available. Lists are cut to `limit`; key material is never returned."""
    if not path:
        families = sorted({"/".join(p.split("/")[:3]) for p in API})
        return {"families": families, "note": "pass a full path, e.g. /api/crush_rule or /api/osd/3"}
    path = "/" + path.strip().lstrip("/")
    data = cluster(cluster_name).get(path)
    if isinstance(data, list):
        return {"cluster": cluster_name, "path": path, "count": len(data), "items": data[:c.limit_of(limit, 100, 2000)]}
    return {"cluster": cluster_name, "path": path, "data": data}


@server.tool(annotations=RO)
@c.tool
def ceph_metrics(cluster_name: str, query: str, minutes: int = 0, step_seconds: int = 60, limit: int = 50) -> dict:
    """A Prometheus query through the dashboard (the cluster's own Prometheus, the one the dashboard's graphs use), e.g.
    ceph_health_status, ceph_osd_apply_latency_ms, rate(ceph_rgw_req[5m]), ceph_pool_percent_used.
    minutes=0: the value now; minutes=N: a series over the last N minutes, one point every step_seconds.
    Needs the dashboard's Prometheus API host set (ceph dashboard set-prometheus-api-host)."""
    if not query.strip() or len(query) > 1000:
        raise c.ToolFailure("query: a Prometheus expression, 1000 characters at most")
    minutes, step = max(0, min(int(minutes or 0), 7 * 24 * 60)), max(15, min(int(step_seconds or 60), 3600))
    if minutes and minutes * 60 / step > 1000:
        step = int(minutes * 60 / 1000) + 1                      # never more than 1000 points per series
    end = int(time.time())
    data = cluster(cluster_name).get("/api/prometheus/data", params={"params": query, "start": end - minutes * 60, "end": end, "step": step})
    result = (data or {}).get("result", data) if isinstance(data, dict) else data
    result = result if isinstance(result, list) else [result]
    return {"cluster": cluster_name, "query": query, "minutes": minutes, "step_seconds": step, "series": len(result),
            "result": result[:c.limit_of(limit, 50)]}


@server.tool(annotations=RO)
@c.tool
def ceph_perf_counters(cluster_name: str, daemon_type: str, daemon_id: str) -> dict:
    """One daemon's performance counters (osd, mon, mgr, rgw, mds), e.g. daemon_type=osd daemon_id=12."""
    if daemon_type not in ("osd", "mon", "mgr", "rgw", "mds", "rbd-mirror", "tcmu-runner") or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", daemon_id or ""):
        raise c.ToolFailure("daemon_type: osd, mon, mgr, rgw, mds; daemon_id: e.g. 12 or the rgw / mds name")
    return {"cluster": cluster_name, "daemon": f"{daemon_type}.{daemon_id}",
            "counters": cluster(cluster_name).get(f"/api/perf_counters/{daemon_type}/{daemon_id}")}
