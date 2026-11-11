#!/usr/bin/env python3
"""Tests of the read-only servers against stand-ins of the four APIs, over real TLS (a test CA and certificate), through
the MCP protocol (stdio, and HTTP with the bearer token). Each stand-in records every request it receives, so the tests
also prove that no write ever left a server. Needs the packages of requirements.txt and openssl.

    python3 connections/servers/test_servers.py          exits 1 on the first failure (about 20 s)"""
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = tempfile.mkdtemp(prefix="sds-mcp-test-")
ENV = {k: v for k, v in os.environ.items() if not k.startswith(("SDS_", "MCP_", "ONEVIEWSDK_"))}


def sh(*cmd):
    subprocess.run(cmd, check=True, capture_output=True, cwd=WORK)


# ---- a test CA and a server certificate for 127.0.0.1
sh("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", "ca.key", "-out", "ca.pem", "-days", "2", "-subj", "/CN=sds-test-ca",
   "-addext", "basicConstraints=critical,CA:TRUE", "-addext", "keyUsage=critical,keyCertSign,cRLSign", "-addext", "subjectKeyIdentifier=hash")
sh("openssl", "req", "-newkey", "rsa:2048", "-nodes", "-keyout", "srv.key", "-out", "srv.csr", "-subj", "/CN=127.0.0.1")
with open(os.path.join(WORK, "ext.cnf"), "w") as f:
    f.write("subjectAltName=IP:127.0.0.1\nbasicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n"
            "authorityKeyIdentifier=keyid\n")
sh("openssl", "x509", "-req", "-in", "srv.csr", "-CA", "ca.pem", "-CAkey", "ca.key", "-CAcreateserial", "-out", "srv.pem", "-days", "2", "-extfile", "ext.cnf")
FPR = subprocess.run(["openssl", "x509", "-in", "srv.pem", "-noout", "-fingerprint", "-sha256"], capture_output=True, text=True, cwd=WORK, check=True).stdout.split("=", 1)[1].strip()


class Fake:
    """an HTTPS server answering with route(method, path, query, headers, body) -> (status, json, headers); every
    request is recorded"""

    def __init__(self, route):
        self.calls = []
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def handle_any(self):
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"null") if n else None
                path, _, query = self.path.partition("?")
                fake.calls.append((self.command, path))
                status, data, headers = route(self.command, path, query, self.headers, body)
                raw = json.dumps(data).encode() if data is not None else b""
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = handle_any

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(os.path.join(WORK, "srv.pem"), os.path.join(WORK, "srv.key"))
        self.srv.socket = ctx.wrap_socket(self.srv.socket, server_side=True)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def writes(self, allowed):
        return [c for c in self.calls if c[0] not in ("GET", "HEAD") and c not in allowed]


