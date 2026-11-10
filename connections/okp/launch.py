#!/usr/bin/env python3
"""The Red Hat Offline Knowledge Portal for the plugin (its `okp` server): a stdio bridge to the okp-mcp service, which
speaks MCP over HTTP. Read-only by nature: okp-mcp only searches the portal.

Where the service is (the first one set wins):
    SDS_OKP_URL          in a person's shell profile, e.g. http://127.0.0.1:8000/mcp (a tunnel to the team's host)
    config.json "url"    beside this file, committed: the team's shared endpoint
    SDS_OKP_TOKEN        optional, shell profile only: a bearer token when a proxy in front of the service asks for one

Nothing configured, or the service does not answer at session start: a one-tool server (okp_setup) that says what is
missing, instead of a failed server. Standard library only.
    python3 connections/okp/launch.py --check     where it would connect and whether the service answers"""
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "brain-sds", "tools"))
HOW = "connections/okp/README.md"


def settings():
    url = os.environ.get("SDS_OKP_URL", "").strip()
    if not url:
        try:
            with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
                url = str(json.load(f).get("url") or "").strip()
        except (OSError, ValueError):
            url = ""
    return url, os.environ.get("SDS_OKP_TOKEN", "").strip()


def opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))     # an internal host: never through a web proxy


def post(url, token, line, session=None, timeout=120):
    """one JSON-RPC message to the service: (session id, [answers])"""
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
               **({"Authorization": "Bearer " + token} if token else {}), **({"Mcp-Session-Id": session} if session else {})}
    with opener().open(urllib.request.Request(url, data=line.encode(), method="POST", headers=headers), timeout=timeout) as r:
        sid = r.headers.get("Mcp-Session-Id") or session
        body = r.read().decode("utf-8", "replace")
        if "text/event-stream" in (r.headers.get("Content-Type") or ""):
            out, data = [], []
            for raw in body.splitlines() + [""]:
                if raw.startswith("data:"):
                    data.append(raw[5:].lstrip())
                elif not raw.strip() and data:
                    out.append("\n".join(data))
                    data = []
            return sid, [m for m in out if m.strip()]
        return sid, [body] if body.strip() else []


def probe(url, token):
    """"" when the service answers an initialize, else why not"""
    hello = json.dumps({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "sds-brain-check", "version": "1"}}})
    try:
        _, answers = post(url, token, hello, timeout=4)
        return "" if any('"result"' in a for a in answers) else "it answered without an initialize result"
    except urllib.error.HTTPError as e:
        return f"it answered HTTP {e.code}"
    except Exception as e:
        return f"{e.__class__.__name__}: {getattr(e, 'reason', e)}"


def bridge(url, token):
    session = None
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            mid = json.loads(line).get("id")
        except (ValueError, AttributeError):
            continue
        try:
            session, answers = post(url, token, line, session)
        except Exception as e:
            why = f"HTTP {e.code}" if isinstance(e, urllib.error.HTTPError) else str(getattr(e, "reason", e))
            answers = [json.dumps({"jsonrpc": "2.0", "id": mid, "error": {"code": -32000, "message": f"okp unreachable: {why}"}})] \
                if mid is not None else []
        for a in answers:
            sys.stdout.write(a.strip() + "\n")
        sys.stdout.flush()
    return 0


def main():
    url, token = settings()
    problem = ("The Red Hat offline portal is not configured: set SDS_OKP_URL in your shell profile (or the team's url in "
               f"connections/okp/config.json) and start a new session. Details: {HOW}") if not url else ""
    if url and not problem:
        why = probe(url, token)
        if why:
            problem = (f"The Red Hat offline portal at {url} did not answer ({why}): is the okp-mcp service running, and "
                       f"the tunnel up when it is on another host? Details: {HOW}")
    if "--check" in sys.argv[1:]:
        print(f"okp: {'ready: ' + url if not problem else problem}")
        return 0 if not problem else 1
    if problem:
        import stub_mcp
        return stub_mcp.serve("okp", "okp_setup", "The Red Hat offline portal is not connected: call this to see what is missing.", problem)
    return bridge(url, token)


if __name__ == "__main__":
    sys.exit(main() or 0)
