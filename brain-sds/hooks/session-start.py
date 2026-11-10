#!/usr/bin/env python3
"""SessionStart hook: sync the team repository (the brain's home), bring this plugin up to date when its files changed
there, and print a few lines of brain status into the session (home, library, environment, the memory catalog,
runbooks, captures waiting, teammates' recent changes, connections).
Standard library only; never fails the session (always exit 0)."""
import glob
import os
import re
import sqlite3
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
import brainlib as b  # noqa: E402

NOTES_CAP, TOPIC_CAP, STALE_DAYS = 60, 150, 180
K = b.KNOWLEDGE


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def home_line():
    return (f"Home: {b.shown()} (the team repository: rules/, knowledge/, docs/, connections/). Paths in the rules and "
            "skills are relative to it; write notes there, never into the folder you were started in.")


def plugin_line():
    """this plugin runs from Claude Code's copy; when the repository's plugin folder differs (a teammate changed a skill
    or a hook), update the copy in the background, once per version. It applies from the next session."""
    src = os.path.join(b.ROOT, b.NAME)
    if not os.path.isdir(src) or os.path.realpath(src) == os.path.realpath(b.PLUGIN):
        return ""
    want = b.fingerprint(src)
    if want == b.fingerprint(b.PLUGIN):
        return ""
    mark = os.path.join(b.CACHE, "plugin-update")
    if read(mark).strip() == want:
        return ("The brain's plugin differs from the team repository and an update did not change that: tell the user to "
                f"run `sh {b.shown()}/join.sh` (uncommitted changes in {b.NAME}/ are not installed).")
    try:
        os.makedirs(b.CACHE, exist_ok=True)
        with open(mark, "w", encoding="utf-8") as f:
            f.write(want + "\n")
        log = open(os.path.join(b.CACHE, "plugin-update.log"), "w")
        subprocess.Popen(["sh", "-c", f"claude plugin marketplace update {b.NAME} && claude plugin update {b.NAME}@{b.NAME}"],
                         stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    except OSError:
        return f"The brain's plugin changed in the team repository: tell the user to run `sh {b.shown()}/join.sh`."
    return "The brain's plugin (skills, hooks) changed in the team repository: it is being updated and applies from the next session."


def library_line():
    """where the vendor documentation is searched on this machine"""
    http, db = b.docs_http(), b.vm_library() or os.path.join(b.CACHE, "docs.db")
    if http and not b.vm_library():
        return ("Docs: the vendor library is on docs-http (the VM's docs service, with the team's knowledge as of its last "
                "10-minute round); docs-local searches the team's knowledge as it is on this machine.")
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
        n, p = con.execute("SELECT count(*), count(DISTINCT vendor || '/' || product) FROM docs WHERE dup_of IS NULL").fetchone()
        con.close()
        return f"Docs: docs-local searches {n} documents in {p} products plus the team's knowledge (list_sources shows them)."
    except sqlite3.Error:
        return "Docs: docs-local builds its index from docs/ at first start (a few seconds), plus the team's knowledge."


def environment_line():
    text = read(os.path.join(K, "environment.md"))
    rows = sum(1 for line in text.splitlines() if re.match(r"^\|\s*[^|\s-][^|]*\|", line) and not line.startswith("| Cluster")
               and not line.startswith("| Grid") and not line.startswith("| Model"))
    if "not yet confirmed per cluster" in text and not rows:
        return "environment.md: only the reported fleet summary, no cluster or grid filled in yet (offer /brain-sds:brain-setup once)."
    return f"environment.md: {rows} cluster / grid / server rows filled."


def stale_count():
    """dated fact lines, and pages / runbooks whose header's last_verified is older than STALE_DAYS"""
    cut, n = time.time() - STALE_DAYS * 86400, 0
    import calendar
    for f in glob.glob(os.path.join(K, "notes", "*.md")) + glob.glob(os.path.join(K, "runbooks", "*.md")):
        m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", b.header(read(f))[0].get("last_verified", ""))
        try:
            if m and calendar.timegm((int(m.group(1)), int(m.group(2)), int(m.group(3)), 0, 0, 0)) < cut:
                n += 1
        except (ValueError, OverflowError):
            pass
    for f in [os.path.join(K, "notes.md")] + glob.glob(os.path.join(K, "notes", "*.md")):
        for line in read(f).splitlines():
            m = line.startswith("- ") and re.search(r"(\d{4})-(\d{2})-(\d{2})", line)
            try:
                if m and calendar.timegm((int(m.group(1)), int(m.group(2)), int(m.group(3)), 0, 0, 0)) < cut:
                    n += 1
            except (ValueError, OverflowError):
                pass
    return n


def memory_lines():
    notes = read(os.path.join(K, "notes.md"))
    n = len(notes.splitlines())
    out = [f"notes.md: {sum(1 for l in notes.splitlines() if l.startswith('- '))} core facts, {n} lines"
           + (f" - OVER the {NOTES_CAP}-line cap: move facts most sessions do not need into notes/<topic>.md" if n > NOTES_CAP else "") + "."]
    topics = []
    for path in sorted(glob.glob(os.path.join(K, "notes", "*.md"))):
        text = read(path)
        title = b.doc_title(text, 70)
        facts = sum(1 for l in text.splitlines() if l.startswith("- ") and re.search(r"\d{4}-\d{2}-\d{2}", l))
        big = " - OVER 150 lines: merge duplicates, drop stale facts" if len(text.splitlines()) > TOPIC_CAP else ""
        topics.append(f"  notes/{os.path.basename(path)}" + (f" ({facts} facts)" if facts else "") + f": {title}{big}")
    if len(topics) > 30:
        topics = topics[:30] + [f"  ... and {len(topics) - 30} more (grep knowledge/notes)"]
    if topics:
        out += ["Memory topics and pages (read the one a question touches; grep knowledge/notes for an unknown name):"] + topics
    books = sorted(glob.glob(os.path.join(K, "runbooks", "*.md")))
    if books:
        names = [os.path.basename(x)[:-3] for x in books]
        out.append(f"runbooks: {len(books)} tested procedures in knowledge/runbooks/ ({', '.join(names[:15])}"
                   + (f", ... {len(names) - 15} more" if len(names) > 15 else "") + "): before giving change steps, read a matching one and follow it.")
    caps = glob.glob(os.path.join(K, "captures", "*.md"))
    if caps:
        oldest = max((time.time() - os.path.getmtime(c)) / 86400 for c in caps)
        due = len(caps) >= 5 or oldest > 14
        out.append(f"captures: {len(caps)} waiting for curation (brain-learn)"
                   + (" - curation is due: offer it once after the user's first question" if due else "") + ".")
    stale = stale_count()
    if stale:
        out.append(f"stale: {stale} fact(s) or page(s) last verified more than {STALE_DAYS} days ago; re-verify the ones a question touches.")
    inc = glob.glob(os.path.join(K, "incidents", "**", "*.md"), recursive=True)
    if inc:
        out.append(f"incidents: {len(inc)} postmortems under knowledge/incidents/ (searchable).")
    return out


def team_changes_line(days=14, most=6):
    """knowledge files teammates committed lately (not this person's own commits): read when a question touches them"""
    if not b.is_repo():
        return ""
    me = b.git(["config", "user.email"], 3)[1] or b.identity().get("GIT_AUTHOR_EMAIL", "")
    rc, out = b.git(["log", f"--since={days}.days", "--invert-grep", "--grep=^SDS brain:", "--format=%x00%ae%x09%an",
                      "--name-only", "--", "knowledge"], 4)          # not the commits that built or restructured the brain
    if rc != 0:
        return ""
    seen = {}
    for block in out.split("\0")[1:]:
        lines = [l for l in block.splitlines() if l.strip()]
        email, _, who = lines[0].partition("\t") if lines else ("", "", "")
        if not lines or email == me:
            continue
        for f in lines[1:]:
            if f.endswith(".md") and f != "knowledge/INDEX.md" and f not in seen and os.path.exists(os.path.join(b.ROOT, f)):
                seen[f] = who or email.split("@")[0]
    if not seen:
        return ""
    items = [f"{f.replace('knowledge/', '', 1)} ({who})" for f, who in list(seen.items())[:most]]
    more = f", {len(seen) - most} more" if len(seen) > most else ""
    return f"Team changes in the last {days} days: " + ", ".join(items) + more + "; read the ones this question touches."


def connections_line():
    graf = "configured" if os.environ.get("SDS_GRAFANA_URL") and os.environ.get("SDS_GRAFANA_TOKEN") else \
        "not configured (connections/grafana/README.md)"
    obj = "local config present" if os.path.exists(os.path.join(b.ROOT, "connections", "objectify", "config.local.json")) else \
        "status only until its API contract is supplied (connections/objectify/README.md)"
    return f"Connections: grafana {graf}; objectify {obj}."


def main():
    try:
        sys.stdin.read()
    except Exception:
        pass
    if not b.ROOT:                                   # installed from the marketplace, not set up yet: set itself up
        try:
            import bootstrap
            got = bootstrap.start()
        except Exception as e:
            got = [f"{b.SETUP} ({e.__class__.__name__}: {e})"]
        print("SDS brain: " + "\n".join(got))
        return 0
    lines = []
    for fn in (home_line, lambda: "Team repository: " + b.sync() + ".", plugin_line, library_line, environment_line, memory_lines, team_changes_line,
               connections_line):
        try:
            got = fn()
            lines += got if isinstance(got, list) else [got]
        except Exception:
            pass
    lines.append("Read-only toward infrastructure: a guard blocks changing commands; give changes as steps for the user to run.")
    print("SDS brain: " + "\n".join(l for l in lines if l))
    return 0


if __name__ == "__main__":
    sys.exit(main())