# ---- StorageGRID: as Harvest and the Ansible collection use it
def sg(method, path, query, h, body):
    if path == "/api/versions":
        return 200, {"data": ["3", "4"]}, None
    if path == "/api/v4/authorize" and method == "POST":
        ok = body == {"username": "sgro", "password": "sg-pass", "cookie": False, "csrfToken": False}
        return (200, {"data": "sg-token"}, None) if ok else (401, {"message": {"text": "bad"}}, None)
    if h.get("Authorization") != "Bearer sg-token":
        return 401, {"message": "token"}, None
    data = {"/api/v4/grid/config/product-version": {"productVersion": "11.9.0.3"},
            "/api/v4/grid/health": {"alarms": {"critical": 0}, "alerts": {"critical": 1, "major": 0, "minor": 2}, "nodes": {"connected": 5, "unknown": 1}},
            "/api/v4/grid/node-health": [{"id": "n1", "name": "dc1-sn1", "state": "connected", "severity": "normal"},
                                         {"id": "n2", "name": "dc1-sn2", "state": "unknown", "severity": "critical"}],
            "/api/v4/grid/accounts-cache": [{"id": "1", "name": "aron", "capabilities": ["s3"], "dataBytes": 900, "objectCount": 3,
                                             "policy": {"quotaObjectBytes": 1000}}, {"id": "2", "name": "bo", "dataBytes": 10, "policy": {"quotaObjectBytes": None}}],
            "/api/v4/grid/ilm-policies": [{"id": "p1", "name": "baseline", "active": True}],
            "/api/v4/grid/ilm-rules": [{"id": "r1", "displayName": "2 copies"}], "/api/v4/grid/ilm-pools": [],
            "/api/v4/grid/ha-groups": [{"name": "s3-vip", "virtualIps": ["10.0.0.5"]}],
            "/api/v4/grid/alerts": [{"name": "Low object data storage", "severity": "minor", "node": "dc1-sn1"},
                                    {"name": "Node not connected", "severity": "critical", "node": "dc1-sn2"}],
            "/api/v4/grid/alert-history": [{"name": "Services appliance link down", "severity": "major", "resolvedAt": "2026-11-09T12:00:00Z"}]}
    if path == "/metrics/api/v1/query":
        return 200, {"status": "success", "data": {"resultType": "vector", "result": [{"metric": {"__name__": "storagegrid_ilm_awaiting_client_objects", "node": "dc1-sn1"}, "value": [1, "42"]}]}}, None
    return (200, {"data": data[path]}, None) if path in data else (404, {"message": "no"}, None)


# ---- Ceph dashboard REST API
def ceph(method, path, query, h, body):
    if path == "/api/auth" and method == "POST":
        return (201, {"token": "ceph-token", "username": "ro"}, None) if body == {"username": "ro", "password": "ceph-pass"} else (401, {"detail": "bad"}, None)
    if h.get("Authorization") != "Bearer ceph-token":
        return 401, {"detail": "token"}, None
    want = {"/api/osd": "1.1", "/api/host": "1.3", "/api/crush_rule": "2.0"}.get(path, "1.0")      # as in Ceph's openapi.yaml
    if h.get("Accept") != f"application/vnd.ceph.api.v{want}+json":
        return 415, {"detail": f"needs v{want}, got {h.get('Accept')}"}, None
    if path == "/api/prometheus/data":
        q = dict(x.split("=", 1) for x in query.split("&") if "=" in x)
        assert set(q) == {"params", "start", "end", "step"}, q
        return 200, {"resultType": "matrix", "result": [{"metric": {"__name__": urllib.request.unquote(q["params"])}, "values": [[int(q["end"]), "1"]]}]}, None
    data = {"/api/summary": {"version": "ceph version 19.2.1-100.el9cp (abc) squid (stable)", "health_status": "HEALTH_WARN"},
            "/api/health/minimal": {"health": {"status": "HEALTH_WARN", "checks": [{"type": "PG_DEGRADED", "severity": "HEALTH_WARN", "summary": {"message": "Degraded data redundancy"}}]},
                                    "pg_info": {"object_stats": {"num_objects_degraded": 12}}},
            "/api/osd": [{"osd": 0, "id": 0, "host": {"name": "osd-01"}, "up": 1, "in": 1, "tree": {"device_class": "hdd"}},
                         {"osd": 1, "id": 1, "host": {"name": "osd-02"}, "up": 0, "in": 1, "tree": {"device_class": "hdd"}}],
            "/api/rgw/user/acme$app": {"user_id": "app", "tenant": "acme", "suspended": 0, "max_buckets": 1000,
                                        "keys": [{"user": "acme$app", "access_key": "AKIAEXAMPLE", "secret_key": "s3cr3tvalue"}]},
            "/api/crush_rule": [{"rule_id": 0, "rule_name": "replicated_rule"}]}
    return (200, data[path], None) if path in data else (404, {"detail": "no"}, None)


