#!/usr/bin/env python3
"""Start the official Grafana MCP server shipped in vendor/ (nothing is downloaded), read-only.

    python3 connections/grafana/launch.py            what the plugin runs (brain-sds/tools/connect.py grafana)
    python3 connections/grafana/launch.py --check    verify the archive for this machine and show the configuration

Configuration (your shell profile; see README.md):
    SDS_GRAFANA_URL      https://grafana.example.internal
    SDS_GRAFANA_TOKEN    a service-account token with the Viewer role
    SDS_GRAFANA_CA_FILE  optional: the CA certificate of your Grafana

Not configured: a one-tool server that says so (no failed server in the session). The archive for this OS / CPU is
checked against the sha256 in release-manifest.json and unpacked once into .cache/bin/. The server runs with
--disable-write and only the read categories below. Standard library only."""
import hashlib
import json
import os
import platform
import re
import sys
import tarfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "brain-sds", "tools"))
FLAGS = ["-t", "stdio", "--disable-write", "--usage-stats=disabled",
         "--enabled-tools=search,datasource,dashboard,elasticsearch,prometheus"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def binary():
    """the verified executable for this machine, unpacked once; raises ValueError with what is wrong"""
    manifest = json.load(open(os.path.join(HERE, "release-manifest.json")))
    arch = {"amd64": "x86_64", "x86_64": "x86_64", "aarch64": "arm64", "arm64": "arm64"}.get(platform.machine().lower(), platform.machine())
    key = f"{platform.system()}_{arch}"
    asset = next((a for a in manifest["assets"] if a["platform"] == key), None)
    if not asset:
        raise ValueError(f"no Grafana MCP archive for {key} in connections/grafana/vendor "
                         f"(shipped: {', '.join(a['platform'] for a in manifest['assets'])})")
    out_dir = os.path.join(ROOT, ".cache", "bin", f"mcp-grafana-{manifest['version']}-{key}")
    exe = os.path.join(out_dir, asset["binary_path"])
    if os.path.isfile(exe) and os.path.getsize(exe) == asset["binary_size_bytes"] and sha256(exe) == asset["binary_sha256"]:
        return exe, manifest["version"]
    archive = os.path.join(HERE, "vendor", asset["name"])
    if not os.path.isfile(archive):
        raise ValueError(f"{archive} is missing")
    if sha256(archive) != asset["sha256"]:
        raise ValueError(f"{asset['name']} does not match the sha256 in release-manifest.json")
    os.makedirs(out_dir, exist_ok=True)
    if archive.endswith(".zip"):
        with zipfile.ZipFile(archive) as z, open(exe, "wb") as f:
            f.write(z.read(asset["binary_path"]))
    else:
        with tarfile.open(archive, "r:gz") as t, open(exe, "wb") as f:
            f.write(t.extractfile(asset["binary_path"]).read())
    os.chmod(exe, 0o755)
    if sha256(exe) != asset["binary_sha256"]:
        os.remove(exe)
        raise ValueError("the unpacked executable does not match the sha256 in release-manifest.json")
    return exe, manifest["version"]


def main():
    url, token = os.environ.get("SDS_GRAFANA_URL", "").strip(), os.environ.get("SDS_GRAFANA_TOKEN", "").strip()
    ca = os.environ.get("SDS_GRAFANA_CA_FILE", "").strip()
    problem = ""
    try:
        exe, version = binary()
    except (ValueError, OSError, KeyError) as e:
        exe, version, problem = "", "?", str(e)
    if not problem and url and not re.fullmatch(r"https://[^\s/@?#]+(/[^\s?#@]*)?", url):
        problem = "SDS_GRAFANA_URL must be an https:// address without credentials, query or fragment"
    if not problem and token and re.search(r"[\x00-\x1f\x7f]", token):
        problem = "SDS_GRAFANA_TOKEN contains control characters"
    if not problem and not (url and token):
        problem = ("Grafana is not configured on this machine. In your shell profile set SDS_GRAFANA_URL (https://...) and "
                   "SDS_GRAFANA_TOKEN (a service-account token with the Viewer role), optionally SDS_GRAFANA_CA_FILE, then "
                   "start a new session. Details: connections/grafana/README.md")
    if not problem and ca and not os.path.isfile(ca):
        problem = f"SDS_GRAFANA_CA_FILE names a file that does not exist: {ca}"
    if "--check" in sys.argv[1:]:
        print(f"grafana: {'ready: ' + url if not problem else problem}" + (f" (mcp-grafana {version}, {exe})" if exe else ""))
        return 0 if exe else 1
    if problem:
        import stub_mcp
        return stub_mcp.serve("grafana", "grafana_setup", "Grafana is not connected yet: call this to see what is missing.", problem)
    # only this connection: no Grafana settings, trace exporters or web proxies inherited from the person's shell
    env = {k: v for k, v in os.environ.items() if k != "SDS_GRAFANA_TOKEN" and not k.upper().startswith(("GRAFANA_", "OTEL_"))
           and k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")}
    env.update(GRAFANA_URL=url, GRAFANA_SERVICE_ACCOUNT_TOKEN=token, GRAFANA_USAGE_STATS="disabled", DO_NOT_TRACK="1")
    os.execve(exe, [exe] + FLAGS + (["--tls-ca-file", ca] if ca else []), env)


if __name__ == "__main__":
    sys.exit(main() or 0)
