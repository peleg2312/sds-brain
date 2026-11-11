"""NetApp StorageGRID, read-only, through the Grid Management API the way NetApp's own code uses it (Harvest's StorageGRID
collector and the netapp.storagegrid Ansible collection): the API version from GET /api/versions, a token from
POST /api/v<n>/authorize, Bearer on every GET, Prometheus metrics from GET /metrics/api/v1/query.

The account: a Grid Manager user in a group with read-only access (no other permission is needed)."""
import re
import threading
from typing import Annotated
from urllib.parse import quote

from . import common as c
from mcp.server.mcpserver import MCPServer

KIND = "storagegrid"
# GET resources NetApp's code reads (netapp.storagegrid na_sg_grid_info, Harvest); sg_get accepts these only.
GRID_GET = {
    "grid/accounts", "grid/accounts-cache", "grid/admin-proxy", "grid/alarms", "grid/alerts", "grid/alert-history", "grid/alert-rules", "grid/audit", "grid/audit-destinations",
    "grid/autosupport", "grid/compliance-global", "grid/config", "grid/config/management", "grid/config/product-version",
    "grid/deactivated-features", "grid/dns-servers", "grid/domain-names", "grid/ec-profiles", "grid/expansion",
    "grid/expansion/nodes", "grid/expansion/sites", "grid/firewall-blocked-ports", "grid/firewall-external-ports",
    "grid/firewall-privileged-ips", "grid/grid-networks", "grid/groups", "grid/ha-groups", "grid/health", "grid/health/topology",
    "grid/ilm-criteria", "grid/ilm-grade-site", "grid/ilm-grades", "grid/ilm-policies", "grid/ilm-rules", "grid/ilm-pools",
    "grid/license", "grid/gateway-configs", "grid/management-certificate", "grid/metric-names", "grid/network-topology",
    "grid/node-health", "grid/ntp-servers", "grid/recovery", "grid/recovery/available-nodes", "grid/regions", "grid/schemes",
    "grid/single-sign-on", "grid/snmp", "grid/storage-api-certificate", "grid/storage-proxy", "grid/untrusted-client-network",
    "grid/vlan-interfaces",
}

server = MCPServer("storagegrid", instructions=(
    "Read-only NetApp StorageGRID through the Grid Management API. Start with sg_overview (one call: version, health, "
    "current alerts, problem nodes, tenants near quota, ILM backlog, lost objects, metadata and certificate state), "
    "then narrow down: sg_alerts / sg_alert_history, sg_node_health, sg_topology, sg_tenants and sg_tenant_buckets "
    "(logical usage, not physical capacity), sg_ilm, sg_metrics for any Prometheus metric, sg_get for other reads. "
    "Grid names come from sg_grids. Nothing here changes the grid. Check the release (sg_version) before applying "
    "documentation: 11.8, 11.9 and 12.0 differ."))
_sessions, _lock = {}, threading.Lock()


class Grid:
    def __init__(self, name):
        self.name, self.settings = name, c.target(KIND, name)
        url = self.settings.get("url") or ""
        if not url.startswith("https://"):
            raise c.ToolFailure(f"storagegrid '{name}': url must be https://<admin node or its load balancer>")
        self.version = str(self.settings.get("api_version") or "")
        self.token = None
        self.client = c.ReadOnlyClient(url, self.settings, headers={"Accept": "application/json"})

    def api(self):
        if not self.version:                                          # unauthenticated, as Harvest does
            r = self.client.request("GET", "/api/versions")
            versions = (r.json().get("data") or []) if r.status_code == 200 else []
            self.version = str(versions[-1]) if versions else "4"
        return f"/api/v{self.version}"

    def login(self):
        user, password = c.credentials(KIND, self.name)
        path = f"{self.api()}/authorize"
        self.client.allow = {("POST", path), ("DELETE", path)}
        r = self.client.request("POST", path, json={"username": user, "password": password, "cookie": False, "csrfToken": False})
        self.client.allow = set()
        if r.status_code != 200 or not isinstance(r.json().get("data"), str):
            raise c.api_error(r, f"storagegrid '{self.name}': sign-in failed")
        self.token = r.json()["data"]

    def get(self, path, params=None, raw=False):
        """GET <api>/<path> (or an absolute path), signing in again once when the token expired"""
        for attempt in (1, 2):
            if not self.token:
                self.login()
            url = path if path.startswith("/") else f"{self.api()}/{path}"
            r = self.client.request("GET", url, params=params, headers={"Authorization": "Bearer " + self.token})
            if r.status_code == 401 and attempt == 1:
                self.token = None
                continue
            if r.status_code != 200:
                raise c.api_error(r, f"storagegrid '{self.name}' GET {url}")
            body = r.json()
            return body if raw else body.get("data", body)