# ---- HPE OneView REST API, as the hpeOneView SDK calls it
def oneview(method, path, query, h, body):
    if path == "/rest/version":
        return 200, {"currentVersion": 6000, "minimumVersion": 120}, None
    if path == "/rest/login-sessions":
        if method == "POST":
            return (200, {"sessionID": "ov-session"}, None) if body and body.get("userName") == "ovro" and body.get("password") == "ov-pass" else (401, {"message": "bad"}, None)
        return 200, None, None
    if h.get("auth") != "ov-session":
        return 401, {"errorCode": "AUTHORIZATION"}, None
    page = lambda members: (200, {"members": members, "count": len(members), "total": len(members), "start": 0, "nextPageUri": None, "uri": path}, None)
    if path == "/rest/alerts":
        return page([{"severity": "Critical", "alertState": "Active", "description": "Drive bay 3 failed", "correctiveAction": "Replace the drive",
                      "created": "2026-11-10T10:00:00Z", "associatedResource": {"resourceName": "osd-02", "resourceCategory": "server-hardware"}}])
    if path == "/rest/server-hardware":
        servers = [{"name": "osd-01", "uri": "/rest/server-hardware/31393736", "model": "Apollo 4200 Gen10 Plus", "serialNumber": "CZ1", "status": "OK", "powerState": "On",
                    "mpModel": "iLO5", "mpFirmwareVersion": "3.10", "mpHostInfo": {"mpIpAddresses": [{"address": "10.1.1.1"}]}},
                   {"name": "osd-02", "uri": "/rest/server-hardware/31393737", "model": "Apollo 4200 Gen10 Plus", "serialNumber": "CZ2", "status": "Critical", "powerState": "On"}]
        q = urllib.request.unquote(query)
        servers = [x for x in servers if not re.search(r"name='([^']+)'", q) or re.search(r"name='([^']+)'", q).group(1) == x["name"]]
        return page(servers)
    if path == "/rest/server-hardware/31393737/utilization":
        assert "refresh=true" not in query.lower(), query                  # never asks the iLO for fresh data
        return 200, {"isFresh": True, "resolution": 300, "metricList": [{"metricName": "CpuUtilization", "metricCapacity": 100,
                                                                          "metricSamples": [[1793520000000, 12], [1793519700000, 15]]}]}, None
    if path == "/rest/tasks":
        return page([{"name": "Update firmware", "taskState": "Completed", "owner": "admin", "associatedResource": {"resourceName": "osd-01"}}])
    return 404, {"message": "no"}, None


