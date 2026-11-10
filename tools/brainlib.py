"""Shared by the hooks (.claude/hooks/) and tools/check.py: where the brain is, the secret scan, and the git sync of
knowledge/. Standard library only; every git call has a timeout and never asks for a password."""
import glob
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE = os.path.join(ROOT, "knowledge")
CACHE = os.path.join(ROOT, ".cache")
MARKER = os.path.join(CACHE, "push-failed")          # the last push failure's reason; session start shows it

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
                out.append(f"{os.path.relpath(path, ROOT)}:{n}: {what}")
                break
    return out


def knowledge_files():
    k = KNOWLEDGE
    return (sorted(glob.glob(os.path.join(k, "*.md"))) + sorted(glob.glob(os.path.join(k, "notes", "*.md")))
            + sorted(glob.glob(os.path.join(k, "runbooks", "*.md"))) + sorted(glob.glob(os.path.join(k, "captures", "*.md")))
            + sorted(glob.glob(os.path.join(k, "incidents", "**", "*.md"), recursive=True)))


# ---- git: knowledge/ is committed and pushed for the team; nothing else is ever committed from here

_IDENT = None


def identity():
    """who commits: the person's own git identity when configured, else <login>@<host>"""
    global _IDENT
    if _IDENT is None:
        _IDENT = {}
        try:
            have = subprocess.run(["git", "-C", ROOT, "config", "--get-regexp", r"^user\.(name|email)$"], capture_output=True,
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
        r = subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL, env=dict(os.environ, GIT_TERMINAL_PROMPT="0", **identity()))
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    except OSError as e:
        return 127, str(e)


def is_repo():
    return os.path.exists(os.path.join(ROOT, ".git"))


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
    if rel:
        spec = ["--", rel]
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
    rc = push(8)
    ahead = git(["rev-list", "--count", "@{upstream}..HEAD"], 5)[1]
    if rc == 0 or ahead in ("0", ""):
        return "in sync with the team repository"
    try:
        why = open(MARKER, encoding="utf-8").read().strip()
    except OSError:
        why = "remote unreachable"
    return f"{ahead} local commit(s) not pushed yet ({why}); retried at the next save or session"
