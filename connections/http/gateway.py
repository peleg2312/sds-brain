#!/usr/bin/env python3
"""Serve a stdio MCP server over HTTP, for a connection that only speaks stdio (Objectify's adapter): one child
process, started once, shared by every client; JSON answers (MCP streamable HTTP without event streams), a bearer
token on every request, optional TLS. Standard library only, Python 3.9.

    python3 gateway.py --listen 0.0.0.0:8000 -- python3 /app/server.py --config /config/config.local.json

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", default="0.0.0.0:8000")
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd[:1] == ["--"] else a.cmd
    token = os.environ.get("MCP_SERVER_TOKEN", "").strip()
    if len(token) < 16 or not cmd:
        sys.exit("gateway: MCP_SERVER_TOKEN (16 characters at least) and the server command are required")
    child = Child(cmd)

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
    print(f"gateway: {'https' if cert and key else 'http'}://{a.listen}/mcp -> {' '.join(cmd)}", file=sys.stderr, flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