def grid(name):
    with _lock:
        if name not in _sessions:
            _sessions[name] = Grid(name)
        return _sessions[name]


RO = c.read_only
GridName = Annotated[str, c.arg("The grid's name in the inventory (sg_grids lists them), e.g. grid-a.")]
Limit = Annotated[int, c.arg("The most items to return.", ge=1, le=500)]


@server.tool(title="List the grids", annotations=RO("List the grids"))
@c.tool
def sg_grids() -> dict:
    """The StorageGRID grids in the inventory: names and admin addresses (no credentials). Use a name with every other tool."""
    return {"grids": [{"name": n, "url": s.get("url")} for n, s in sorted(c.targets(KIND).items())]}


@server.tool(title="Grid overview (triage)", annotations=RO("Grid overview (triage)"))
@c.tool
def sg_overview(grid_name: GridName) -> dict:
    """One call for the state of a grid, for a first look or a daily check: release, health counts, the current alerts
    (most severe first), nodes that are not connected and normal, tenants above 80% of their quota, and key metrics:
    ILM backlog, lost objects, metadata used against allowed, usable against total space, the soonest certificate
    expiry, NTP lock, failed appliance disks. A part that cannot be read says why, the rest still answers."""
    g = grid(grid_name)

    def metric(q):
        body = g.get("/metrics/api/v1/query?query=" + quote(q, safe=""), raw=True)
        res = (body.get("data") or {}).get("result") if isinstance(body, dict) else None
        vals = [float(r["value"][1]) for r in res or [] if isinstance(r, dict) and len(r.get("value") or []) == 2]
        return vals[0] if len(vals) == 1 else vals
    metrics = {
        "ilm_awaiting_client_objects": "sum(storagegrid_ilm_awaiting_client_objects)",
        "ilm_awaiting_total_objects": "sum(storagegrid_ilm_awaiting_total_objects)",
        "objects_lost": "sum(storagegrid_content_objects_lost)",
        "metadata_used_of_allowed_max_ratio": "max(storagegrid_storage_utilization_metadata_bytes / storagegrid_storage_utilization_metadata_allowed_bytes)",
        "usable_of_total_space_ratio": "sum(storagegrid_storage_utilization_usable_space_bytes) / sum(storagegrid_storage_utilization_total_space_bytes)",
        "storage_api_cert_expiry_days_min": "min(storagegrid_servercertificate_storage_api_endpoints_cert_expiry_days)",
        "management_cert_expiry_days_min": "min(storagegrid_servercertificate_management_interface_cert_expiry_days)",
        "ntp_locked_min": "min(storagegrid_ntp_locked)",
        "appliance_failed_disks": "sum(storagegrid_appliance_failed_disks)",
    }

    def alerts():
        rows = g.get("grid/alerts") or []
        rank = {"critical": 0, "major": 1, "minor": 2}
        rows = sorted(rows, key=lambda a: rank.get(str(a.get("severity", "")).lower(), 3) if isinstance(a, dict) else 3) if isinstance(rows, list) else rows
        return {"count": len(rows), "top": rows[:10]} if isinstance(rows, list) else rows

    def nodes():
        rows = g.get("grid/node-health") or []
        return [n for n in rows if str(n.get("state", "")).lower() != "connected" or str(n.get("severity", "normal")).lower() != "normal"][:20]

    def tenants():
        rows = []
        for r in g.get("grid/accounts-cache") or []:
            used, quota = r.get("dataBytes"), c.pick(r, "policy.quotaObjectBytes")
            if isinstance(used, (int, float)) and quota and used / quota >= 0.8:
                rows.append({"id": r.get("id"), "name": r.get("name"), "used_percent": round(used / quota * 100, 1)})
        return sorted(rows, key=lambda x: -x["used_percent"])[:20]
    parts = {"version": lambda: g.get("grid/config/product-version"), "health": lambda: g.get("grid/health"),
             "alerts": alerts, "problem_nodes": nodes, "tenants_over_80_percent": tenants}
    parts.update({k: (lambda q=q: metric(q)) for k, q in metrics.items()})
    out = c.gather(parts)
    return {"grid": grid_name, **{k: out[k] for k in ("version", "health", "alerts", "problem_nodes", "tenants_over_80_percent")},
            "metrics": {k: out[k] for k in metrics}}


