#!/usr/bin/env python3
"""Stop hook: after a substantial session (20+ tool calls) in which nothing was saved to knowledge/, ask Claude ONCE
whether it learned something durable and, if so, to write it down (brain-learn skill). One marker per session under
.cache/nudged. Off with SDS_NUDGE_DISABLE=1; threshold in SDS_NUDGE_MIN_TOOLS. Silent on any error; exit 0 always."""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import brainlib as b  # noqa: E402

REASON = (
    "This was a substantial session and nothing was saved to the team's knowledge. Check whether it produced durable, "
    "non-obvious knowledge: a root cause, a workaround, a quirk of this environment, a procedure that worked, a wrong "
    "assumption corrected, a fixed problem. If yes, write it down with the brain-learn skill (a dated line in "
    "notes/<topic>.md when confident, else a capture captures/<date>-<slug>.md, under ~/.claude/sds-brain/knowledge/) and tell the user in "
    "two lines. If not, reply with one short line saying nothing needed capturing and stop. Do not repeat your "
    "previous answer.")


def main():
    if os.environ.get("SDS_NUDGE_DISABLE") == "1" or not b.ROOT:
        return 0
    try:
        data = json.load(sys.stdin)
        if data.get("stop_hook_active"):
            return 0
        need = int(os.environ.get("SDS_NUDGE_MIN_TOOLS") or 20)
        sid = os.path.basename(str(data.get("session_id") or ""))
        text = open(data.get("transcript_path") or "", encoding="utf-8", errors="replace").read()
    except (OSError, ValueError):
        return 0
    if not sid or text.count('"type":"tool_use"') + text.count('"type": "tool_use"') < need:
        return 0
    # something was written under knowledge/ this session (a mention of the folder in prose does not count)
    if re.search(r'"file_path"\s*:\s*"[^"]*knowledge/(?:notes/|captures/|runbooks/|incidents/|notes\.md|environment\.md)', text):
        return 0
    d = os.path.join(b.CACHE, "nudged")
    try:
        os.makedirs(d, exist_ok=True)
        for f in os.listdir(d):
            p = os.path.join(d, f)
            if time.time() - os.path.getmtime(p) > 14 * 86400:
                os.remove(p)
        marker = os.path.join(d, sid)
        if os.path.exists(marker):
            return 0
        open(marker, "w").close()
    except OSError:
        return 0
    print(json.dumps({"decision": "block", "reason": REASON}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
