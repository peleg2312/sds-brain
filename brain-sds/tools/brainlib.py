"""Shared by the plugin's hooks and tools and by check.py: where the brain's home is, the secret scan, and the git
sync of knowledge/. Standard library only; every git call has a timeout and never asks for a password.

The plugin is what Claude Code installs (a copy in its own cache); the team repository is the brain's HOME and holds
what the plugin works on: rules/, knowledge/, docs/, connections/. join.sh links it as ~/.claude/sds-brain."""
import glob
import hashlib
import json
import os
import re
import subprocess

NAME = "brain-sds"
PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # this plugin folder (repository or cache copy)
CONFIG = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
LINK = os.path.join(CONFIG, "sds-brain")                                      # what join.sh creates


def find_home():
    """the team repository: SDS_BRAIN_HOME, the folder this plugin sits in (run from a clone), or join.sh's link"""
    for c in (os.environ.get("SDS_BRAIN_HOME"), os.path.dirname(PLUGIN), LINK):
        if c and os.path.isdir(os.path.join(c, "knowledge")) and os.path.isdir(os.path.join(c, "rules")):
            return os.path.realpath(c)
    return ""


ROOT = find_home()                                    # "" until join.sh ran on this machine
BASE = ROOT or os.path.join(os.devnull, "sds-brain")  # a path that never exists when there is no home
KNOWLEDGE = os.path.join(BASE, "knowledge")
CACHE = os.path.join(BASE, ".cache")
MARKER = os.path.join(CACHE, "push-failed")          # the last push failure's reason; session start shows it
SETUP = ("The SDS brain is not set up on this machine: clone the team repository and run `sh join.sh` in it once "
         "(it links the repository as ~/.claude/sds-brain and loads the team's rules), then start a new session.")