# ---- HPE iLO Redfish, as python-ilorest-library calls it
def ilo(method, path, query, h, body):
    p = path.rstrip("/")
    if p == "/redfish/v1":
        return 200, {"@odata.id": "/redfish/v1/", "RedfishVersion": "1.13.0", "Links": {"Sessions": {"@odata.id": "/redfish/v1/SessionService/Sessions/"}},
                     "Systems": {"@odata.id": "/redfish/v1/Systems/"}}, None
    if p == "/redfish/v1/SessionService/Sessions" and method == "POST":
        if body != {"UserName": "ilo-ro", "Password": "ilo-pass"}:
            return 401, {"error": "bad"}, None
        host = h.get("Host")                                       # iLO answers with the session's absolute address
        return 201, {"Id": "s1"}, {"X-Auth-Token": "ilo-token", "Location": f"https://{host}/redfish/v1/SessionService/Sessions/s1/"}
    if p == "/redfish/v1/SessionService/Sessions/s1" and method == "DELETE":
        return 200, {}, None
    if h.get("X-Auth-Token") != "ilo-token":
        return 401, {"error": "auth"}, None
    data = {"/redfish/v1/Systems": {"Members": [{"@odata.id": "/redfish/v1/Systems/1/"}]},
            "/redfish/v1/Managers": {"Members": [{"@odata.id": "/redfish/v1/Managers/1/"}]},
            "/redfish/v1/Chassis": {"Members": [{"@odata.id": "/redfish/v1/Chassis/1/"}]},
            "/redfish/v1/Systems/1": {"Model": "ProLiant XL420 Gen10 Plus", "SerialNumber": "CZ1", "PowerState": "On", "BiosVersion": "U44 v2.80",
                                      "Status": {"Health": "Warning"}, "Oem": {"Hpe": {"PostState": "FinishedPost", "AggregateHealthStatus": {"Storage": {"Status": {"Health": "Critical"}}}}}},
            "/redfish/v1/Managers/1": {"Model": "iLO 5", "FirmwareVersion": "iLO 5 v3.10"},
            "/redfish/v1/Systems/1/LogServices/IML/Entries": {"Members": [
                {"@odata.id": "/redfish/v1/Systems/1/LogServices/IML/Entries/1/", "Created": "2026-11-09T08:00:00Z", "Severity": "OK", "Message": "Server power restored"},
                {"@odata.id": "/redfish/v1/Systems/1/LogServices/IML/Entries/2/", "Created": "2026-11-10T09:59:00Z", "Severity": "Critical",
                 "Message": "Drive Array Physical Drive Status Change. Port 1I Box 1 Bay 3 failed", "Oem": {"Hpe": {"Class": 13, "Code": 33}}}]},
            "/redfish/v1/Chassis/1/Thermal": {"Fans": [{"Name": "Fan 1", "Reading": 30, "Status": {"Health": "OK"}}],
                                              "Temperatures": [{"Name": "01-Inlet Ambient", "ReadingCelsius": 24, "Status": {"Health": "OK"}}]}}
    return (200, data[p], None) if p in data else (404, {"error": "no"}, None)


SG, CEPH, OV, ILO = Fake(sg), Fake(ceph), Fake(oneview), Fake(ilo)
inventory = {"storagegrid": {"grid-a": {"url": f"https://127.0.0.1:{SG.port}", "ca_file": "ca.pem"}},
             "ceph": {"prod-a": {"url": f"https://127.0.0.1:{CEPH.port}", "ca_file": "ca.pem"},
                      "bad": {"url": f"https://127.0.0.1:{CEPH.port}", "insecure": True}},
             "oneview": {"ov-1": {"host": f"127.0.0.1:{OV.port}", "ca_file": "ca.pem"}},
             "ilo": {"defaults": {"ca_file": "ca.pem"},
                     "servers": {"osd-01": {"host": f"127.0.0.1:{ILO.port}"},
                                 "osd-pinned": {"host": f"127.0.0.1:{ILO.port}", "ca_file": "", "fingerprint": FPR},
                                 "osd-unverified": {"host": f"127.0.0.1:{ILO.port}", "ca_file": ""}}}}
with open(os.path.join(WORK, "targets.json"), "w") as f:
    json.dump(inventory, f)
ENV.update(SDS_MCP_CONFIG=os.path.join(WORK, "targets.json"), PYTHONPATH=HERE, NO_PROXY="127.0.0.1",
           SDS_STORAGEGRID_USERNAME="sgro", SDS_STORAGEGRID_PASSWORD="sg-pass", SDS_CEPH_PROD_A_USERNAME="ro", SDS_CEPH_PROD_A_PASSWORD="ceph-pass",
           SDS_ONEVIEW_USERNAME="ovro", SDS_ONEVIEW_PASSWORD="ov-pass", SDS_ILO_USERNAME="ilo-ro", SDS_ILO_PASSWORD="ilo-pass")


