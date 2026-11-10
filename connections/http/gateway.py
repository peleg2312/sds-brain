#!/usr/bin/env python3
"""Put a bearer token (and optional TLS) in front of an MCP server, over HTTP. Standard library only, Python 3.9.

    python3 gateway.py --listen 0.0.0.0:8000 --objectify                 Objectify's stdio adapter ($OBJECTIFY_CONFIG)
    python3 gateway.py --listen 0.0.0.0:8000 -- <command...>             any stdio MCP server
    python3 gateway.py --listen 0.0.0.0:8080 --upstream http://127.0.0.1:8000/mcp     an HTTP MCP server without
                                                                          authentication of its own (okp-mcp)

stdio: one child process, started once, shared by every client. upstream: one session with the server, its event-
stream answers turned into plain JSON. Either way JSON answers (MCP streamable HTTP without event streams).

Environment: MCP_SERVER_TOKEN (required: requests without `Authorization: Bearer <it>` get 401), MCP_TLS_CERT and
MCP_TLS_KEY (both, for HTTPS). Endpoints: POST /mcp, GET /health. The child's initialize answer is reused for every
client; requests reach it one at a time with ids of the gateway's own, so two clients never see each other's answers."""
import argparse
import hmac
import itertools
import json
import os
import ssl
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_BODY = 1 << 20


class Child:
    def __init__(self, cmd):
        self.cmd, self.lock, self.ids = cmd, threading.Lock(), itertools.count(1)
        self.proc, self.init = None, None
        self.start()

    def start(self):
        self.proc = subprocess.Popen(self.cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.init = self._call({"jsonrpc": "2.0", "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "sds-gateway", "version": "1"}}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(self, msg):
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def _call(self, msg):
        mid = next(self.ids)
        self._send(dict(msg, id=mid))
        for line in self.proc.stdout:
            try:
                got = json.loads(line)
            except ValueError:
                continue
            if got.get("id") == mid:
                return got
        raise OSError("the server stopped")

    def call(self, msg):
        """one client request: (answer or None for a notification)"""
        with self.lock:
            if self.proc.poll() is not None:
                self.start()                                   # the child exited: a fresh one
            if msg.get("method") == "initialize":
                return dict(self.init, id=msg.get("id"))
            if "id" not in msg:
                if msg.get("method") != "notifications/initialized":
                    self._send(msg)
                return None
            got = self._call(msg)
            return dict(got, id=msg["id"])


class Upstream:
    """an HTTP MCP server: one session, answers in JSON or as an event stream"""

    def __init__(self, url):
        import urllib.request
        self.url, self.lock, self.session, self.init = url, threading.Lock(), None, None
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.token = os.environ.get("MCP_UPSTREAM_TOKEN", "").strip()

    def _post(self, msg):
        import urllib.request
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                   **({"Authorization": "Bearer " + self.token} if self.token else {}),
                   **({"Mcp-Session-Id": self.session} if self.session else {})}
        req = urllib.request.Request(self.url, data=json.dumps(msg).encode(), method="POST", headers=headers)
        with self.opener.open(req, timeout=120) as r:
            self.session = r.headers.get("Mcp-Session-Id") or self.session
            body = r.read().decode("utf-8", "replace")
            if "text/event-stream" not in (r.headers.get("Content-Type") or ""):
                return [json.loads(body)] if body.strip() else []
        out, data = [], []
        for line in body.splitlines() + [""]:
            if line.startswith("data:"):
                data.append(line[5:].lstrip())
            elif not line.strip() and data:
                out.append(json.loads("\n".join(data)))
                data = []
        return out

    def _start(self):
        self.session = None
        got = self._post({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "sds-gateway", "version": "1"}}})
        self.init = next(m for m in got if m.get("id") == 0)
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call(self, msg):
        with self.lock:
            if self.init is None:
                self._start()
            if msg.get("method") == "initialize":
                return dict(self.init, id=msg.get("id"))
            if "id" not in msg:
                if msg.get("method") != "notifications/initialized":
                    self._post(msg)
                return None
            try:
                got = self._post(msg)
            except Exception:
                self._start()                                  # the session expired or the server restarted: once more
                got = self._post(msg)
            return next((m for m in got if m.get("id") == msg.get("id")), None) or \
                {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32000, "message": "no answer from the server"}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", default="0.0.0.0:8000")
    ap.add_argument("--upstream", help="an HTTP MCP server to front, e.g. http://127.0.0.1:8000/mcp")
    ap.add_argument("--objectify", action="store_true", help="Objectify's adapter beside this file, with $OBJECTIFY_CONFIG")
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd[:1] == ["--"] else a.cmd
    if a.objectify:
        here = os.path.dirname(os.path.abspath(__file__))
        conf = os.environ.get("OBJECTIFY_CONFIG") or ""
        if not os.path.isfile(conf):                    # no configuration mounted yet: the disabled example (status only)
            if conf:
                print(f"gateway: {conf} not found: running the disabled example", file=sys.stderr, flush=True)
            conf = os.path.join(here, "config.example.json")
        cmd = [sys.executable, os.path.join(here, "server.py"), "--config", conf]
    token = os.environ.get("MCP_SERVER_TOKEN", "").strip()
    if len(token) < 16 or not (cmd or a.upstream):
        sys.exit("gateway: MCP_SERVER_TOKEN (16 characters at least) and a server (--upstream, --objectify or a command) are required")
    child = Upstream(a.upstream) if a.upstream else Child(cmd)

    class H(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

        def send(self, code, body=None):
            data = json.dumps(body).encode() if body is not None else b""
            self.send_response(code)
            if body is not None:
                self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self.send(200, {"status": "ok"}) if self.path == "/health" else self.send(404, {"error": "not found"})

        def do_DELETE(self):
            self.send(200, {})

        def do_POST(self):
            if self.path.split("?", 1)[0] != "/mcp":
                return self.send(404, {"error": "not found"})
            auth = self.headers.get("Authorization", "")
            if not hmac.compare_digest(auth.encode(), ("Bearer " + token).encode()):
                return self.send(401, {"error": "bearer token required"})
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > MAX_BODY:
                return self.send(413 if n > MAX_BODY else 400, {"error": "bad request body"})
            try:
                msg = json.loads(self.rfile.read(n))
            except ValueError:
                return self.send(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
            if not isinstance(msg, dict):
                return self.send(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "one message per request"}})
            try:
                got = child.call(msg)
            except Exception as e:
                return self.send(200, {"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32000, "message": f"server error: {e}"}})
            self.send(202) if got is None else self.send(200, got)

    host, _, port = a.listen.rpartition(":")
    srv = ThreadingHTTPServer((host or "0.0.0.0", int(port)), H)
    cert, key = os.environ.get("MCP_TLS_CERT"), os.environ.get("MCP_TLS_KEY")
    if cert and key:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert, key)
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    print(f"gateway: {'https' if cert and key else 'http'}://{a.listen}/mcp -> {a.upstream or ' '.join(cmd)}", file=sys.stderr, flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
