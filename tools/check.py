#!/usr/bin/env python3
"""The repository's own check (CI runs it on every push; run it before a manual change lands):
every JSON file parses, the Python files compile, every skill and agent has a name and a description, the hooks the
settings name exist, the knowledge files hold no secret, notes.md stays under its cap, every runbook has its
Pre-checks / Procedure / Verification / Rollback sections, every docs product says where it came from, and the
vendored Grafana archives match their pinned sha256. Standard library, Python 3.9. Exit 1 on a finding."""
import glob
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brainlib as b  # noqa: E402

ROOT = b.ROOT
bad = []
RUNBOOK_SECTIONS = ("Pre-checks", "Procedure", "Verification", "Rollback")


def ok(label, cond, detail=""):
    if not cond:
        bad.append(label)
        print("FAIL " + label + (": " + detail if detail else ""))


def rel(p):
    return os.path.relpath(p, ROOT)


def tracked(*patterns):
    out = []
    for pat in patterns:
        out += [p for p in glob.glob(os.path.join(ROOT, pat), recursive=True) if "/.cache/" not in p and "/.git/" not in p]
    return sorted(set(out))


def front(path):
    parts = open(path, encoding="utf-8", errors="replace").read().split("---")
    return parts[1] if len(parts) > 2 else ""


for f in tracked("*.json", ".mcp.json", ".claude/**/*.json", "connections/**/*.json", "docs/**/manifest.json"):
    try:
        json.load(open(f, encoding="utf-8"))
    except (OSError, ValueError) as e:
        ok("json " + rel(f), False, str(e))
for f in tracked("tools/**/*.py", ".claude/hooks/*.py", "connections/**/*.py"):
    try:
        compile(open(f, encoding="utf-8").read(), f, "exec")       # a syntax check; nothing is written
    except SyntaxError as e:
        ok("python " + rel(f), False, f"line {e.lineno}: {e.msg}")

skills = tracked(".claude/skills/*/SKILL.md")
ok("skills present", len(skills) > 0)
for f in skills:
    fm = front(f)
    name = re.search(r"^name:\s*(\S+)", fm, re.M)
    ok("skill " + rel(f), bool(name) and name.group(1) == os.path.basename(os.path.dirname(f)) and "description:" in fm,
       "frontmatter needs name (= its folder) and description")
    desc = re.search(r"^description:\s*(.*)$", fm, re.M)
    ok("skill description length " + rel(f), not desc or len(desc.group(1)) <= 1024, "1024 characters at most")
for f in tracked(".claude/agents/*.md"):
    ok("agent " + rel(f), "name:" in front(f) and "description:" in front(f), "frontmatter needs name and description")

settings = json.load(open(os.path.join(ROOT, ".claude", "settings.json")))
for groups in settings.get("hooks", {}).values():
    for g in groups:
        for h in g.get("hooks", []):
            m = re.search(r"\.claude/hooks/([\w.-]+\.py)", h.get("command", ""))
            ok("hook " + h.get("command", "")[-40:], bool(m) and os.path.isfile(os.path.join(ROOT, ".claude", "hooks", m.group(1))),
               "the settings name a hook script that is missing")
servers = json.load(open(os.path.join(ROOT, ".mcp.json")))["mcpServers"]
for name, cfg in servers.items():
    script = next((a for a in cfg.get("args", []) if a.endswith(".py")), "")
    ok(f".mcp.json {name}", bool(script) and os.path.isfile(os.path.join(ROOT, script)), "its script is missing")
ok("enabledMcpjsonServers", sorted(settings.get("enabledMcpjsonServers", [])) == sorted(servers),
   ".claude/settings.json and .mcp.json name different servers")

for f in b.knowledge_files():
    found = b.findings(f)
    ok("no secret in " + rel(f), not found, "; ".join(x.split(": ", 1)[-1] + " line " + x.split(":")[1] for x in found[:5]))
notes = os.path.join(b.KNOWLEDGE, "notes.md")
if os.path.isfile(notes):
    n = len(open(notes, encoding="utf-8").read().splitlines())
    ok("knowledge/notes.md under 60 lines", n <= 60, f"{n} lines: move facts into knowledge/notes/<topic>.md")
for f in tracked("knowledge/runbooks/*.md"):
    heads = {m.group(1).strip().lower() for m in re.finditer(r"^##\s+(.+?)\s*$", open(f, encoding="utf-8", errors="replace").read(), re.M)}
    missing = [h for h in RUNBOOK_SECTIONS if not any(x.startswith(h.lower()) for x in heads)]
    ok("runbook " + rel(f), not missing, "missing section(s): " + ", ".join("## " + h for h in missing))
loose = 0
for f in [notes] + tracked("knowledge/notes/*.md"):
    for n, line in enumerate(open(f, encoding="utf-8", errors="replace").read().splitlines() if os.path.isfile(f) else [], 1):
        if re.match(r"^- \d{4}-\d{2}-\d{2}\b", line) and not re.search(r"\b(verified|observed|hypothesis)\b", line):
            loose += 1
            if loose <= 10:
                print(f"note {rel(f)}:{n}: dated fact without a confidence word (verified / observed / hypothesis)")

for product in tracked("docs/*/*/"):
    files = [x for x in os.listdir(product) if not x.startswith(".")]
    ok("docs source " + rel(product), os.path.isfile(os.path.join(product, ".source_url")) or os.path.isfile(os.path.join(product, "manifest.json"))
       or os.path.isfile(os.path.join(product, "SOURCE.md")),
       "say where these documents come from: a SOURCE.md (one line is enough), .source_url or manifest.json") if files else None

manifest = os.path.join(ROOT, "connections", "grafana", "release-manifest.json")
if os.path.isfile(manifest):
    for asset in json.load(open(manifest))["assets"]:
        p = os.path.join(ROOT, "connections", "grafana", "vendor", asset["name"])
        if not os.path.isfile(p):
            ok("grafana archive " + asset["name"], False, "missing")
            continue
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                h.update(block)
        ok("grafana archive " + asset["name"], h.hexdigest() == asset["sha256"], "does not match release-manifest.json")

print("all checks passed" if not bad else f"{len(bad)} finding(s)")
sys.exit(1 if bad else 0)
