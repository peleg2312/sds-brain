#!/usr/bin/env python3
"""Connect the SDS brain to the VM's docs service. Run once as root on the VM, from a clone of the team repository whose
`origin` is the team's git url; run it again after documents were added under docs/.

    sudo python3 vm-setup.py      [--host <name the members reach the VM by>] [--remote <https url of the team repository>]

The VM already runs the docs service of the storage team's brain (paas-docs: /mcp?team=<team> over HTTPS with one
token). This script makes SDS a team of that service, without touching the other teams:

  1. library   docs/ of this clone is copied to /opt/paas/libraries/sds/docs/ and indexed there (docs.db). The service
               serves it to team sds instead of the general library.
  2. team      /opt/paas/teams/sds/team.json names the library and this repository's url: the service keeps its own
               clone and re-indexes the team's knowledge every 10 minutes, and at once after a member's push.
  3. plugin    brain-sds/.mcp.json gets the server docs-http (the service's address for team sds and its token) and
               brain-sds/lib/paas-ui.crt the VM's certificate. COMMIT AND PUSH these two files (the script prints the
               commands): every member's plugin then searches the library on the VM and builds nothing locally.

The token is the docs service's one read token; in the plugin it is readable by everyone with access to the team
repository, as for the other teams. The service pulls the repository with the VM's git token for that host
(`paas-user git-token <host>`, once, as for every team). Standard library, Python 3.9.
Paths for a test: PAAS_ROOT (/opt/paas), PAAS_ETC (/etc/paas)."""
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PLUG = os.path.join(HERE, "brain-sds")
ROOT = os.environ.get("PAAS_ROOT") or "/opt/paas"
ETC = os.environ.get("PAAS_ETC") or "/etc/paas"


def say(mark, text):
    print(f"  {mark:<5} {text}")


def readable(folder):
    """every account and the docs service read it: folders 755, files 644"""
    for dp, _, files in os.walk(folder):
        os.chmod(dp, 0o755)
        for f in files:
            os.chmod(os.path.join(dp, f), 0o644)


def setting(name, default):
    try:
        for line in open(os.path.join(ETC, "docs.env"), encoding="utf-8"):
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip() or default
    except OSError:
        pass
    return default


def library(team):
    name = team["library"]
    src, lib = os.path.join(HERE, "docs"), os.path.join(ROOT, "libraries", name)
    dst = os.path.join(lib, "docs")
    products = sorted(os.path.join(v, p) for v in os.listdir(src) if os.path.isdir(os.path.join(src, v))
                      for p in os.listdir(os.path.join(src, v)) if os.path.isdir(os.path.join(src, v, p)))
    for rel in products:                       # the products this repository carries replace their copies; others stay
        shutil.rmtree(os.path.join(dst, rel), ignore_errors=True)
        shutil.copytree(os.path.join(src, rel), os.path.join(dst, rel))
    built = os.path.join(HERE, "library", "docs.db")          # the index built ahead: paas-library then only checks it
    if os.path.isfile(built):
        shutil.copy(built, os.path.join(lib, "docs.db"))
    tool = os.path.join(ROOT, "bin", "paas-library")
    if os.path.isfile(tool):                   # the VM's own indexer: the index matches the service that reads it
        r = subprocess.run([sys.executable, tool, "build", name], env=dict(os.environ, PAAS_LIBRARIES=os.path.join(ROOT, "libraries")),
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"vm-setup: paas-library build {name} failed: {(r.stdout + r.stderr).strip()[-400:]}")
    else:                                      # no paas-library on this VM: the plugin's copy of the same indexer
        sys.path.insert(0, os.path.join(PLUG, "tools", "engine"))
        import docs_index
        docs_index.build(dst, os.path.join(lib, "docs.db"), log=lambda *_: None)
    readable(lib)
    say("ok", f"library {name}: {len(products)} products indexed in {lib}")


def https_url(remote):
    """git@host:group/repo.git and ssh://git@host/group/repo.git as the https url the docs service can pull"""
    m = re.match(r"^(?:ssh://)?git@([^:/]+)[:/](.+)$", remote)
    return f"https://{m.group(1)}/{m.group(2)}" if m else remote


