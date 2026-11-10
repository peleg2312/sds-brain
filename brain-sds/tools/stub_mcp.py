"""A one-tool MCP server (stdio) for a connection that is not configured yet: Claude Code shows it as connected, and the
tool tells Claude (and so the user) what is missing, instead of a failed server at every session start. Standard library."""
import json
import sys


def serve(name, tool, description, text):
    """answer initialize / tools/list / tools/call until stdin closes; every call of the tool returns `text`"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        mid, method = msg.get("id"), msg.get("method", "")
        if mid is None:                                   # a notification: nothing to answer
            continue
        if method == "initialize":
            result = {"protocolVersion": (msg.get("params") or {}).get("protocolVersion", "2025-06-18"),
                      "capabilities": {"tools": {}}, "serverInfo": {"name": name, "version": "setup"},
                      "instructions": description}
        elif method == "tools/list":
            result = {"tools": [{"name": tool, "description": description,
                                 "inputSchema": {"type": "object", "properties": {}},
                                 "annotations": {"readOnlyHint": True}}]}
        elif method == "tools/call":
            result = {"content": [{"type": "text", "text": text}]}
        elif method == "ping":
            result = {}
        else:
            print(json.dumps({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found"}}), flush=True)
            continue
        print(json.dumps({"jsonrpc": "2.0", "id": mid, "result": result}), flush=True)
    return 0
