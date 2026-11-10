#!/usr/bin/env python3
"""The brain's home on a machine where the plugin was installed straight from the marketplace, without join.sh:

    claude plugin marketplace add <the team repository's git url, or a clone's folder>
    claude plugin install brain-sds@brain-sds

At the first session the session-start hook calls start(): the team repository is cloned as ~/.claude/sds-brain from the
same place the marketplace came from (in the background, it carries the docs library), or, for a marketplace added from a
folder that is itself a clone, that folder is linked; then ~/.claude/CLAUDE.md gets the import line of the team's rules.
Until the clone is there, this session gets the rules from Claude Code's copy of the marketplace. From the next session
on everything is in place, as after join.sh. Standard library only; nothing is printed to Claude except through
start()'s return value."""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import brainlib as b  # noqa: E402

LOG = os.path.join(b.CONFIG, "sds-brain-setup.log")


def import_line():
    default = os.path.join(os.path.expanduser("~"), ".claude")
    return "@~/.claude/sds-brain/rules/main.md" if os.path.realpath(b.CONFIG) == os.path.realpath(default) \
        else "@" + os.path.join(b.LINK, "rules", "main.md")


def add_import():
    md = os.path.join(b.CONFIG, "CLAUDE.md")
    line = import_line()
    try:
        text = open(md, encoding="utf-8").read()
    except OSError:
        text = ""
    if line not in text.splitlines():
        with open(md, "a", encoding="utf-8") as f:
            f.write(("\n" if text and not text.endswith("\n") else "") + "\n" + line + "\n")


def marketplace():
    """(where Claude Code keeps the marketplace, the git url or folder it came from)"""
    try:
        with open(os.path.join(b.CONFIG, "plugins", "known_marketplaces.json"), encoding="utf-8") as f:
            entry = json.load(f).get(b.NAME) or {}
    except (OSError, ValueError):
        return "", ""
    loc, src = entry.get("installLocation") or "", entry.get("source") or {}
    kind = src.get("source")
    if kind == "directory":
        return loc, src.get("path") or loc
    if kind == "github" and src.get("repo"):
        return loc, f"https://github.com/{src['repo']}.git"
    if src.get("url"):
        return loc, src["url"]
    try:
        r = subprocess.run(["git", "-C", loc, "remote", "get-url", "origin"], capture_output=True, text=True, timeout=5)
        return loc, r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return loc, ""


def is_home(folder):
    return bool(folder) and all(os.path.isdir(os.path.join(folder, d)) for d in ("knowledge", "rules", b.NAME))


def rules_now(loc):
    """this session's rules, read from Claude Code's copy of the marketplace (the clone is not there yet)"""
    out = []
    for rel in ("rules/persona.md", "rules/main.md"):
        try:
            text = open(os.path.join(loc, rel), encoding="utf-8").read()
        except OSError:
            continue
        out.append("\n".join(l for l in text.splitlines() if not l.startswith("@")))
    return "\n\n".join(out)


def start():
    """called by session start when there is no home: returns the lines for this session"""
    loc, src = marketplace()
    if not src:
        return [b.SETUP]
    if os.path.isdir(src) and is_home(src):                # a marketplace added from a clone's folder: that clone is the home
        if not os.path.lexists(b.LINK):
            os.makedirs(b.CONFIG, exist_ok=True)
            os.symlink(os.path.realpath(src), b.LINK)
        add_import()
        return [f"The brain's home was linked now: {b.LINK} -> {os.path.realpath(src)}, and the team's rules are imported from "
                "the next session on. Tell the user once: start a new session for the full brain (rules, notes, docs)."]
    partial = b.LINK + ".partial"
    if os.path.isdir(partial) and time.time() - os.path.getmtime(partial) < 1800:
        state = "is still being cloned"
    else:
        try:
            os.makedirs(b.CONFIG, exist_ok=True)
            with open(LOG, "w") as log:
                subprocess.Popen([sys.executable, os.path.abspath(__file__), "clone", src], stdin=subprocess.DEVNULL, stdout=log,
                                 stderr=log, start_new_session=True)
            state = "is being cloned now (in the background)"
        except OSError as e:
            return [f"The brain could not set itself up ({e}). " + b.SETUP]
    shown = src if os.path.isdir(src) else src.split("@")[-1] if "://" not in src else src.split("://", 1)[0] + "://" + src.split("://", 1)[1].split("@")[-1]
    lines = [f"First session of the SDS brain on this machine: the team repository ({shown}) {state} as ~/.claude/sds-brain "
             f"(log: {LOG}). Tell the user once: start a new session when it is done (a minute or two) for the team's notes, "
             "the docs search and the rules; nothing is written to the team's knowledge until then."]
    rules = rules_now(loc)
    if rules:
        lines.append("The team's rules for this session:\n" + rules)
    return lines


def clone(src):
    """the background part: clone into <home>.partial, then move it into place and import the rules"""
    partial = b.LINK + ".partial"
    if os.path.lexists(b.LINK):
        return 0
    import shutil
    shutil.rmtree(partial, ignore_errors=True)
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    r = subprocess.run(["git", "clone", "-q", "--", src, partial], env=env, stdin=subprocess.DEVNULL)
    if r.returncode != 0 or not is_home(partial):
        shutil.rmtree(partial, ignore_errors=True)
        print(f"clone of {src} failed: run join.sh from a clone instead (README)")
        return 1
    os.rename(partial, b.LINK)
    add_import()
    print(f"done: {b.LINK}")
    return 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["clone"] and len(sys.argv) == 3:
        sys.exit(clone(sys.argv[2]))
    print("\n".join(start()))
