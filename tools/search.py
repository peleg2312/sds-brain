#!/usr/bin/env python3
"""Search the offline library from the shell (the same index the sds-docs MCP server uses; vendor docs only).

    python3 tools/search.py "ILM policy tag" --product storagegrid-119
    python3 tools/search.py PG_DEGRADED
    python3 tools/search.py read-chunk 1234          a hit in full
    python3 tools/search.py sources                  what is in the library
A first word that is not a command (search, read-chunk, read-doc, related, sources) is taken as the query."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docs_server  # noqa: E402  (puts tools/engine on the path)

docs_server.ensure_index()
import search_cli as lib  # noqa: E402

lib._SYN.clear()
lib._SYN.update({w: g for g in docs_server.SYNONYMS for w in g})
args = sys.argv[1:]
if args and args[0] not in ("search", "read-chunk", "read-doc", "related", "sources", "-h", "--help", "--json", "--db"):
    args = ["search"] + args
sys.argv = [sys.argv[0], "--db", docs_server.DB] + args
lib.main()
