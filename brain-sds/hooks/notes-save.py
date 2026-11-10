#!/usr/bin/env python3
"""PostToolUse hook (Edit / Write / MultiEdit): a file saved under the team repository's knowledge/ is scanned for
secrets (S3 keys, tokens, passwords, presigned URLs, private keys). Clean: committed and pushed to the team repository,
docs-local's index is refreshed in the background and the VM's docs service (docs-http) is told to re-index the team's
knowledge, so teammates find the page seconds later. A secret: nothing is committed and Claude is told to replace it.
  notes-save.py --scan     scan every knowledge file; exit 1 on findings (check.py runs the same patterns)
  notes-save.py --index    rewrite knowledge/INDEX.md (every knowledge commit does it too)
Standard library only; never fails the tool call (always exit 0 as a hook)."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
import brainlib as b  # noqa: E402

MAX_LINES = 15


def reindex():
    """the docs server's own knowledge indexing, detached: the note is searchable seconds later, in this session too"""
    engine = os.path.join(b.PLUGIN, "tools", "engine", "mcp_stdio.py")
    try:
        subprocess.Popen([sys.executable, engine, "--knowledge", b.KNOWLEDGE, "--brain-db", os.path.join(b.CACHE, "knowledge.db"),
                          "--reindex-knowledge"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except OSError:
        pass


def notify_docs():
    """POST /refresh?team=<team> to the VM's docs service: it pulls the team repository and re-indexes now instead of at
    its next 10-minute round. Detached, 3 seconds, best effort; a certificate that does not verify: nothing is sent."""
    cfg = b.docs_http()
    if not cfg or "?team=" not in cfg[0]:
        return
    url, auth, ca = cfg
    base, team = url.split("/mcp", 1)[0], url.split("?team=", 1)[1].split("&")[0]
    code = ("import ssl, sys, urllib.request\n"
            "url, auth, ca = sys.argv[1:4]\n"
            "ctx = ssl.create_default_context()\n"
            "ca and ctx.load_verify_locations(ca)\n"
            "req = urllib.request.Request(url, data=b'', method='POST', headers={'Content-Length': '0', **({'Authorization': auth} if auth else {})})\n"
            "urllib.request.urlopen(req, timeout=3, **({'context': ctx} if url.startswith('https') else {})).read()\n")
    try:
        subprocess.Popen([sys.executable, "-c", code, f"{base}/refresh?team={team}", auth, ca], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        pass


def hook():
    try:
        path = (json.load(sys.stdin).get("tool_input") or {}).get("file_path", "")
    except Exception:
        return 0
    if not path or not b.ROOT:
        return 0
    path = os.path.realpath(os.path.expanduser(path))
    root = os.path.realpath(b.KNOWLEDGE) + os.sep
    if not path.startswith(root) or not os.path.isfile(path):
        return 0
    found = b.findings(path)
    if found:
        more = f"\n... and {len(found) - MAX_LINES} more" if len(found) > MAX_LINES else ""
        msg = (f"{os.path.basename(path)} holds {len(found)} secret(s); it was not committed. Replace each value with "
               "<REDACTED> now (rule 4):\n" + "\n".join(found[:MAX_LINES]) + more)
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}))
        return 0
    rel = os.path.relpath(path, os.path.realpath(b.ROOT))
    if b.commit("brain: " + rel, rel):
        notify_docs()
    reindex()
    return 0


def main():
    if sys.argv[1:2] == ["--index"]:
        print("knowledge/INDEX.md " + ("rewritten" if b.write_index() else "unchanged"))
        return 0
    if sys.argv[1:2] == ["--scan"]:
        found = [x for f in b.knowledge_files() for x in b.findings(f)]
        print("\n".join(found))
        return 1 if found else 0
    try:
        return hook()
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
