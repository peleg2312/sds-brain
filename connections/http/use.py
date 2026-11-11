#!/usr/bin/env python3
"""Point one of the plugin's connections at a server that runs over HTTP (a container on the VM), or back to the stdio
launcher every person runs on their own machine:

    python3 connections/http/use.py grafana   https://vm.example.internal:8444/mcp --token-file /root/grafana-mcp.token
    python3 connections/http/use.py objectify https://vm.example.internal:8445/mcp --token-file /root/objectify-mcp.token
    python3 connections/http/use.py okp       https://okp.example.internal/mcp     [--token-file ...]
    python3 connections/http/use.py docs-http https://sds-docs.apps.example/mcp?team=sds --token-file docs.token
    python3 connections/http/use.py ceph      https://sds-ceph.apps.example/mcp --token-file ceph.token   (also storagegrid, oneview, ilo)
    python3 connections/http/use.py grafana   --stdio          (docs-http: --stdio removes it, docs-local takes over)

It rewrites that server's entry in brain-sds/.mcp.json (the name stays, so the guard, the tool map and the skills keep
working); commit and push it, and every member's plugin uses it from their next session. The token is written into
the file, as for docs-http: everyone with access to the team repository can read it, so give the server read-only
upstream credentials and change the token when someone leaves. Standard library only."""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MCP = os.path.join(os.path.dirname(os.path.dirname(HERE)), "brain-sds", ".mcp.json")
NAMES = ("grafana", "objectify", "okp", "docs-http", "storagegrid", "ceph", "oneview", "ilo")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", choices=NAMES)
    ap.add_argument("url", nargs="?")
    ap.add_argument("--token-file")
    ap.add_argument("--stdio", action="store_true")
    a = ap.parse_args()
    cfg = json.load(open(MCP, encoding="utf-8"))
    if a.stdio and a.name == "docs-http":
        cfg["mcpServers"].pop("docs-http", None)
        with open(MCP, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
            f.write("\n")
        print("brain-sds/.mcp.json: docs-http removed (docs-local indexes docs/ on each machine); commit and push it")
        return 0
    if a.stdio:
        entry = {"type": "stdio", "command": "python3", "args": ["${CLAUDE_PLUGIN_ROOT}/tools/connect.py", a.name]}
    else:
        if not a.url or not re.fullmatch(r"https?://[^\s/@?#]+(/[^\s?#@]*)?(\?[^\s#@]*)?", a.url):
            sys.exit("use: give the server's url (https://<host>:<port>/mcp), or --stdio")
        if a.name == "docs-http" and "?team=" not in a.url:
            sys.exit("use: docs-http needs ?team=<team> at the end of its url (?team=sds)")
        if a.url.startswith("http://"):
            print("use: note: plain http sends the token unencrypted; use https (the VM's certificate) outside a lab")
        token = ""
        if a.token_file:
            token = open(a.token_file, encoding="utf-8").read().strip()
            if len(token) < 16 or re.search(r"\s", token):
                sys.exit("use: the token must be one word of 16 characters at least")
        elif a.name != "okp":                           # okp may sit behind a proxy of its own
            sys.exit("use: --token-file is required: the server must not answer without a token")
        entry = {"type": "http", "url": a.url, **({"headers": {"Authorization": "Bearer " + token}} if token else {})}
    cfg["mcpServers"][a.name] = entry
    with open(MCP, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    shown = dict(entry, **({"headers": {"Authorization": "Bearer <token>"}} if entry.get("headers") else {}))
    print(f"brain-sds/.mcp.json: {a.name} = {json.dumps(shown)}\n"
          f"commit and push it: git add brain-sds/.mcp.json && git commit -m 'SDS brain: {a.name} over {'stdio' if a.stdio else 'http'}' && git push")
    return 0


if __name__ == "__main__":
    sys.exit(main())
