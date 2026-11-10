#!/usr/bin/env python3
"""The SDS docs service in a container (OpenShift or Podman): the library index built into the image (/app/docs.db,
from the repository's docs/) and the team's knowledge, cloned from the team repository and re-indexed every
SDS_REFRESH_MINUTES (10) and at once on POST /refresh?team=sds (the notes hook sends it after each push).
The same engine and HTTP server as the VM's docs service, with the SDS search vocabulary.

Environment: MCP_SERVER_TOKEN (required, 16 characters at least), SDS_REPO_URL (the team repository, https),
SDS_REPO_USER + SDS_REPO_TOKEN (a read-only deploy token; given to git through a credential helper, never written
into a url or a file), SDS_REFRESH_MINUTES, MCP_TLS_CERT + MCP_TLS_KEY (optional HTTPS). State: /data (an emptyDir:
the clone and the knowledge index are rebuilt from the repository at start)."""
import json
import os
import sys

APP = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(APP, "tools"), os.path.join(APP, "tools", "engine")]
DATA = os.environ.get("SDS_DATA") or "/data"


def main():
    token = os.environ.get("MCP_SERVER_TOKEN", "").strip()
    if len(token) < 16:
        sys.exit("docs-serve: MCP_SERVER_TOKEN must be set (16 characters at least)")
    os.makedirs(os.path.join(DATA, "state"), exist_ok=True)
    tfile = os.path.join(DATA, ".token")
    fd = os.open(tfile, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(token + "\n")
    try:
        with open(os.path.join(APP, "team.json"), encoding="utf-8") as f:      # the plugin's: the team's name
            meta = json.load(f)
    except (OSError, ValueError):
        meta = {}
    team = {"name": meta.get("name") or "sds", "title": meta.get("title") or "SDS"}   # no "library": the image's is the team's
    remote = os.environ.get("SDS_REPO_URL", "").strip()
    if remote:
        team["remote"] = remote
        if os.environ.get("SDS_REPO_TOKEN"):        # git asks this helper for the credential; it is never stored
            os.environ.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="credential.helper", GIT_CONFIG_VALUE_0=
                              '!f() { echo "username=${SDS_REPO_USER:-oauth2}"; echo "password=${SDS_REPO_TOKEN}"; }; f')
    else:
        print("docs-serve: SDS_REPO_URL is not set: the library only, no team knowledge", file=sys.stderr, flush=True)
    tdir = os.path.join(DATA, "teams", team["name"])
    os.makedirs(os.path.join(tdir, "knowledge"), exist_ok=True)
    with open(os.path.join(tdir, "team.json"), "w") as f:
        json.dump(team, f)
    import docs_server                                # the SDS vocabulary and tool texts
    import mcp_stdio
    import search_cli as lib
    lib.SYNONYMS[:] = docs_server.SYNONYMS
    lib._SYN.clear()
    lib._SYN.update({w: g for g in docs_server.SYNONYMS for w in g})
    mcp_stdio.TOOLS[:] = [t for t in mcp_stdio.TOOLS if t["name"] != "explain_code"]
    tls = ["--tls-cert", os.environ["MCP_TLS_CERT"], "--tls-key", os.environ["MCP_TLS_KEY"]] \
        if os.environ.get("MCP_TLS_CERT") and os.environ.get("MCP_TLS_KEY") else []
    sys.argv = [sys.argv[0], "--db", os.path.join(APP, "docs.db"), "--http", "0.0.0.0:8000", "--token-file", tfile,
                "--teams-dir", os.path.join(DATA, "teams"), "--state-dir", os.path.join(DATA, "state"),
                "--refresh-minutes", os.environ.get("SDS_REFRESH_MINUTES") or "10"] + tls
    return mcp_stdio.main()


if __name__ == "__main__":
    sys.exit(main() or 0)