@server.tool(title="Grid release", annotations=RO("Grid release"))
@c.tool
def sg_version(grid_name: GridName) -> dict:
    """The grid's StorageGRID release (product version) and the API version this server uses with it."""
    g = grid(grid_name)
    return {"grid": grid_name, "product_version": g.get("grid/config/product-version"), "api_version": g.version}


@server.tool(title="Grid health counts", annotations=RO("Grid health counts"))
@c.tool
def sg_health(grid_name: GridName) -> dict:
    """Grid health in numbers: alarm and alert counts by severity, node connection states (sg_alerts lists the alerts)."""
    return {"grid": grid_name, "health": grid(grid_name).get("grid/health")}


@server.tool(title="Current alerts", annotations=RO("Current alerts"))
@c.tool
def sg_alerts(grid_name: GridName, limit: Limit = 50) -> dict:
    """The grid's current alerts, most severe first, as the grid returns them (rule, severity, node, site, triggered
    time). For what fired and cleared before, sg_alert_history."""
    rows = grid(grid_name).get("grid/alerts") or []
    rank = {"critical": 0, "major": 1, "minor": 2}
    if isinstance(rows, list):
        rows.sort(key=lambda a: rank.get(str(a.get("severity", "")).lower(), 3) if isinstance(a, dict) else 3)
    return {"grid": grid_name, "count": len(rows) if isinstance(rows, list) else None,
            "alerts": rows[:c.limit_of(limit)] if isinstance(rows, list) else rows}


@server.tool(title="Resolved alerts", annotations=RO("Resolved alerts"))
@c.tool
def sg_alert_history(grid_name: GridName, limit: Limit = 50) -> dict:
    """Alerts that fired and were resolved, as the grid returns them: what happened before now (correlate with an
    incident's time)."""
    rows = grid(grid_name).get("grid/alert-history") or []
    return {"grid": grid_name, "count": len(rows) if isinstance(rows, list) else None,
            "alerts": rows[:c.limit_of(limit)] if isinstance(rows, list) else rows}


@server.tool(title="Node health", annotations=RO("Node health"))
@c.tool
def sg_node_health(grid_name: GridName,
                   only_problems: Annotated[bool, c.arg("Only nodes that are not connected or not normal (default true).")] = True,
                   limit: Limit = 100) -> dict:
    """Every node's health and connection state: name, type, site, state, severity."""
    nodes = grid(grid_name).get("grid/node-health") or []
    if only_problems:
        nodes = [n for n in nodes if str(n.get("state", "")).lower() != "connected" or str(n.get("severity", "normal")).lower() != "normal"]
    return {"grid": grid_name, "count": len(nodes), "nodes": nodes[:c.limit_of(limit, 100)]}


@server.tool(title="Grid topology", annotations=RO("Grid topology"))
@c.tool
def sg_topology(grid_name: GridName,
                depth: Annotated[str, c.arg("How deep: grid, site (default) or node.", pattern="^(grid|site|node)$")] = "site") -> dict:
    """The grid's sites and nodes with their health, as a tree."""
    return {"grid": grid_name, "topology": grid(grid_name).get("grid/health/topology", params={"depth": depth})}


@server.tool(title="Tenants and quota", annotations=RO("Tenants and quota"))
@c.tool
def sg_tenants(grid_name: GridName,
               name_contains: Annotated[str, c.arg("Only tenants whose name contains this text (case-insensitive).")] = "",
               limit: Limit = 50) -> dict:
    """Tenant accounts with their logical usage against quota, fullest first: id, name, data bytes, object count, quota
    bytes, percent used (as Harvest reads it, grid/accounts-cache). Logical usage, not physical capacity."""
    rows = grid(grid_name).get("grid/accounts-cache") or []
    if name_contains:
        rows = [r for r in rows if name_contains.lower() in str(r.get("name", "")).lower()]
    out = []
    for r in rows:
        used, quota = r.get("dataBytes"), c.pick(r, "policy.quotaObjectBytes")
        out.append({"id": r.get("id"), "name": r.get("name"), "capabilities": r.get("capabilities"), "data_bytes": used,
                    "object_count": r.get("objectCount"), "quota_bytes": quota,
                    "used_percent": round(used / quota * 100, 1) if isinstance(used, (int, float)) and quota else None})
    out.sort(key=lambda x: -(x["used_percent"] or 0))
    return {"grid": grid_name, "count": len(out), "tenants": out[:c.limit_of(limit)]}


