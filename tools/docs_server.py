#!/usr/bin/env python3
"""The SDS docs MCP server (stdio): offline search over docs/ (vendor documentation) and knowledge/ (the team's notes,
runbooks, captures, incidents). Standard library only.

    python3 tools/docs_server.py            what .mcp.json runs
    python3 tools/docs_server.py --index    build or refresh the index, print what is in it, exit

The index is a local cache (.cache/docs.db, never committed): built the first time (a few seconds), refreshed when a
file under docs/ was added, changed or removed. To add your own documents (Red Hat manuals, internal guides): put
PDF / HTML / Markdown / text files under docs/<vendor>/<product>/ and commit them; the next session indexes them.
PDF needs the pypdf package; without it PDFs are skipped and the rest is indexed.

The search engine in tools/engine/ (docs_index.py, search_cli.py, mcp_stdio.py) is copied unchanged from the SAN
brain's docs-search server; this file only points it at this repository and gives it the SDS vocabulary."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "tools", "engine")
DOCS = os.path.join(ROOT, "docs")
CACHE = os.path.join(ROOT, ".cache")
DB = os.path.join(CACHE, "docs.db")
sys.path.insert(0, ENGINE)

# Words that mean the same thing in a search (a query word matches any member of its group)
SYNONYMS = [
    ["rgw", "radosgw", "rados gateway", "object gateway", "ceph object gateway"], ["osd", "object storage daemon"],
    ["pg", "placement group"], ["mon", "monitor"], ["mgr", "manager"], ["rhcs", "red hat ceph storage"],
    ["sg", "storagegrid"], ["ilm", "information lifecycle management"], ["ec", "erasure coding", "erasure coded"],
    ["lb", "load balancer"], ["ha", "high availability"], ["sigv4", "signature version 4"],
    ["mpu", "multipart upload"], ["acl", "access control list"], ["kms", "key management"],
    ["slow ops", "slow requests", "slow operations"], ["multisite", "multi site"], ["ilo", "integrated lights out"],
    ["certificate", "cert"], ["slow", "latency", "performance degradation"], ["error", "failure", "fault"],
    ["alert", "alarm", "event"], ["air gapped", "airgapped", "offline", "disconnected"],
    ["disappeared", "lost", "missing", "gone"], ["shows", "show", "display"], ["details", "info", "information"],
]


def fingerprint():
    """what the index was built from: every file under docs/ with its size and whole-second mtime"""
    import hashlib
    h, n = hashlib.sha1(), 0
    for root, dirs, files in os.walk(DOCS):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(root, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            h.update(f"{os.path.relpath(p, DOCS)}\0{st.st_size}\0{int(st.st_mtime)}\n".encode())
            n += 1
    return f"{n}:{h.hexdigest()[:16]}"


def ensure_index(log=lambda *_: None):
    """build or refresh .cache/docs.db when docs/ changed since the last build (one session builds, the others wait)"""
    os.makedirs(CACHE, exist_ok=True)
    stamp, state = DB + ".stamp", fingerprint()

    def fresh():
        try:
            return os.path.exists(DB) and open(stamp).read().strip() == state
        except OSError:
            return False
    if fresh():
        return
    lock = open(DB + ".lock", "w")
    try:
        try:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass
        if fresh():
            return
        import docs_index
        docs_index.build(DOCS, DB, log=log)
        with open(stamp, "w") as f:
            f.write(state + "\n")
    finally:
        lock.close()


def main():
    if "--index" in sys.argv[1:]:
        ensure_index(log=print)
        import sqlite3
        con = sqlite3.connect(DB)
        for vendor, product, n in con.execute("SELECT vendor, product, count(*) FROM docs WHERE dup_of IS NULL GROUP BY 1, 2 ORDER BY 1, 2"):
            print(f"  {vendor}/{product}: {n} documents")
        return 0
    try:
        ensure_index(log=lambda *a: print(*a, file=sys.stderr))
    except Exception as e:                       # a broken document must not take the knowledge search down with it
        print(f"docs index not rebuilt: {e.__class__.__name__}: {e}", file=sys.stderr)
    import search_cli as lib
    import mcp_stdio
    lib.SYNONYMS[:] = SYNONYMS
    lib._SYN.clear()
    lib._SYN.update({w: g for g in SYNONYMS for w in g})
    mcp_stdio.TOOLS[:] = [t for t in mcp_stdio.TOOLS if t["name"] != "explain_code"]   # an ONTAP / Dell code lookup: not SDS
    sys.argv = [sys.argv[0], "--knowledge", os.path.join(ROOT, "knowledge"), "--brain-db", os.path.join(CACHE, "knowledge.db")]
    if os.path.exists(DB):
        sys.argv += ["--db", DB]
    else:
        sys.argv += ["--no-library"]
    return mcp_stdio.main()


if __name__ == "__main__":
    sys.exit(main() or 0)
