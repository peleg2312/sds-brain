"""Shared by the SDS brain's MCP servers (StorageGRID, Ceph, HPE OneView, HPE iLO): the inventory of systems, their
credentials, TLS that is always verified, an HTTP client that can only read, bounded and redacted answers, and the
stdio / HTTP runner. Built on the official MCP Python SDK (mcp 2.x, MCPServer).

Inventory: a JSON file, $SDS_MCP_CONFIG (default: targets.json beside this package's folder), no secrets in it:
    {"storagegrid": {"grid-a": {"url": "https://admin-a.example", "ca_file": "ca.pem"}},
     "ceph":        {"prod-a": {"url": "https://mgr-a.example:8443"}},
     "oneview":     {"ov-1": {"host": "oneview.example", "login_domain": "LOCAL"}},
     "ilo":         {"defaults": {"ca_file": "ilo-ca.pem"},
                     "servers": {"osd-01": {"host": "osd-01-ilo.example"}, "osd-02": {"host": "10.0.0.12", "fingerprint": "AB:CD:..."}}}}
ca_file paths are relative to the inventory file. Credentials come from the environment (a Kubernetes / Podman secret):
SDS_<KIND>_<NAME>_USERNAME / _PASSWORD, else the kind's shared read-only account SDS_<KIND>_USERNAME / _PASSWORD
(e.g. SDS_CEPH_PROD_A_PASSWORD, SDS_ILO_USERNAME). Use read-only accounts: StorageGRID a group with read-only access,
Ceph the dashboard's read-only role, OneView the Read only role, iLO the Read Only role."""
import functools
import json
import os
import re
import ssl
import sys
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_CHARS = 60_000                                    # one answer; more is cut, and the answer says so
SECRET_KEY = re.compile(r"(passw(or)?d|passwd|secret|token|private|credential|cookie|authorization|session.?(id|key)|"
                        r"(^|_)keys?$|access.?key|swift_keys|community|ssh.?key)", re.I)


class ReadOnlyViolation(RuntimeError):
    """a request that is not a read reached the client: a bug, never sent"""


class ToolFailure(Exception):
    """a failure the user should see (unknown target, missing credentials, the system answered an error)"""


# ---- inventory and credentials

def config_path():
    return os.environ.get("SDS_MCP_CONFIG") or os.path.join(os.path.dirname(HERE), "targets.json")


@functools.lru_cache(maxsize=1)
def config():
    path = config_path()
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except ValueError as e:
        raise ToolFailure(f"the inventory {path} is not valid JSON: {e}")


def targets(kind):
    """{name: settings} for one kind; for ilo the servers, with the kind's defaults merged in"""
    section = config().get(kind) or {}
    if kind == "ilo":
        defaults = section.get("defaults") or {}
        return {n: dict(defaults, **(s or {})) for n, s in (section.get("servers") or {}).items()}
    return {n: s for n, s in section.items() if isinstance(s, dict)}


def target(kind, name):
    found = targets(kind)
    if name not in found:
        known = ", ".join(sorted(found)[:40]) or "none (the inventory has no " + kind + " section)"
        raise ToolFailure(f"unknown {kind} '{name}'. Known: {known}. The inventory is {config_path()}.")
    return found[name]


def env_name(*parts):
    return "SDS_" + "_".join(re.sub(r"[^A-Za-z0-9]+", "_", p).strip("_").upper() for p in parts)


def credentials(kind, name):
    def pick(field):
        for var in (env_name(kind, name, field), env_name(kind, field)):
            if os.environ.get(var):
                return os.environ[var]
            if os.environ.get(var + "_FILE") and os.path.isfile(os.environ[var + "_FILE"]):
                with open(os.environ[var + "_FILE"], encoding="utf-8") as f:
                    return f.read().strip()
        return ""
    user, password = pick("username"), pick("password")
    if not user or not password:
        raise ToolFailure(f"no credentials for {kind} '{name}': set {env_name(kind, name, 'username')} / _PASSWORD, or the shared "
                          f"{env_name(kind, 'username')} / _PASSWORD (a read-only account)")
    return user, password


def ca_file(settings):
    """the CA file of a target, resolved against the inventory's folder; "" for the system's trust store"""
    ca = settings.get("ca_file") or ""
    if ca and not os.path.isabs(ca):
        ca = os.path.join(os.path.dirname(os.path.abspath(config_path())), ca)
    if ca and not os.path.isfile(ca):
        raise ToolFailure(f"ca_file {ca} does not exist")
    return ca


def tls_context(settings):
    """certificate verification is never switched off: the target's CA file, else the system's trust store"""
    if settings.get("insecure") or settings.get("verify") is False:
        raise ToolFailure("certificate verification cannot be switched off: give the system's CA as ca_file")
    ca = ca_file(settings)
    return ssl.create_default_context(cafile=ca or None)


# ---- the read-only HTTP client (StorageGRID, Ceph)

class ReadOnlyClient:
    """httpx client that sends GET only, plus the exact login / logout requests named in `allow`
    ({("POST", "/api/v4/authorize"), ...}); anything else raises ReadOnlyViolation before it leaves"""

    def __init__(self, base_url, settings, allow=(), headers=None, timeout=30.0):
        import httpx
        self.allow = {(m.upper(), p) for m, p in allow}
        self.http = httpx.Client(base_url=base_url.rstrip("/"), verify=tls_context(settings), trust_env=False,
                                 follow_redirects=False, headers=headers or {}, timeout=httpx.Timeout(timeout, connect=10.0),
                                 event_hooks={"request": [self._guard]})

    def _guard(self, request):
        if request.method in ("GET", "HEAD"):
            return
        if (request.method, request.url.path) not in self.allow:
            raise ReadOnlyViolation(f"{request.method} {request.url.path} refused: this server only reads")

    def request(self, method, path, **kw):
        return self.http.request(method, path, **kw)


