"""NetApp StorageGRID, read-only, through the Grid Management API the way NetApp's own code uses it (Harvest's StorageGRID
collector and the netapp.storagegrid Ansible collection): the API version from GET /api/versions, a token from
POST /api/v<n>/authorize, Bearer on every GET, Prometheus metrics from GET /metrics/api/v1/query.

The account: a Grid Manager user in a group with read-only access (no other permission is needed)."""
import threading
from urllib.parse import quote

from . import common as c
from mcp.server.mcpserver import MCPServer

KIND = "storagegrid"
# GET resources NetApp's code reads (netapp.storagegrid na_sg_grid_info, Harvest); sg_get accepts these only.
GRID_GET = {
    "grid/accounts", "grid/accounts-cache", "grid/admin-proxy", "grid/alarms", "grid/audit", "grid/audit-destinations",
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
    "Read-only NetApp StorageGRID (Grid Management API). Start with sg_grids, then sg_health / sg_node_health for the "
    "grid's state, sg_tenants for logical usage against quota (logical, not physical capacity), sg_ilm for policies and "
    "rules, sg_metrics for Prometheus metrics (ILM queue, capacity: see the library's 'commonly used Prometheus metrics' "
    "page for names). Nothing here changes the grid. Check the grid's version (sg_version) before applying documentation."))
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


RO = c.read_only()


@server.tool(annotations=RO)
@c.tool
def sg_grids() -> dict:
    """The StorageGRID grids in the inventory (names and addresses only)."""
    return {"grids": [{"name": n, "url": s.get("url")} for n, s in sorted(c.targets(KIND).items())]}


@server.tool(annotations=RO)
@c.tool
def sg_version(grid_name: str) -> dict:
    """The grid's StorageGRID release (product version) and the API version in use."""
    g = grid(grid_name)
    return {"grid": grid_name, "product_version": g.get("grid/config/product-version"), "api_version": g.version}


@server.tool(annotations=RO)
@c.tool
def sg_health(grid_name: str) -> dict:
    """Grid health: alarm and alert counts by severity, node connection states."""
    return {"grid": grid_name, "health": grid(grid_name).get("grid/health")}


@server.tool(annotations=RO)
@c.tool
def sg_node_health(grid_name: str, only_problems: bool = True, limit: int = 100) -> dict:
    """Every node's health and connection state (by default only the nodes that are not connected and healthy)."""
    nodes = grid(grid_name).get("grid/node-health") or []
    if only_problems:
        nodes = [n for n in nodes if str(n.get("state", "")).lower() != "connected" or str(n.get("severity", "normal")).lower() != "normal"]
    lim = c.limit_of(limit, 100)
    return {"grid": grid_name, "count": len(nodes), "nodes": nodes[:lim]}


@server.tool(annotations=RO)
@c.tool
def sg_topology(grid_name: str, depth: str = "site") -> dict:
    """The grid's sites and nodes with their health (depth: grid, site or node)."""
    if depth not in ("grid", "site", "node"):
        raise c.ToolFailure("depth: grid, site or node")
    return {"grid": grid_name, "topology": grid(grid_name).get("grid/health/topology", params={"depth": depth})}


@server.tool(annotations=RO)
@c.tool
def sg_tenants(grid_name: str, name_contains: str = "", limit: int = 50) -> dict:
    """Tenant accounts with their logical usage against quota (grid/accounts-cache, as Harvest reads it): id, name,
    data bytes, object count, quota bytes, percent used. Logical usage, not physical capacity."""
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


@server.tool(annotations=RO)
@c.tool
def sg_ilm(grid_name: str) -> dict:
    """ILM policies (active, proposed, historical; with policy tags on 11.8 and later), rules and storage pools, as the grid
    returns them (long lists are cut)."""
    g = grid(grid_name)
    return {"grid": grid_name, "policies": g.get("grid/ilm-policies"), "rules": g.get("grid/ilm-rules"), "pools": g.get("grid/ilm-pools")}


@server.tool(annotations=RO)
@c.tool
def sg_metrics(grid_name: str, query: str, limit: int = 100) -> dict:
    """A Prometheus query (instant) on the grid's metrics, e.g.
    storagegrid_ilm_awaiting_client_objects or storagegrid_storage_utilization_data_bytes. Returns up to `limit` series."""
    if not query.strip() or len(query) > 1000:
        raise c.ToolFailure("query: a Prometheus expression, 1000 characters at most")
    body = grid(grid_name).get("/metrics/api/v1/query?query=" + quote(query, safe=""), raw=True)
    data = body.get("data") if isinstance(body, dict) else body
    result = data.get("result", data) if isinstance(data, dict) else data
    result = result if isinstance(result, list) else [result]
    return {"grid": grid_name, "query": query, "series": len(result), "result": result[:c.limit_of(limit, 100)]}


@server.tool(annotations=RO)
@c.tool
def sg_get(grid_name: str, resource: str, limit: int = 100) -> dict:
    """Any other read the Grid Management API offers among NetApp's documented ones (e.g. grid/ha-groups,
    grid/gateway-configs, grid/ntp-servers, grid/ec-profiles, grid/license, grid/metric-names). Lists are cut to `limit`."""
    resource = resource.strip().strip("/")
    if resource not in GRID_GET:
        raise c.ToolFailure(f"'{resource}' is not one of the reads this server offers: {', '.join(sorted(GRID_GET))}")
    data = grid(grid_name).get(resource)
    if isinstance(data, list):
        return {"grid": grid_name, "resource": resource, "count": len(data), "items": data[:c.limit_of(limit, 100)]}
    return {"grid": grid_name, "resource": resource, "data": data}
