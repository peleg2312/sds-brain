#!/usr/bin/env python3
"""Build the container images that serve the brain's connections over HTTP, from this repository only:

    python3 connections/http/build.py grafana   [--base <image>] [--arch x86_64|arm64] [--save grafana-mcp.tar]
    python3 connections/http/build.py objectify [--base <image>] [--save objectify-mcp.tar]

grafana    the official Grafana MCP server v2.2.0 from connections/grafana/vendor: the archive and the executable are
           checked against release-manifest.json before anything is built; it serves streamable HTTP itself.
objectify  connections/objectify/server.py (stdio) behind gateway.py (HTTP, bearer token).

--base     the base image, from your internal registry on a network without the internet (default: Red Hat UBI 9,
           ubi-minimal for grafana, python-312 for objectify).
--save     also write the image as a tar file, to carry it to the VM (`podman load -i <file>` there).
Uses podman when it is installed, else docker. Tags: localhost/sds-brain/<name>-mcp:<version>. Standard library only."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
CONN = os.path.dirname(HERE)
ROOT = os.path.dirname(CONN)
BASES = {"grafana": "registry.access.redhat.com/ubi9/ubi-minimal:latest",
         "objectify": "registry.access.redhat.com/ubi9/python-312:latest"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def stage_grafana(d, arch):
    g = os.path.join(CONN, "grafana")
    manifest = json.load(open(os.path.join(g, "release-manifest.json")))
    asset = next((a for a in manifest["assets"] if a["platform"] == f"Linux_{arch}"), None)
    if not asset:
        sys.exit(f"build: no Linux_{arch} archive in release-manifest.json")
    archive = os.path.join(g, "vendor", asset["name"])
    if sha256(archive) != asset["sha256"]:
        sys.exit(f"build: {asset['name']} does not match its sha256 in release-manifest.json")
    exe = os.path.join(d, "mcp-grafana")
    with tarfile.open(archive, "r:gz") as t, open(exe, "wb") as f:
        f.write(t.extractfile(asset["binary_path"]).read())
    if sha256(exe) != asset["binary_sha256"]:
        sys.exit("build: the unpacked executable does not match release-manifest.json")
    os.chmod(exe, 0o755)
    for f in ("grafana-entrypoint.sh",):
        shutil.copy(os.path.join(HERE, f), d)
    shutil.copy(os.path.join(g, "LICENSE.upstream"), d)
    return manifest["version"], "linux/" + {"x86_64": "amd64", "arm64": "arm64"}[arch]


def stage_objectify(d):
    o = os.path.join(CONN, "objectify")
    for f in ("server.py", "config.example.json", "observed-endpoints.json"):
        shutil.copy(os.path.join(o, f), d)
    shutil.copy(os.path.join(HERE, "gateway.py"), d)
    r = subprocess.run(["git", "-C", ROOT, "log", "-1", "--format=%h", "--", "connections/objectify", "connections/http"],
                       capture_output=True, text=True)
    return (r.stdout.strip() or "dev"), ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", choices=sorted(BASES))
    ap.add_argument("--base")
    ap.add_argument("--arch", default="x86_64", choices=["x86_64", "arm64"])
    ap.add_argument("--save")
    a = ap.parse_args()
    tool = shutil.which("podman") or shutil.which("docker")
    if not tool:
        sys.exit("build: neither podman nor docker is installed")
    d = tempfile.mkdtemp(prefix=f"sds-{a.name}-")
    try:
        version, platform = stage_grafana(d, a.arch) if a.name == "grafana" else stage_objectify(d)
        shutil.copy(os.path.join(HERE, f"{a.name}.Containerfile"), os.path.join(d, "Containerfile"))
        tag = f"localhost/sds-brain/{a.name}-mcp:{version}"     # the same name under podman and docker
        cmd = [tool, "build", "-t", tag, "-f", os.path.join(d, "Containerfile"), "--build-arg", f"BASE={a.base or BASES[a.name]}"]
        cmd += (["--platform", platform] if platform else []) + [d]
        print("build:", " ".join(cmd), flush=True)
        if subprocess.run(cmd).returncode:
            sys.exit("build: the image build failed (above)")
        print(f"built {tag}")
        if a.save:
            if subprocess.run([tool, "save", "-o", a.save, tag]).returncode:
                sys.exit("build: saving the image failed")
            print(f"saved {a.save}: on the VM, podman load -i {os.path.basename(a.save)}")
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
