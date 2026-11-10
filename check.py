#!/usr/bin/env python3
"""The team repository's own check (CI runs it on every push; run it before a manual change lands):
every JSON file parses, the Python files compile, the marketplace and the plugin name each other, every skill and
agent has a name and a description, the hooks and MCP servers the plugin names exist, no .mcp.json entry is a
placeholder, the rules stay short, the knowledge files hold no secret, notes.md stays under its cap, every runbook has
its Pre-checks / Procedure / Verification / Rollback sections, every docs product says where it came from, and the
vendored Grafana archives match their pinned sha256. Standard library, Python 3.9. Exit 1 on a finding."""
import glob
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["SDS_BRAIN_HOME"] = HERE                      # this clone, whatever is joined on the machine
sys.path.insert(0, os.path.join(HERE, "brain-sds", "tools"))
import brainlib as b  # noqa: E402

ROOT, PLUG = b.ROOT, os.path.join(HERE, b.NAME)
bad = []
RUNBOOK_SECTIONS = ("Pre-checks", "Procedure", "Verification", "Rollback")
RULE_CAPS = {"main.md": 120, "persona.md": 30, "storage.md": 150}


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


for f in tracked("*.json", ".claude-plugin/*.json", "brain-sds/**/*.json", "brain-sds/.mcp.json", "brain-sds/.claude-plugin/*.json",
                 "connections/**/*.json", "docs/**/manifest.json"):
    try:
        json.load(open(f, encoding="utf-8"))
    except (OSError, ValueError) as e:
        ok("json " + rel(f), False, str(e))
for f in tracked("*.py", "brain-sds/**/*.py", "connections/**/*.py"):
    try:
        compile(open(f, encoding="utf-8").read(), f, "exec")       # a syntax check; nothing is written
    except SyntaxError as e:
        ok("python " + rel(f), False, f"line {e.lineno}: {e.msg}")

market = json.load(open(os.path.join(ROOT, ".claude-plugin", "marketplace.json")))
manifest = json.load(open(os.path.join(PLUG, ".claude-plugin", "plugin.json")))
entry = next((p for p in market.get("plugins", []) if p.get("name") == b.NAME), {})
ok("marketplace", market.get("name") == b.NAME and entry.get("source") == "./" + b.NAME and manifest.get("name") == b.NAME,
   f"marketplace.json, its plugin entry (source ./{b.NAME}) and plugin.json must all be named {b.NAME}")
