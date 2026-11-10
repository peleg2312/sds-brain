#!/usr/bin/env python3
"""PostToolUse hook (Bash and MCP tools): when a result names something the offline library documents, add its meaning
next to the result, so Claude explains it from the documentation instead of guessing, without a search round trip:
  - Ceph health checks (PG_DEGRADED, OSD_NEARFULL, MON_DISK_LOW...) in `ceph health detail` or any other output,
  - S3 error codes (SignatureDoesNotMatch, AccessDenied, NoSuchUpload...) in client output or logs,
  - error messages ("failed to ...: <text>") found word for word in a document.
Only identifiers the library really documents count; at most three per result, each once per session; nothing is
printed otherwise. The docs tools' own results are skipped. Searches this machine's index, else docs-http (a few
seconds at most). Standard library only; never fails the tool call (always exit 0). Off: SDS_DOCS_HINTS=0."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))


def strings(x, out):
    if isinstance(x, str):
        out.append(x)
    elif isinstance(x, dict):
        for v in x.values():
            strings(v, out)
    elif isinstance(x, list):
        for v in x:
            strings(v, out)
    return out


def main():
    if os.environ.get("SDS_DOCS_HINTS") == "0":
        return 0
    data = json.load(sys.stdin)
    tool = str(data.get("tool_name") or "")
    if not (tool == "Bash" or tool.startswith("mcp__")) or "docs-local__" in tool or "docs-http__" in tool:
        return 0
    import docs_access as d
    if not d.b.ROOT:
        return 0
    text = "\n".join(strings(data.get("tool_response"), []))
    if not text.strip():
        return 0
    path = d.seen_file("docs-hints", data.get("session_id"))
    seen = d.read_seen(path)
    hints = d.identifier_hints(text, seen)
    if not hints:
        return 0
    d.write_seen(path, seen)
    ctx = (f"Docs on identifiers in this result ({d.server()}: read_chunk <chunk> for the full text; versions differ):\n"
           + "\n".join("- " + h for h in hints))
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ctx}}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