@server.tool(title="A tenant's buckets", annotations=RO("A tenant's buckets"))
@c.tool
def sg_tenant_buckets(grid_name: GridName,
                      tenant_id: Annotated[str, c.arg("The tenant's account id (sg_tenants shows it), digits only.", pattern=r"^\d{1,30}$")],
                      limit: Limit = 100) -> dict:
    """One tenant's total usage and every bucket's object count and data bytes, largest first (as Harvest reads it:
    grid/accounts/<id>/usage with bucket detail)."""
    if not re.fullmatch(r"\d{1,30}", tenant_id or ""):
        raise c.ToolFailure("tenant_id: the account id, digits only")
    data = grid(grid_name).get(f"grid/accounts/{tenant_id}/usage", params={"includeBucketDetail": "true"}) or {}
    buckets = data.get("buckets") or [] if isinstance(data, dict) else []
    buckets = sorted(buckets, key=lambda b: -(b.get("dataBytes") or 0) if isinstance(b, dict) else 0)
    totals = {k: v for k, v in data.items() if k != "buckets"} if isinstance(data, dict) else data
    return {"grid": grid_name, "tenant_id": tenant_id, "usage": totals, "bucket_count": len(buckets), "buckets": buckets[:c.limit_of(limit, 100)]}


@server.tool(title="ILM policies and rules", annotations=RO("ILM policies and rules"))
@c.tool
def sg_ilm(grid_name: GridName) -> dict:
    """ILM policies (active, proposed, historical; with policy tags on 11.8 and later), rules and storage pools, as the
    grid returns them. For the ILM backlog itself, sg_overview or sg_metrics storagegrid_ilm_awaiting_client_objects."""
    g = grid(grid_name)
    return {"grid": grid_name, "policies": g.get("grid/ilm-policies"), "rules": g.get("grid/ilm-rules"), "pools": g.get("grid/ilm-pools")}


@server.tool(title="Prometheus query", annotations=RO("Prometheus query"))
@c.tool
def sg_metrics(grid_name: GridName,
               query: Annotated[str, c.arg("A Prometheus expression on the grid's metrics, e.g. sum by (node) (storagegrid_ilm_awaiting_client_objects) "
                                           "or max_over_time(storagegrid_ilm_awaiting_client_objects[6h]).", max_length=1000)],
               limit: Limit = 100) -> dict:
    """Any Prometheus query on the grid's own metrics (as NetApp's Harvest reads them), the value now; for a period use
    *_over_time or a subquery. Metric names: the library's 'commonly used Prometheus metrics' page, or
    sg_get grid/metric-names."""
    if not query.strip():
        raise c.ToolFailure("query: a Prometheus expression")
    body = grid(grid_name).get("/metrics/api/v1/query?query=" + quote(query, safe=""), raw=True)
    data = body.get("data") if isinstance(body, dict) else body
    result = data.get("result", data) if isinstance(data, dict) else data
    result = result if isinstance(result, list) else [result]
    return {"grid": grid_name, "query": query, "series": len(result), "result": result[:c.limit_of(limit, 100)]}


@server.tool(title="Other grid reads", annotations=RO("Other grid reads"))
@c.tool
def sg_get(grid_name: GridName,
           resource: Annotated[str, c.arg("One of NetApp's documented grid reads, e.g. grid/ha-groups, grid/gateway-configs, "
                                          "grid/ntp-servers, grid/ec-profiles, grid/license, grid/alert-rules, grid/metric-names.")],
           limit: Limit = 100) -> dict:
    """Any other read of the Grid Management API among NetApp's documented ones (HA groups, load balancer endpoints, NTP,
    erasure coding profiles, license, alert rules, metric names, expansion and recovery state...). Lists are cut to limit."""
    resource = resource.strip().strip("/")
    if resource not in GRID_GET:
        raise c.ToolFailure(f"'{resource}' is not one of the reads this server offers: {', '.join(sorted(GRID_GET))}")
    data = grid(grid_name).get(resource)
    if isinstance(data, list):
        return {"grid": grid_name, "resource": resource, "count": len(data), "items": data[:c.limit_of(limit, 100)]}
    return {"grid": grid_name, "resource": resource, "data": data}