def api_error(resp, what):
    """a short error from a response, never its headers"""
    text = ""
    try:
        body = resp.json()
        text = str(body.get("message") or body.get("detail") or body.get("error") or "")[:300] if isinstance(body, dict) else ""
    except ValueError:
        text = resp.text[:200]
    return ToolFailure(f"{what}: HTTP {resp.status_code}" + (f": {text}" if text else ""))


# ---- answers: redacted, projected, bounded

def redact(obj):
    if isinstance(obj, dict):
        return {k: ("<redacted>" if SECRET_KEY.search(str(k)) and v not in (None, "", [], {}) else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    return obj


def pick(obj, path):
    """a dotted path through dicts ("status.health"), None when missing"""
    for part in path.split("."):
        if not isinstance(obj, dict):
            return None
        obj = obj.get(part)
    return obj


def project(items, fields):
    return [{f: pick(i, f) for f in fields} for i in items]


def bounded(answer):
    """the answer as it goes back: redacted, and cut to MAX_CHARS (lists shortened first) with a note"""
    answer = redact(answer)
    text = json.dumps(answer, default=str)
    if len(text) <= MAX_CHARS:
        return answer
    if isinstance(answer, dict):
        for k, v in sorted(answer.items(), key=lambda kv: -len(json.dumps(kv[1], default=str))):
            if isinstance(v, list) and len(v) > 1:
                keep = max(1, int(len(v) * MAX_CHARS / len(text) * 0.9))
                answer = dict(answer, **{k: v[:keep]}, truncated=f"{k}: {keep} of {len(v)} shown; ask for fewer (limit, filters)")
                break
        if len(json.dumps(answer, default=str)) <= MAX_CHARS:
            return answer
    return {"truncated": f"the answer was {len(text)} characters; narrow it (limit, filters, one item)",
            "head": json.dumps(answer, default=str)[:MAX_CHARS - 500]}


def tool(fn):
    """every tool: the answer bounded and redacted; a failure becomes {"error": ...} instead of a stack trace"""
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        try:
            return bounded(fn(*a, **kw))
        except ToolFailure as e:
            return {"error": str(e)}
        except ReadOnlyViolation as e:
            return {"error": f"refused: {e}"}
        except Exception as e:                                   # connection refused, TLS, timeouts
            return {"error": f"{e.__class__.__name__}: {str(e)[:300]}"}
    return wrapper


def read_only(title=None):
    """the annotations every tool here carries: reads only, safe to repeat, talks to a system outside"""
    from mcp_types import ToolAnnotations
    return ToolAnnotations(title=title, readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)


def arg(description, **kw):
    """a parameter's description in the tool's input schema: Annotated[str, arg("...")]"""
    from pydantic import Field
    return Field(description=description, **kw)


def gather(parts):
    """run several reads for one overview; each part's failure is reported in place instead of failing the whole answer.
    parts: {name: callable}"""
    out = {}
    for name, fn in parts.items():
        try:
            out[name] = fn()
        except ToolFailure as e:
            out[name] = {"error": str(e)}
        except Exception as e:
            out[name] = {"error": f"{e.__class__.__name__}: {str(e)[:200]}"}
    return out


def limit_of(n, default=50, most=500):
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = default
    return max(1, min(n or default, most))


# ---- running: stdio (each person's machine) or HTTP with a bearer token (the VM, OpenShift)

def run(server, argv=None):
    """stdio by default; --http HOST:PORT serves MCP's streamable HTTP at /mcp (JSON answers, stateless) with a bearer token
    from MCP_SERVER_TOKEN (16 characters at least; requests without it get 401), /health without; MCP_TLS_CERT and
    MCP_TLS_KEY for HTTPS"""
    argv = sys.argv[1:] if argv is None else argv
    if "--http" not in argv:
        server.run("stdio")
        return 0
    listen = argv[argv.index("--http") + 1] if len(argv) > argv.index("--http") + 1 else "0.0.0.0:8000"
    host, _, port = listen.rpartition(":")
    token = os.environ.get("MCP_SERVER_TOKEN", "").strip()
    if len(token) < 16:
        sys.exit(f"{server.name}: MCP_SERVER_TOKEN must be set (16 characters at least): without it anyone could call the server")
    import hmac
    import uvicorn
    app = server.streamable_http_app(json_response=True, stateless_http=True, host=host or "0.0.0.0")
    expected = ("Bearer " + token).encode()

    async def guarded(scope, receive, send):
        if scope["type"] == "http":
            if scope["path"] == "/health":
                await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": b'{"status": "ok"}'})
                return
            auth = dict(scope.get("headers") or []).get(b"authorization", b"")
            if not hmac.compare_digest(auth, expected):
                await send({"type": "http.response.start", "status": 401, "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": b'{"error": "bearer token required"}'})
                return
        await app(scope, receive, send)
    tls = {"ssl_certfile": os.environ["MCP_TLS_CERT"], "ssl_keyfile": os.environ["MCP_TLS_KEY"]} \
        if os.environ.get("MCP_TLS_CERT") and os.environ.get("MCP_TLS_KEY") else {}
    uvicorn.run(guarded, host=host or "0.0.0.0", port=int(port), log_level="warning", proxy_headers=False, **tls)
    return 0