def team():
    """this plugin's team.json: the team's name on the VM's docs service and the name of its library there"""
    try:
        with open(os.path.join(PLUGIN, "team.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def docs_http():
    """the VM's docs service, from this plugin's .mcp.json (vm-setup.py writes it there): (url, Authorization header,
    CA file) or None while the team has no VM"""
    try:
        with open(os.path.join(PLUGIN, ".mcp.json"), encoding="utf-8") as f:
            cfg = (json.load(f).get("mcpServers") or {}).get("docs-http") or {}
    except (OSError, ValueError):
        return None
    url = str(cfg.get("url") or "")
    if not url.startswith(("http://", "https://")):
        return None
    ca = os.path.join(PLUGIN, "lib", "paas-ui.crt")
    return url, str((cfg.get("headers") or {}).get("Authorization") or ""), ca if os.path.isfile(ca) else ""


def vm_library():
    """the team's library where the VM's docs service keeps it (this machine is the VM), or """""
    name = str(team().get("library") or "")
    path = os.path.join(os.environ.get("PAAS_LIBRARIES") or "/opt/paas/libraries", name, "docs.db")
    return path if name and os.path.isfile(path) and os.access(path, os.R_OK) else ""


def shown():
    """the home as the rules name it: join.sh's link (~/.claude/sds-brain) when it leads here"""
    if ROOT and os.path.realpath(LINK) == ROOT:
        home = os.path.expanduser("~")
        return "~" + LINK[len(home):] if LINK.startswith(home + os.sep) else LINK
    return ROOT


def fingerprint(folder):
    """the content of a plugin folder: its files and what is in them (caches and Claude Code's own markers left out)"""
    h = hashlib.sha1()
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for f in sorted(files):
            if f.endswith(".pyc") or f.startswith(".orphaned"):
                continue
            p = os.path.join(root, f)
            try:
                with open(p, "rb") as fh:
                    data = fh.read()
            except OSError:
                continue
            h.update(os.path.relpath(p, folder).replace(os.sep, "/").encode() + b"\0" + hashlib.sha1(data).digest())
    return h.hexdigest()


# What must never be saved in a note (rule 4). A line ending in "notes-check: allow" is skipped.
SECRET = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
    (re.compile(r"\beyJhbGciOi[\w-]{5,}\.[\w-]+"), "JWT"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"), "bearer token"),
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "AWS-style access key"),
    (re.compile(r"(?i)X-Amz-(?:Signature|Credential|Security-Token)=[\w%/+-]{8,}"), "presigned URL"),
    (re.compile(r"""(?i)["']?(?:secret[_-]?(?:access[_-]?)?key|secret)["']?\s*[=:]\s*["']?(?!<[^>]*>|REDACTED)[A-Za-z0-9/+=]{20,}"""), "S3 secret key"),
    (re.compile(r"""(?i)\b(?:password|passwd|token|api[_-]?key)\b["']?\s*[=:]\s*["']?(?!<[^>]*>|REDACTED)(?=[^\s"',;]*[\d_@#$%^&*+/=!?-])[^\s"',;]{6,}"""), "credential value"),
]


def findings(path):
    """secrets in one file: ["name:line: kind", ...] (never the value)"""
    out = []
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return out
    for n, line in enumerate(lines, 1):
        if line.rstrip().endswith("notes-check: allow"):
            continue
        for rx, what in SECRET:
            if rx.search(line):
                out.append(f"{os.path.relpath(path, BASE)}:{n}: {what}")
                break
    return out


def knowledge_files():
    k = KNOWLEDGE
    return (sorted(glob.glob(os.path.join(k, "*.md"))) + sorted(glob.glob(os.path.join(k, "notes", "*.md")))
            + sorted(glob.glob(os.path.join(k, "runbooks", "*.md"))) + sorted(glob.glob(os.path.join(k, "captures", "*.md")))
            + sorted(glob.glob(os.path.join(k, "incidents", "**", "*.md"), recursive=True)))


def write_index():
    """knowledge/INDEX.md: what the team knows, at a glance in the git server's web view (core facts, topics with their
    fact counts, pages, runbooks, captures waiting, incidents, the tool map). Generated at every knowledge commit; never
    edited by hand. Returns True when it changed."""
    k = KNOWLEDGE
    if not os.path.isdir(k):
        return False

    def title(f):
        try:
            return open(f, encoding="utf-8", errors="replace").read().split("\n", 1)[0].lstrip("# ").strip()[:90]
        except OSError:
            return ""

    def facts(f):
        try:
            return sum(1 for l in open(f, encoding="utf-8", errors="replace").read().splitlines()
                       if re.match(r"^- \d{4}-\d{2}-\d{2}\b", l))
        except OSError:
            return 0
    name = os.path.basename
    topics, pages = [], []
    for f in sorted(glob.glob(os.path.join(k, "notes", "*.md"))):
        n = facts(f)
        (topics if n else pages).append(f"- [{name(f)}](notes/{name(f)}): {title(f)}" + (f" ({n} facts)" if n else ""))
    core = facts(os.path.join(k, "notes.md"))
    books = [f"- [{name(f)}](runbooks/{name(f)}): {title(f)}" for f in sorted(glob.glob(os.path.join(k, "runbooks", "*.md")))]
    caps = sorted(glob.glob(os.path.join(k, "captures", "*.md")))
    inc = sorted(glob.glob(os.path.join(k, "incidents", "**", "*.md"), recursive=True))
    rel = lambda f: os.path.relpath(f, k).replace(os.sep, "/")
    lines = ["# Team knowledge index", "", "Generated at every knowledge commit; edit the files, not this page.", "",
             f"- [environment.md](environment.md): clusters, grids, servers, monitoring (loaded every session)",
             f"- [notes.md](notes.md): {core} core facts (loaded every session)",
             "- [tool-map.md](tool-map.md): which tool answers what (loaded every session)", "",
             "## Topics (dated facts, read when a question touches them)", ""] + (topics or ["- none yet"]) + [
             "", "## Pages", ""] + (pages or ["- none yet"]) + [
             "", "## Runbooks (change procedures a person ran and confirmed)", ""] + (books or ["- none yet"]) + [
             "", f"## Captures waiting for curation: {len(caps)}", ""] + [f"- [{name(c)}]({rel(c)}): {title(c)}" for c in caps[:40]] + [
             "", f"## Incidents: {len(inc)}", ""] + [f"- [{rel(i)}]({rel(i)}): {title(i)}" for i in inc[-40:]] + [""]
    text = "\n".join(lines)
    p = os.path.join(k, "INDEX.md")
    try:
        if open(p, encoding="utf-8").read() == text:
            return False
    except OSError:
        pass
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(p + ".tmp", p)
    return True


# ---- git: knowledge/ is committed and pushed for the team; nothing else is ever committed from here

_IDENT = None


def identity():
    """who commits: the person's own git identity when configured, else <login>@<host>"""
    global _IDENT
    if _IDENT is None:
        _IDENT = {}
        try:
            have = subprocess.run(["git", "-C", BASE, "config", "--get-regexp", r"^user\.(name|email)$"], capture_output=True,
                                  text=True, timeout=5, stdin=subprocess.DEVNULL).stdout
        except Exception:
            have = ""
        import getpass
        import socket
        try:
            name = getpass.getuser()
        except Exception:
            name = os.environ.get("USER") or os.environ.get("USERNAME") or "sds-brain"
        if "user.name" not in have:
            _IDENT.update(GIT_AUTHOR_NAME=name, GIT_COMMITTER_NAME=name)
        if "user.email" not in have:
            mail = f"{name}@{socket.gethostname()}"
            _IDENT.update(GIT_AUTHOR_EMAIL=mail, GIT_COMMITTER_EMAIL=mail)
    return _IDENT


def git(args, timeout=10):
    """(return code, output); 124 on timeout, 127 when git is missing"""
    try:
        r = subprocess.run(["git", "-C", BASE] + list(args), capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL, env=dict(os.environ, GIT_TERMINAL_PROMPT="0", **identity()))
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    except OSError as e:
        return 127, str(e)


def is_repo():
    return bool(ROOT) and os.path.exists(os.path.join(ROOT, ".git"))


def upstream():
    return is_repo() and git(["rev-parse", "--abbrev-ref", "@{upstream}"], 5)[0] == 0


def push(timeout=6):
    rc, out = git(["push", "-q"], timeout)
    try:
        os.makedirs(CACHE, exist_ok=True)
        if rc == 0:
            if os.path.exists(MARKER):
                os.remove(MARKER)
        elif rc != 124:
            with open(MARKER, "w", encoding="utf-8") as f:
                f.write((out.splitlines() or ["push failed"])[-1][:200] + "\n")
    except OSError:
        pass
    return rc


def commit(message, rel=None):
    """commit knowledge/ (one file, or everything changed there except files that still hold a secret), then push; a push
    rejected because a teammate pushed first: pull their commits, push again. Returns True when something was committed."""
    if not is_repo():
        return False
    write_index()
    if rel:
        spec = ["--", rel, os.path.join("knowledge", "INDEX.md")]
    else:
        held = [os.path.relpath(f, ROOT) for f in knowledge_files() if findings(f)]
        spec = ["--", "knowledge"] + [":!" + h for h in held]
    git(["add", "-A"] + spec, 6)
    if git(["diff", "--cached", "--quiet"] + spec, 6)[0] == 0:
        return False
    if git(["commit", "-q", "-m", message] + spec, 8)[0] != 0:
        return False
    if upstream():
        if push() not in (0, 124):
            if git(["pull", "--rebase", "--autostash", "-q"], 12)[0] == 0:
                push()
            else:
                git(["rebase", "--abort"], 8)
    return True


def sync():
    """session start: commit what is pending in knowledge/, pull the team's changes, push ours. One line of state."""
    if not is_repo():
        return "not a git repository: knowledge stays on this machine (git init + a remote shares it)"
    commit("brain: update")
    if not upstream():
        return "no remote branch: knowledge is committed locally only"
    rc, out = git(["pull", "--rebase", "--autostash", "-q"], 12)
    if rc == 124:
        git(["rebase", "--abort"], 8)
        return "sync timed out (remote slow or unreachable): working from the local copy, retried next session"
    if rc != 0:
        conflicted = git(["diff", "--name-only", "--diff-filter=U"], 5)[1].split()
        git(["rebase", "--abort"], 8)
        if conflicted:
            return ("CONFLICT with the team's changes in " + ", ".join(conflicted[:5])
                    + f": tell the user to resolve it by hand (cd {ROOT} && git pull --rebase)")
        return "pull failed: " + (out.splitlines() or ["?"])[-1][:160] + " (working from the local copy)"
    if write_index():                       # two members' pages merged: the index follows them
        commit("brain: index", os.path.join("knowledge", "INDEX.md"))
    rc = push(8)
    ahead = git(["rev-list", "--count", "@{upstream}..HEAD"], 5)[1]
    if rc == 0 or ahead in ("0", ""):
        return "in sync with the team repository"
    try:
        why = open(MARKER, encoding="utf-8").read().strip()
    except OSError:
        why = "remote unreachable"
    return f"{ahead} local commit(s) not pushed yet ({why}); retried at the next save or session"
