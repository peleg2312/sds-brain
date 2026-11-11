#!/usr/bin/env python3
"""Regenerate sds_mcp/ceph_api.json, the Ceph dashboard API reads the ceph server may call, from Ceph's own OpenAPI
descriptions (src/pybind/mgr/dashboard/openapi.yaml of each release branch). Needs PyYAML; run where GitHub is
reachable, or pass the files:

    python3 connections/servers/gen_ceph_api.py                       fetches squid and tentacle from github.com/ceph/ceph
    python3 connections/servers/gen_ceph_api.py squid=openapi-squid.yaml tentacle=openapi-tentacle.yaml

Every GET path with its media version (Accept: application/vnd.ceph.api.v<version>+json), the union of the releases;
paths that hand out other systems' credentials or the dashboard's own users are left out (DENY)."""
import json
import os
import re
import sys
import urllib.request

import yaml

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sds_mcp", "ceph_api.json")
DENY = re.compile(r"^/api/(auth|user|settings|feedback|multi-cluster|cluster/user|telemetry|motd|login|logout|"
                  r"iscsi/discoveryauth|smb/joinauth|smb/usersgroups|rgw/user/get_emails|rgw/realm/get_realm_tokens|"
                  r"rgw/bucket/getEncryptionConfig|mgr/module|"
                  r"rgw/user/[^/]+/(keys|subuser)|rgw/accounts/[^/]+/keys)", re.I)        # credentials, other systems' tokens, people


def load(src):
    if src.startswith("http"):
        with urllib.request.urlopen(src, timeout=120) as r:
            return yaml.safe_load(r.read())
    return yaml.safe_load(open(src, encoding="utf-8"))


def main():
    sources = dict(a.split("=", 1) for a in sys.argv[1:]) or {
        r: f"https://raw.githubusercontent.com/ceph/ceph/{r}/src/pybind/mgr/dashboard/openapi.yaml" for r in ("squid", "tentacle")}
    paths, releases = {}, {}
    for release, src in sources.items():
        spec = load(src)
        releases[release] = src
        for path, ops in (spec.get("paths") or {}).items():
            get = ops.get("get") if isinstance(ops, dict) else None
            if not get or DENY.match(path):
                continue
            content = ((get.get("responses") or {}).get("200") or {}).get("content") or {}
            m = next((re.search(r"vnd\.ceph\.api\.v([\d.]+)\+json", k) for k in content), None)
            version = m.group(1) if m else "1.0"
            entry = paths.setdefault(path, {"version": version, "releases": []})
            entry["releases"].append(release)
            entry["version"] = version                                # the newest release's, when they differ
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"source": releases, "paths": dict(sorted(paths.items()))}, f, indent=1)
        f.write("\n")
    print(f"{OUT}: {len(paths)} GET paths from {', '.join(releases)}")


if __name__ == "__main__":
    main()
