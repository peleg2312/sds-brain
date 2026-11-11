#!/usr/bin/env python3
"""Build the container images that serve the brain's connections over HTTP, from this repository only:

    python3 connections/http/build.py grafana [--base <image>] [--arch x86_64|arm64] [--save grafana-mcp.tar]
    python3 connections/http/build.py gateway [--base <image>] [--save mcp-gateway.tar]
    python3 connections/http/build.py docs    [--base <image>] [--save docs-mcp.tar]
    python3 connections/http/build.py servers [--base <image>] [--pip-index-url <mirror>] [--wheelhouse <dir>] [--save sds-mcp.tar]
    python3 connections/http/build.py --download-wheels <dir>        (a connected machine: the wheelhouse for the line above)

grafana  the official Grafana MCP server v2.2.0 from connections/grafana/vendor: the archive and the executable are
         checked against release-manifest.json before anything is built; it serves streamable HTTP itself.
gateway  gateway.py (bearer token over HTTP) with Objectify's adapter: Objectify by default, or in front of okp-mcp.
docs     the docs service: the library of docs/ indexed into the image, the team's knowledge from the repository.
servers  the read-only StorageGRID, Ceph, OneView and iLO servers (connections/servers), one image for the four.
         Their Python packages come from PyPI, from your internal mirror (--pip-index-url), or from a wheelhouse made
         on a connected machine (--download-wheels <dir>, then --wheelhouse <dir> where the image is built). Simplest:
         build on a connected machine and carry the image (--save).

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
         "gateway": "registry.access.redhat.com/ubi9/python-312:latest",
         "docs": "registry.access.redhat.com/ubi9/python-312:latest",
         "servers": "registry.access.redhat.com/ubi9/python-312:latest"}
IMAGES = {"grafana": "grafana-mcp", "gateway": "mcp-gateway", "docs": "docs-mcp", "servers": "sds-mcp"}


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


def commit_of(*paths):
    r = subprocess.run(["git", "-C", ROOT, "log", "-1", "--format=%h", "--"] + list(paths), capture_output=True, text=True)
    return r.stdout.strip() or "dev"


def stage_gateway(d):
    o = os.path.join(CONN, "objectify")
    for f in ("server.py", "config.example.json", "observed-endpoints.json"):
        shutil.copy(os.path.join(o, f), d)
    shutil.copy(os.path.join(HERE, "gateway.py"), d)
    return commit_of("connections/objectify", "connections/http/gateway.py"), ""


def stage_docs(d):
    plug = os.path.join(ROOT, "brain-sds")
    shutil.copytree(os.path.join(plug, "tools"), os.path.join(d, "tools"), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    sys.path.insert(0, os.path.join(plug, "tools"))
    import docs_server                                          # the committed index when it matches docs/, else built now
    if not docs_server.prebuilt_fresh():
        print("build: library/docs.db does not match docs/: indexing now (commit library/ afterwards)")
        docs_server.build_library()
    shutil.copy(docs_server.PREBUILT, os.path.join(d, "docs.db"))
    shutil.copy(os.path.join(plug, "team.json"), d)
    shutil.copy(os.path.join(HERE, "docs-serve.py"), d)
    return commit_of("docs", "brain-sds/tools", "connections/http/docs-serve.py"), ""


PLATFORM = ["--platform", "manylinux2014_x86_64", "--platform", "manylinux_2_17_x86_64", "--platform", "manylinux_2_28_x86_64",
            "--implementation", "cp", "--python-version", "3.12", "--only-binary=:all:"]


def download_wheels(dest):
    """everything the servers image installs, for Linux x86-64 / Python 3.12 (the UBI 9 python-312 image), into dest.
    jsonpath-rw (needed by HPE's iLO library) exists only as source: it comes as a source package, with setuptools to
    build it offline; the rest as wheels."""
    os.makedirs(dest, exist_ok=True)
    req = [l.split("#", 1)[0].strip() for l in open(os.path.join(CONN, "servers", "requirements.txt")) if l.split("#", 1)[0].strip()]
    ilo = [r for r in req if r.startswith("python-ilorest-library")]
    rest = [r for r in req if not r.startswith("python-ilorest-library")]
    pip = [sys.executable, "-m", "pip", "download", "-q", "-d", dest]
    steps = [pip + ["--no-deps"] + PLATFORM + ilo,                                          # the iLO library itself (a wheel)
             pip + ["--no-deps", "--no-binary=:all:", "jsonpath-rw"],                       # its source-only dependency
             pip + PLATFORM + rest + ["jsonpatch", "jsonpointer", "six", "urllib3", "decorator", "ply", "setuptools", "wheel"]]
    for cmd in steps:
        if subprocess.run(cmd).returncode:
            sys.exit("build: downloading the wheels failed (above)")
    print(f"{len(os.listdir(dest))} packages in {dest}: carry the folder, then build.py servers --wheelhouse {dest}")


def stage_servers(d, wheelhouse):
    src = os.path.join(CONN, "servers")
    shutil.copytree(os.path.join(src, "sds_mcp"), os.path.join(d, "sds_mcp"), ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy(os.path.join(src, "requirements.txt"), d)
    shutil.copy(os.path.join(ROOT, "brain-sds", "tools", "stub_mcp.py"), d)
    os.makedirs(os.path.join(d, "wheels"))
    if wheelhouse:
        for f in os.listdir(wheelhouse):
            if f.endswith((".whl", ".tar.gz", ".zip")):
                shutil.copy(os.path.join(wheelhouse, f), os.path.join(d, "wheels"))
    return commit_of("connections/servers"), ""


def main():
    ap = argparse.ArgumentParser()
    if sys.argv[1:2] == ["--download-wheels"] and len(sys.argv) == 3:
        return download_wheels(sys.argv[2])
    ap.add_argument("name", choices=sorted(BASES))
    ap.add_argument("--base")
    ap.add_argument("--arch", default="x86_64", choices=["x86_64", "arm64"])
    ap.add_argument("--save")
    ap.add_argument("--wheelhouse", help="servers: install the Python packages from this folder instead of PyPI")
    ap.add_argument("--pip-index-url", help="servers: your internal PyPI mirror (Nexus, Artifactory, devpi)")
    a = ap.parse_args()
    tool = shutil.which("podman") or shutil.which("docker")
    if not tool:
        sys.exit("build: neither podman nor docker is installed")
    d = tempfile.mkdtemp(prefix=f"sds-{a.name}-")
    try:
        version, platform = stage_grafana(d, a.arch) if a.name == "grafana" else stage_gateway(d) if a.name == "gateway" else \
            stage_servers(d, a.wheelhouse) if a.name == "servers" else stage_docs(d)
        shutil.copy(os.path.join(HERE, f"{a.name}.Containerfile"), os.path.join(d, "Containerfile"))
        tag = f"localhost/sds-brain/{IMAGES[a.name]}:{version}"     # the same name under podman and docker
        cmd = [tool, "build", "-t", tag, "-f", os.path.join(d, "Containerfile"), "--build-arg", f"BASE={a.base or BASES[a.name]}"]
        cmd += (["--platform", platform] if platform else []) + (["--build-arg", f"PIP_INDEX_URL={a.pip_index_url}"] if a.pip_index_url else []) + [d]
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
