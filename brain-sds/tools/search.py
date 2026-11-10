#!/usr/bin/env python3
"""Search the vendor documentation from the shell, without MCP (the index docs-local uses on this machine: the VM's
library, or the repository's docs/ indexed here; with docs-http only, use the docs-http server instead).

    S=~/.claude/sds-brain/brain-sds/tools/search.py
    python3 $S "ILM policy tag" --product storagegrid-119
    python3 $S PG_DEGRADED
    python3 $S read-chunk 1234          a hit in full
    python3 $S sources                  what is in the library
A first word that is not a command (search, read-chunk, read-doc, related, sources) is taken as the query."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docs_server  # noqa: E402  (puts tools/engine on the path)

if not docs_server.ROOT:
    sys.exit(docs_server.b.SETUP)
DB, WHAT = docs_server.library()
if not DB:
    sys.exit("no vendor-docs index on this machine (" + WHAT + ")")
import search_cli as lib  # noqa: E402

lib._SYN.clear()
lib._SYN.update({w: g for g in docs_server.SYNONYMS for w in g})
args = sys.argv[1:]
if args and args[0] not in ("search", "read-chunk", "read-doc", "related", "sources", "-h", "--help", "--json", "--db"):
    args = ["search"] + args
sys.argv = [sys.argv[0], "--db", DB] + args
lib.main()