def mcp(name, calls):
    """initialize, tools/list, then each (tool, arguments) over stdio; returns ({tool: structured result}, [tool names])"""
    msgs = [{"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"}, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}]
    msgs += [{"jsonrpc": "2.0", "id": 10 + i, "method": "tools/call", "params": {"name": t, "arguments": a}} for i, (t, a) in enumerate(calls)]
    p = subprocess.Popen([sys.executable, "-m", "sds_mcp", name], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, cwd=HERE, env=ENV)
    out = {}
    for m in msgs:                                             # one at a time: the answers come back in order
        p.stdin.write(json.dumps(m) + "\n")
        p.stdin.flush()
        if "id" not in m:
            continue
        while True:
            line = p.stdout.readline()
            if not line:
                raise AssertionError(f"{name} exited: {p.stderr.read()[-800:]}")
            got = json.loads(line)
            if got.get("id") == m["id"]:
                out[m["id"]] = got
                break
    p.stdin.close()
    p.wait(timeout=20)
    tools = [t["name"] for t in out[1]["result"]["tools"]]
    for t in out[1]["result"]["tools"]:
        assert t.get("annotations", {}).get("readOnlyHint") is True and t["annotations"].get("destructiveHint") is False, (name, t["name"])
    res = []
    for i in range(len(calls)):
        r = out[10 + i].get("result") or {}
        sc = r.get("structuredContent")
        res.append(sc.get("result", sc) if isinstance(sc, dict) and set(sc) == {"result"} else sc if sc is not None else json.loads(r["content"][0]["text"]))
    return res, tools