def register(team, remote):
    if not remote:
        r = subprocess.run(["git", "-C", HERE, "remote", "get-url", "origin"], capture_output=True, text=True)
        remote = https_url(r.stdout.strip()) if r.returncode == 0 else ""
    d = os.path.join(ROOT, "teams", team["name"])
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "team.json"), "w", encoding="utf-8") as f:
        json.dump(dict(team, **({"remote": remote} if remote else {})), f, indent=2)
        f.write("\n")
    readable(d)
    if not remote:
        say("FAIL", "this clone has no origin: the service cannot follow the team's knowledge. Add the remote (or --remote <url>) and run again")
        return False
    say("ok", f"team {team['name']}: the docs service indexes the knowledge of {remote}")
    if remote.startswith("http"):
        host = remote.split("://", 1)[1].split("/", 1)[0].split("@")[-1]
        say("note", f"the service pulls it with the VM's git token for {host}: `paas-user git-token {host}` when not stored yet")
    return True


def plugin(team, host):
    scheme = "http" if os.path.exists(os.path.join(ETC, "plain-http")) else "https"
    url = f"{scheme}://{host}:{setting('PAAS_DOCS_PORT', '8443')}/mcp?team={team['name']}"
    try:
        token = open(os.path.join(ETC, "docs-token"), encoding="utf-8").read().strip()
    except OSError as e:
        sys.exit(f"vm-setup: cannot read the docs token ({e}): run as root")
    path = os.path.join(PLUG, ".mcp.json")
    cfg = json.load(open(path, encoding="utf-8"))
    cfg["mcpServers"]["docs-http"] = {"type": "http", "url": url, **({"headers": {"Authorization": "Bearer " + token}} if token else {})}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")
    changed, cert = [path], ""
    if scheme == "https":
        cert = next((c for c in (os.path.join(ETC, "market", "paas-ui.crt"), os.path.join(ROOT, "paas-ui.crt")) if os.path.isfile(c)), "")
        if cert:
            os.makedirs(os.path.join(PLUG, "lib"), exist_ok=True)
            shutil.copy(cert, os.path.join(PLUG, "lib", "paas-ui.crt"))
            changed.append(os.path.join(PLUG, "lib", "paas-ui.crt"))
        else:
            say("FAIL", "the VM's certificate (paas-ui.crt) was not found: members cannot verify the service")
    owner = os.stat(HERE)                       # run with sudo in a person's clone: the files stay that person's
    for p in changed + [os.path.join(PLUG, "lib")]:
        try:
            os.chown(p, owner.st_uid, owner.st_gid)
        except OSError:
            pass
    say("ok", f"plugin: docs-http = {url}")
    return url, token, cert, [os.path.relpath(p, HERE) for p in changed]


def check(url, token, cert, team):
    base = url.split("/mcp", 1)[0]
    ctx = {}
    if url.startswith("https"):
        c = ssl.create_default_context()
        if cert:
            c.load_verify_locations(cert)
        ctx = {"context": c}
    try:
        urllib.request.urlopen(f"{base}/health", timeout=8, **ctx).read()
        req = urllib.request.Request(f"{base}/refresh?team={team}", data=b"", method="POST",
                                     headers={"Content-Length": "0", **({"Authorization": "Bearer " + token} if token else {})})
        urllib.request.urlopen(req, timeout=8, **ctx).read()
        say("ok", f"the docs service answers at {base} and was told to index team {team}")
        return True
    except Exception as e:
        say("FAIL", f"the docs service does not answer at {base} ({e.__class__.__name__}: {e}): systemctl status paas-docs; "
                    "--host <name> when members reach the VM by another name")
        return False


def main():
    args = sys.argv[1:]
    opt = lambda name: args[args.index(name) + 1] if name in args and len(args) > args.index(name) + 1 else ""
    host = opt("--host") or socket.getfqdn()
    if not os.path.isdir(os.path.join(ROOT, "teams")) or not os.path.isfile(os.path.join(ETC, "docs-token")):
        sys.exit(f"vm-setup: this machine has no docs service of the storage team's brain ({ROOT}/teams, {ETC}/docs-token). "
                 "Without it the SDS brain still works: docs-local indexes docs/ on each machine.")
    team = json.load(open(os.path.join(PLUG, "team.json"), encoding="utf-8"))
    print(f"SDS brain on the VM's docs service ({host})")
    library(team)
    good = register(team, opt("--remote"))
    url, token, cert, changed = plugin(team, host)
    good = check(url, token, cert, team["name"]) and good
    print("now commit and push the plugin's docs address, as yourself (members get it at their next session; nothing to "
          "commit when it did not change):\n"
          f"  cd {HERE} && git add {' '.join(changed)} && git commit -m 'SDS brain: docs-http of {host}' && git push")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
