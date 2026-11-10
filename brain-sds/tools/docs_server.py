#!/usr/bin/env python3
"""docs-local, the plugin's small docs MCP server (stdio). Standard library only. It always searches the team's
knowledge (notes, runbooks, captures, incidents of the team repository, indexed at every start when a page changed) and,
depending on the machine, the vendor documentation:

  on the VM that runs the docs service   the team's library there (/opt/paas/libraries/<library>/docs.db), read as is
  the plugin has docs-http               nothing more: docs-http (the VM's docs service) serves the library
  no VM (docs-http not set up)           the repository's own docs/, indexed here into .cache/docs.db (a few seconds the
                                         first time, refreshed when a file under docs/ changed)

    python3 brain-sds/tools/docs_server.py            what the plugin's .mcp.json runs
    python3 brain-sds/tools/docs_server.py --index    say which of the three applies, build the local index when it is the third

To add your own documents (Red Hat manuals, internal guides): PDF / HTML / Markdown / text files under
docs/<vendor>/<product>/, commit, and re-run vm-setup.py on the VM (LIBRARY.md). PDF needs the pypdf package; without
it PDFs are skipped. The search engine in tools/engine/ (docs_index.py, search_cli.py, mcp_stdio.py) is copied
unchanged from the SAN brain's docs-search server, the same code the VM's docs service runs."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "engine"))
import brainlib as b  # noqa: E402

ROOT = b.ROOT
DOCS = os.path.join(b.BASE, "docs")
CACHE = b.CACHE
DB = os.path.join(CACHE, "docs.db")

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


KNOWLEDGE_ONLY = ("This server holds the SDS team's own knowledge only: notes, runbooks, captures and incidents (library "
                  '"team knowledge"), including what was written a moment ago. The vendor documentation is on the docs-http '
                  "server: search there for how a product works. A hit titled \"Unverified capture\" is a teammate's draft: say so.")


def library(log=lambda *_: None):
    """the vendor-docs index this machine searches: (path or "", what it is)"""
    vm = b.vm_library()
    if vm:
        return vm, f"the VM's library ({vm})"
    if b.docs_http():
        return "", "none here: docs-http (the VM's docs service) serves the library; docs-local searches the team knowledge"
    ensure_index(log=log)
    return (DB, f"the repository's docs/, indexed here ({DB})") if os.path.exists(DB) else ("", "no index could be built from docs/")


def main():
    if not ROOT:
        if "--index" in sys.argv[1:]:
            print(b.SETUP)
            return 1
        import stub_mcp
        return stub_mcp.serve("docs-local", "docs_setup", "The team knowledge is not connected: call this to see why.", b.SETUP)
    if "--index" in sys.argv[1:]:
        db, what = library(log=print)
        print("library: " + what)
        if db:
            import sqlite3
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            for vendor, product, n in con.execute("SELECT vendor, product, count(*) FROM docs WHERE dup_of IS NULL GROUP BY 1, 2 ORDER BY 1, 2"):
                print(f"  {vendor}/{product}: {n} documents")
        return 0
    try:
        db, _ = library(log=lambda *a: print(*a, file=sys.stderr))
    except Exception as e:                       # a broken document must not take the knowledge search down with it
        print(f"docs index not rebuilt: {e.__class__.__name__}: {e}", file=sys.stderr)
        db = ""
    import search_cli as lib
    import mcp_stdio
    lib.SYNONYMS[:] = SYNONYMS
    lib._SYN.clear()
    lib._SYN.update({w: g for g in SYNONYMS for w in g})
    mcp_stdio.TOOLS[:] = [t for t in mcp_stdio.TOOLS if t["name"] != "explain_code"]   # an ONTAP / Dell code lookup: not SDS
    if not db:
        mcp_stdio.INSTRUCTIONS = KNOWLEDGE_ONLY
    os.makedirs(CACHE, exist_ok=True)
    sys.argv = [sys.argv[0], "--knowledge", b.KNOWLEDGE, "--brain-db", os.path.join(CACHE, "knowledge.db")]
    sys.argv += ["--db", db] if db else ["--no-library"]
    return mcp_stdio.main()


if __name__ == "__main__":
    sys.exit(main() or 0)