try:
    # ---- StorageGRID
    r, tools = mcp("storagegrid", [("sg_grids", {}), ("sg_version", {"grid_name": "grid-a"}), ("sg_health", {"grid_name": "grid-a"}),
                                   ("sg_node_health", {"grid_name": "grid-a"}), ("sg_tenants", {"grid_name": "grid-a"}),
                                   ("sg_metrics", {"grid_name": "grid-a", "query": "storagegrid_ilm_awaiting_client_objects"}),
                                   ("sg_get", {"grid_name": "grid-a", "resource": "grid/ha-groups"}),
                                   ("sg_alerts", {"grid_name": "grid-a"}), ("sg_alert_history", {"grid_name": "grid-a"}),
                                   ("sg_get", {"grid_name": "grid-a", "resource": "grid/users/root/change-password"}),
                                   ("sg_version", {"grid_name": "nope"})])
    assert {"sg_grids", "sg_version", "sg_health", "sg_alerts", "sg_alert_history", "sg_node_health", "sg_topology", "sg_tenants", "sg_ilm",
            "sg_metrics", "sg_get"} <= set(tools), tools
    assert r[1]["product_version"] == {"productVersion": "11.9.0.3"} and r[1]["api_version"] == "4", r[1]
    assert r[2]["health"]["alerts"]["critical"] == 1
    assert [n["name"] for n in r[3]["nodes"]] == ["dc1-sn2"], r[3]                        # only the problem node
    assert r[4]["tenants"][0] == {"id": "1", "name": "aron", "capabilities": ["s3"], "data_bytes": 900, "object_count": 3, "quota_bytes": 1000, "used_percent": 90.0}, r[4]
    assert r[5]["result"][0]["value"][1] == "42", r[5]
    assert r[6]["items"][0]["name"] == "s3-vip"
    assert r[7]["alerts"][0]["severity"] == "critical" and r[7]["count"] == 2, r[7]                      # most severe first
    assert r[8]["alerts"][0]["name"] == "Services appliance link down", r[8]
    assert "not one of the reads" in r[9]["error"] and "unknown storagegrid 'nope'" in r[10]["error"], (r[9], r[10])
    assert SG.writes({("POST", "/api/v4/authorize")}) == [], SG.writes(set())
    print("storagegrid ok")

    # ---- Ceph
    r, tools = mcp("ceph", [("ceph_status", {"cluster_name": "prod-a"}), ("ceph_osds", {"cluster_name": "prod-a", "only_problems": True}),
                            ("ceph_rgw_user", {"cluster_name": "prod-a", "uid": "acme$app"}),
                            ("ceph_api_get", {"cluster_name": "prod-a", "path": "/api/crush_rule"}),
                            ("ceph_api_get", {"cluster_name": "prod-a", "path": "/api/auth/check"}),
                            ("ceph_api_get", {"cluster_name": "prod-a", "path": "/api/osd/../auth"}),
                            ("ceph_status", {"cluster_name": "bad"}),
                            ("ceph_metrics", {"cluster_name": "prod-a", "query": "ceph_health_status", "minutes": 60})])
    assert r[0]["health"]["checks"][0]["type"] == "PG_DEGRADED" and "squid" in r[0]["version"], r[0]
    assert [o["id"] for o in r[1]["osds"]] == [1], r[1]
    assert "keys" not in r[2]["user"] and "s3cr3tvalue" not in json.dumps(r) and "AKIAEXAMPLE" not in json.dumps(r), r[2]
    assert r[3]["items"][0]["rule_name"] == "replicated_rule", r[3]                    # v2.0 media type for crush_rule
    assert "not a dashboard read" in r[4]["error"] and "dot segments" in r[5]["error"], (r[4], r[5])
    assert "cannot be switched off" in r[6]["error"], r[6]
    assert r[7]["result"][0]["metric"]["__name__"] == "ceph_health_status" and r[7]["minutes"] == 60, r[7]
    assert {"ceph_alerts", "ceph_metrics", "ceph_perf_counters"} <= set(tools), tools
    assert CEPH.writes({("POST", "/api/auth")}) == [], CEPH.writes(set())
    print("ceph ok")

    # ---- OneView, through HPE's SDK
    r, tools = mcp("oneview", [("ov_alerts", {"appliance": "ov-1"}), ("ov_server_hardware", {"appliance": "ov-1"}),
                               ("ov_server", {"appliance": "ov-1", "server_name": "osd-02"}), ("ov_tasks", {"appliance": "ov-1"}),
                               ("ov_utilization", {"appliance": "ov-1", "name": "osd-02", "metrics": "CpuUtilization"})])
    assert r[0]["alerts"][0]["description"] == "Drive bay 3 failed" and r[0]["alerts"][0]["correctiveAction"] == "Replace the drive", r[0]
    assert r[1]["count"] == 2 and r[1]["servers"][0]["mpHostInfo.mpIpAddresses"] == [{"address": "10.1.1.1"}], r[1]
    assert r[2]["server"]["status"] == "Critical", r[2]
    assert r[3]["tasks"][0]["name"] == "Update firmware", r[3]
    assert r[4]["metrics"]["CpuUtilization"]["samples"][0] == [1793520000000, 12] and r[4]["resolution"] == 300, r[4]
    assert OV.writes({("POST", "/rest/login-sessions")}) == [], OV.writes(set())
    # the guard: a write through the SDK's own connection is refused before it is sent
    sys.path.insert(0, HERE)
    os.environ.update({k: v for k, v in ENV.items() if k.startswith("SDS_")})
    from sds_mcp import common, oneview, ilo
    common.config.cache_clear()
    ov = oneview.client("ov-1")
    before = len(OV.calls)
    for attempt in (lambda: ov.connection.post("/rest/server-hardware", {"hostname": "x"}),
                    lambda: ov.connection.put("/rest/server-hardware/1/powerState", {"powerState": "Off"}),
                    lambda: ov.server_hardware.get_by_name("osd-01").update_power_state({"powerState": "Off", "powerControl": "PressAndHold"})):
        try:
            attempt()
            raise AssertionError("a write went through the OneView guard")
        except common.ReadOnlyViolation:
            pass
    assert all(m == "GET" for m, _ in OV.calls[before:]), OV.calls[before:]
    print("oneview ok")

    # ---- iLO, through HPE's python-ilorest-library
    r, tools = mcp("ilo", [("ilo_summary", {"server_name": "osd-01"}), ("ilo_logs", {"server_name": "osd-01", "only_problems": True}),
                           ("ilo_thermal", {"server_name": "osd-pinned"}), ("ilo_summary", {"server_name": "osd-unverified"}),
                           ("ilo_get", {"server_name": "osd-01", "path": "/redfish/v1/AccountService/Accounts"})])
    assert r[0]["system"]["Model"] == "ProLiant XL420 Gen10 Plus" and r[0]["ilo"]["Model"] == "iLO 5", r[0]
    assert len(r[1]["entries"]) == 1 and "Bay 3 failed" in r[1]["entries"][0]["Message"], r[1]
    assert r[2]["fans"][0]["Name"] == "Fan 1", r[2]                                      # certificate pinned by fingerprint
    assert "give ca_file or fingerprint" in r[3]["error"], r[3]
    assert "not accounts" in r[4]["error"], r[4]
    sessions = [c for c in ILO.calls if c[0] == "POST"]
    assert len(sessions) == 3 and len([c for c in ILO.calls if c[0] == "DELETE"]) == 3, ILO.calls      # every sign-in signed out
    assert ILO.writes({("POST", "/redfish/v1/SessionService/Sessions/"), ("DELETE", "/redfish/v1/SessionService/Sessions/s1/")}) == [], ILO.writes(set())
    cl = ilo.connect("osd-01")
    cl.login(auth="session")
    ilo.path_only(cl)
    before = len(ILO.calls)
    for attempt in (lambda: cl.post("/redfish/v1/Systems/1/Actions/ComputerSystem.Reset/", {"ResetType": "ForceOff"}),
                    lambda: cl.patch("/redfish/v1/Systems/1/", {"IndicatorLED": "Lit"}),
                    lambda: cl.delete("/redfish/v1/Systems/1/LogServices/IML/Entries/")):
        try:
            attempt()
            raise AssertionError("a write went through the iLO guard")
        except common.ReadOnlyViolation:
            pass
    assert len(ILO.calls) == before, ILO.calls[before:]
    cl.logout()
    print("ilo ok")

    # ---- HTTP: the bearer token, /health, and a tool call
    with socket.socket() as so:
        so.bind(("127.0.0.1", 0)); port = so.getsockname()[1]
    srv = subprocess.Popen([sys.executable, "-m", "sds_mcp", "ceph", "--http", f"127.0.0.1:{port}"], cwd=HERE,
                           env=dict(ENV, MCP_SERVER_TOKEN="http-token-0123456789"), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1).read(); break
            except OSError:
                time.sleep(0.1)

        def post(msg, token="http-token-0123456789"):
            req = urllib.request.Request(f"http://127.0.0.1:{port}/mcp", data=json.dumps(msg).encode(), method="POST", headers={
                "Content-Type": "application/json", "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-06-18",
                **({"Authorization": "Bearer " + token} if token else {})})
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    return resp.status, json.loads(resp.read() or b"null")
            except urllib.error.HTTPError as e:
                return e.code, None
        assert post({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, token="")[0] == 401
        assert post({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, token="wrong-token-0123456789")[0] == 401
        code, got = post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}})
        assert code == 200 and got["result"]["serverInfo"]["name"] == "ceph", (code, got)
        code, got = post({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "ceph_capacity", "arguments": {"cluster_name": "prod-a"}}})
        assert code == 200 and "error" in json.dumps(got), got                                 # the stand-in has no capacity: an error, not a crash
    finally:
        srv.kill()
    r = subprocess.run([sys.executable, "-m", "sds_mcp", "ceph", "--http", "127.0.0.1:1"], cwd=HERE, env=ENV, capture_output=True, text=True, timeout=30)
    assert r.returncode != 0 and "MCP_SERVER_TOKEN" in r.stderr, r.stderr
    print("http ok")
    print("all server tests passed")
finally:
    for f in (SG, CEPH, OV, ILO):
        f.srv.shutdown()
    shutil.rmtree(WORK, ignore_errors=True)