ok("plugin.json has no version", "version" not in manifest, "leave it out: Claude Code then takes the commit as the version, so every change is delivered")
team = b.team()
ok("team.json", bool(re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", str(team.get("name", ""))))
   and bool(re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", str(team.get("library", "")))), "needs name and library (lower case)")

skills = tracked("brain-sds/skills/*/SKILL.md")
ok("skills present", len(skills) > 0)
for f in skills:
    fm = front(f)
    name = re.search(r"^name:\s*(\S+)", fm, re.M)
    ok("skill " + rel(f), bool(name) and name.group(1) == os.path.basename(os.path.dirname(f)) and "description:" in fm,
       "frontmatter needs name (= its folder) and description")
    desc = re.search(r"^description:\s*(.*)$", fm, re.M)
    ok("skill description length " + rel(f), not desc or len(desc.group(1)) <= 1024, "1024 characters at most")
for f in tracked("brain-sds/agents/*.md"):
    ok("agent " + rel(f), "name:" in front(f) and "description:" in front(f), "frontmatter needs name and description")

hooks = json.load(open(os.path.join(PLUG, "hooks", "hooks.json")))
for groups in hooks.get("hooks", {}).values():
    for g in groups:
        for h in g.get("hooks", []):
            m = re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/(hooks/[\w.-]+\.py)", h.get("command", ""))
            ok("hook " + h.get("command", "")[-40:], bool(m) and os.path.isfile(os.path.join(PLUG, m.group(1))),
               "hooks.json names a hook script that is missing (use ${CLAUDE_PLUGIN_ROOT}/hooks/<name>.py)")
servers = json.load(open(os.path.join(PLUG, ".mcp.json")))["mcpServers"]
ok(".mcp.json docs-local", "docs-local" in servers, "the plugin's own docs server is missing")
for name, cfg in servers.items():
    if cfg.get("type") == "http" or cfg.get("url"):
        url = str(cfg.get("url", ""))
        ok(f".mcp.json {name}", url.startswith(("http://", "https://")) and not re.search(r"\b(HOST|TOKEN|example)\b", json.dumps(cfg)),
           "an address or token placeholder: a server goes into .mcp.json only when it is complete (vm-setup.py writes docs-http)")
        continue
    script = next((a for a in cfg.get("args", []) if a.endswith(".py")), "").replace("${CLAUDE_PLUGIN_ROOT}/", "")
    ok(f".mcp.json {name}", bool(script) and os.path.isfile(os.path.join(PLUG, script)), "its script is missing")
    if "connect.py" in script:
        conn = next((a for a in cfg.get("args", []) if not a.endswith(".py")), "")
        ok(f"connection {name}", os.path.isfile(os.path.join(ROOT, "connections", conn, "launch.py")), f"connections/{conn}/launch.py is missing")

for name, cap in RULE_CAPS.items():
    f = os.path.join(ROOT, "rules", name)
    ok("rules/" + name, os.path.isfile(f), "missing")
    if os.path.isfile(f):
        n = len(open(f, encoding="utf-8").read().splitlines())
        ok(f"rules/{name} under {cap} lines", n <= cap, f"{n} lines: it is loaded into every session")
        found = b.findings(f)
        ok("no secret in rules/" + name, not found, "; ".join(x.split(": ", 1)[-1] for x in found[:5]))
main_md = open(os.path.join(ROOT, "rules", "main.md"), encoding="utf-8").read() if os.path.isfile(os.path.join(ROOT, "rules", "main.md")) else ""
for imp in re.findall(r"^@(\S+)$", main_md, re.M):
    ok("rules/main.md import " + imp, os.path.isfile(os.path.normpath(os.path.join(ROOT, "rules", imp))), "the imported file is missing")

for f in b.knowledge_files():
    found = b.findings(f)
    ok("no secret in " + rel(f), not found, "; ".join(x.split(": ", 1)[-1] + " line " + x.split(":")[1] for x in found[:5]))
tmap = os.path.join(b.KNOWLEDGE, "tool-map.md")
if os.path.isfile(tmap):
    n = len(open(tmap, encoding="utf-8").read().splitlines())
    ok("knowledge/tool-map.md under 40 lines", n <= 40, f"{n} lines: it is loaded into every session")
notes = os.path.join(b.KNOWLEDGE, "notes.md")
if os.path.isfile(notes):
    n = len(open(notes, encoding="utf-8").read().splitlines())
    ok("knowledge/notes.md under 60 lines", n <= 60, f"{n} lines: move facts into knowledge/notes/<topic>.md")
learn = open(os.path.join(PLUG, "skills", "brain-learn", "SKILL.md"), encoding="utf-8").read()
for name in sorted(set(re.findall(r"`(?:templates/)?([a-z]+\.md)` *(?:\)|from|:|\.|,| )", learn)) & {"topic.md", "capture.md", "page.md", "runbook.md", "incident.md", "metric.md"}):
    ok("templates/" + name, os.path.isfile(os.path.join(ROOT, "templates", name)), "the brain-learn skill names it, the file is missing")
for f in tracked("templates/*.md"):
    found = b.findings(f)
    ok("no secret in " + rel(f), not found, "; ".join(x.split(": ", 1)[-1] for x in found[:5]))
for f in tracked("knowledge/runbooks/*.md", "templates/runbook.md"):
    heads = {m.group(1).strip().lower() for m in re.finditer(r"^##\s+(.+?)\s*$", open(f, encoding="utf-8", errors="replace").read(), re.M)}
    missing = [h for h in RUNBOOK_SECTIONS if not any(x.startswith(h.lower()) for x in heads)]
    ok("runbook " + rel(f), not missing, "missing section(s): " + ", ".join("## " + h for h in missing))
loose = 0
for f in [notes] + tracked("knowledge/notes/*.md"):
    for n, line in enumerate(open(f, encoding="utf-8", errors="replace").read().splitlines() if os.path.isfile(f) else [], 1):
        if re.match(r"^- \d{4}-\d{2}-\d{2}\b", line) and not re.search(r"\b(verified|observed|documented|user-reported|hypothesis)\b", line):
            loose += 1
            if loose <= 10:
                print(f"note {rel(f)}:{n}: dated fact without a confidence word (verified / observed / documented / user-reported / hypothesis)")

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
