#!/usr/bin/env python3
"""PreToolUse hook: the safety net behind rule 1 (read-only toward infrastructure).

Shell commands (Bash), looked at piece by piece, also inside ssh / cephadm shell / podman exec / bash -c:
  blocked  changes to storage: ceph, radosgw-admin, rados, rbd, cephadm, ceph-volume (anything that is not a known read
           command), S3 clients (aws s3 / s3api, s3cmd, mc, s5cmd, rclone: writes and deletes), HPE tools (ilorest,
           ipmitool, ssacli, storcli, smartctl tests), and host changes on a remote machine (systemctl, dnf, SELinux,
           network, disks, kill...). Also commands that print keys (radosgw-admin user info without a jq projection).
  asked    (the user confirms): curl / wget writes to another host, a host change on this machine, a remote command
           this guard does not know.
MCP tools: a tool whose name says it changes something is blocked.
Brain files: in the team repository (the brain's home) Claude may write under knowledge/ and docs/; the rules, this
plugin, the connections and everything else there are changed by people, with a commit.
Approved without a prompt, because the plugin cannot ship permission rules: the plugin's own read-only MCP tools
(docs-local, docs-http, grafana, objectify), saving a file under the home's knowledge/, and tools/search.py.

Exit code 2 = blocked, the reason goes back to Claude. A read command blocked by mistake: add its exact beginning to
rules/guard-allow.txt in the team repository (one per line). This is a net against mistakes, not a sandbox: read-only
accounts on every backend are the real guarantee."""
import fnmatch
import json
import os
import re
import shlex
import sys

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:                                                 # the home is looked up by the shared library; without it only the home rules are off
    sys.path.insert(0, os.path.join(PLUGIN, "tools"))
    import brainlib
    ROOT, NAME = brainlib.ROOT, brainlib.NAME
except Exception:
    ROOT, NAME = "", "brain-sds"
WRITABLE = ("knowledge/", "docs/", ".cache/")        # what Claude may write inside the team repository
OWN_MCP = f"mcp__plugin_{NAME}_"                     # how Claude Code names this plugin's MCP tools
ALLOW = json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow",
                                           "permissionDecisionReason": "SDS brain: a read-only tool of the brain itself"}})
SUBST = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")


def segments(cmd):
    """the command's pieces between ; | & && || and newlines, outside quotes (a quoted remote command stays whole)"""
    out, cur, quote, i = [], [], "", 0
    while i < len(cmd):
        c = cmd[i]
        if quote:
            if c == "\\" and quote == '"' and i + 1 < len(cmd):
                cur.append(cmd[i:i + 2]); i += 2; continue
            if c == quote:
                quote = ""
        elif c in "'\"":
            quote = c
        elif c == "\\" and i + 1 < len(cmd):
            cur.append(cmd[i:i + 2]); i += 2; continue
        elif c in ";|&\n":
            if c == "&" and (cur and cur[-1] == ">" or cmd[i + 1:i + 2] == ">" or (cur and cur[-1].isdigit() and "".join(cur[-2:-1]) == ">")):
                cur.append(c); i += 1; continue          # 2>&1, &>file: a redirect, not a separator
            out.append("".join(cur)); cur = []; i += 1
            continue
        cur.append(c); i += 1
    out.append("".join(cur))
    return [x.strip() for x in out if x.strip()]
WRAPPERS = {"sudo", "time", "nohup", "env", "nice", "ionice", "stdbuf", "command", "exec", "watch", "timeout"}
SSH_VALUE_OPTS = set("bcDEeFIiJLlmOopQRSWw")

# ---- read-only commands, by tool (the first words after the program, options removed)
CEPH_READ = {tuple(x.split()) for x in """status|health|df|versions|version|fsid|quorum_status|features|time-sync-status|
progress|insights|node ls|log last|mon stat|mon dump|mon metadata|mon versions|mon ok-to-stop|mgr stat|mgr dump|mgr services|
mgr metadata|mgr versions|mgr module ls|osd stat|osd tree|osd df|osd perf|osd dump|osd ls|osd find|osd metadata|osd versions|
osd info|osd utilization|osd blocklist ls|osd ok-to-stop|osd safe-to-destroy|osd pool ls|osd pool get|osd pool stats|
osd pool autoscale-status|osd pool get-quota|osd pool application get|osd crush tree|osd crush dump|osd crush rule ls|
osd crush rule dump|osd crush class ls|osd crush show-tunables|osd crush weight-set ls|osd erasure-code-profile ls|
osd erasure-code-profile get|osd getcrushmap|osd getmap|osd numa-status|osd count-metadata|pg stat|pg dump|pg dump_stuck|
pg dump_json|pg dump_pools_json|pg ls|pg ls-by-osd|pg ls-by-pool|pg ls-by-primary|pg map|pg getmap|config get|
config help|config ls|config-key ls|config-key exists|orch status|orch ls|
orch ps|orch host ls|orch device ls|orch upgrade status|orch upgrade check|orch upgrade ls|crash ls|crash ls-new|crash info|
crash stat|device ls|device info|device ls-by-daemon|device ls-by-host|device get-health-metrics|balancer status|
balancer eval|fs ls|fs status|fs dump|fs get|telemetry status|healthcheck history ls""".replace("\n", "").split("|")}
TELL_READ = {tuple(x.split()) for x in """version|versions|status|perf dump|perf schema|perf histogram dump|
dump_ops_in_flight|dump_historic_ops|dump_historic_slow_ops|dump_blocked_ops|dump_mempools|config show|config get|
config diff|dump_osd_network|heap stats|mon_status|quorum_status|cache status|dump_watchers|dump_recovery_reservations|
dump_scrubs|ops|sessions|help""".replace("\n", "").split("|")}
RGW_READ = {tuple(x.split()) for x in """sync status|metadata sync status|data sync status|bucket stats|bucket list|
bucket limit check|bucket sync status|bucket sync info|bucket radoslist|bucket layout|user list|user stats|usage show|
zone list|zonegroup list|zonegroup get|realm list|realm get|realm list-periods|period get|period list|
period get-current|lc list|lc get|gc list|reshard list|reshard status|log list|log show|bi list|object stat|
metadata list|mdlog status|mdlog list|datalog status|datalog list|bilog status|bilog list|sync error list|
sync group get|sync policy get|ratelimit get|topic list|topic get|notification list""".replace("\n", "").split("|")}
RGW_KEYS = {("user", "info"), ("zone", "get"), ("metadata", "get"), ("key", "create"), ("user", "create"), ("subuser", "create")}
VALUE_OPTS = {"--uid", "--bucket", "--rgw-zone", "--rgw-zonegroup", "--rgw-realm", "--source-zone", "--tenant", "--object",
              "--shard-id", "--start-date", "--end-date", "--max-entries", "--marker", "--format", "-f", "--cluster", "--id",
              "--user", "-n", "--name", "-c", "--conf", "-k", "--keyring", "--connect-timeout", "-p", "--pool", "-N",
              "--namespace", "-o", "--service_name", "--service-name", "--daemon-id", "--daemon_id", "--daemon-type",
              "--daemon_type", "--hostname", "--host", "--profile", "--endpoint-url", "--region", "--query", "--output",
              "--cli-connect-timeout", "--cli-read-timeout", "--max-items", "--page-size", "--prefix", "--key",
              "--version-id", "--max-uploads", "--max-keys", "--delimiter", "--fsid", "--image", "--url", "-u", "-H"}
RADOS_READ = {"df", "lspools", "ls", "stat", "stat2", "getxattr", "listxattr", "listomapkeys", "listomapvals", "getomapval",
              "getomapheader", "lssnap"}
RBD_READ = {"ls", "list", "info", "status", "du", "disk-usage", "showmapped", "children", "diff"}
CEPHADM_READ = {"ls", "version", "check-host", "logs", "inspect-image", "list-networks", "gather-facts"}
S3CMD_READ = {"ls", "la", "info", "du", "multipart", "listmp", "getlifecycle", "getpolicy", "getcors", "version"}
MC_READ = {"ls", "stat", "du", "tree", "find", "ping", "head", "cat", "diff", "ready"}
S5CMD_READ = {"ls", "du", "cat", "head", "version"}
RCLONE_READ = {"ls", "lsd", "lsl", "lsf", "lsjson", "size", "about", "check", "cat", "tree", "version", "listremotes"}
ILOREST_READ = {"login", "logout", "get", "list", "info", "types", "select", "status", "serverinfo", "serverstatus", "help",
                "version", "save"}
IPMI_CHANGE = re.compile(r"\b(power\s+(on|off|cycle|reset|soft|diag)|chassis\s+(bootdev|bootparam\s+set|identify|policy)|"
                         r"(mc|bmc)\s+reset|sel\s+clear|lan\s+set|user\s+(set|enable|disable|priv)|raw|sol\s+(activate|set)|"
                         r"fru\s+(write|edit)|sensor\s+thresh|firewall\s+(enable|disable))\b")
REMOTE_READ = set("""cat ls head tail grep egrep fgrep zgrep zcat awk cut sort uniq wc tr df du free uptime uname hostname date id
whoami ps vmstat iostat mpstat pidstat sar lsblk lspci lscpu lsmem lsscsi lsusb dmidecode blkid findmnt ip ss nmcli ethtool
chronyc timedatectl journalctl systemctl getenforce sestatus ausearch matchpathcon rpm dnf yum podman docker stat file find
echo true test jq ping traceroute tracepath dig nslookup host curl openssl lsof dmesg smartctl nvme multipath pvs vgs lvs
lvdisplay pvdisplay vgdisplay sysctl which type sleep sed xargs printf basename dirname readlink getent set cd [""".split())
HOST_CHANGE = re.compile(
    r"^(systemctl\s+(-\S+\s+)*(start|stop|restart|reload|try-restart|enable|disable|mask|unmask|kill|isolate|daemon-reload|"
    r"reboot|poweroff|halt|set-property|edit|reset-failed)\b|(reboot|shutdown|poweroff|halt)\b|init\s+[06]\b|setenforce\b|"
    r"setsebool\b|semanage\s+\w+\s+-[amd]\b|restorecon\b|chcon\b|audit2allow\b.*\s-M\b|semodule\s+-[ierd]\b|"
    r"(dnf|yum)\s+(-\S+\s+)*(install|remove|erase|update|upgrade|downgrade|reinstall|autoremove|module\s+(enable|disable|install|reset))\b|"
    r"rpm\s+-[A-Za-z]*[iUeF]\b|modprobe\b|rmmod\b|sysctl\s+(-w|--write|[\w.]+\s*=)|"
    r"ip\s+(-\S+\s+)*(link|addr|address|route|rule|neigh|tunnel)\s+(set|add|del|delete|change|replace|flush)\b|"
    r"nmcli\s+(-\S+\s+)*(c|con|connection|d|dev|device|n|networking|g|general|r|radio)\s+(up|down|mod|modify|add|del|delete|"
    r"reapply|reload|connect|disconnect|set|on|off|hostname)\b|ethtool\s+(-[sKGACLEeUNfpP]\b|--(set|change|flash|reset|offload|pause|coalesce|features)\S*)|"
    r"mkfs\S*\b|wipefs\b|sgdisk\b|sfdisk\b|blkdiscard\b|fdisk\s+(?!-l\b)|parted\b(?!.*\bprint\b)|dd\b.*\bof=|"
    r"(lv|vg|pv)(create|remove|extend|reduce|resize|change|rename)\b|multipath\s+-[fF]\b|"
    r"mdadm\s+.*--(create|stop|remove|fail|add|grow|zero-superblock)\b|(kill|pkill|killall)\b|umount\b|mount\s+\S|swapoff\b|"
    r"firewall-cmd\b(?!.*--(list|get|query|state|info))|iptables\b(?!.*\s-[LS]\b)|nft\s+(add|delete|flush|insert|replace)\b|"
    r"chronyc\s+(makestep|burst|offline|online|add|delete|reset)\b|timedatectl\s+set-|hostnamectl\s+set-|"
    r"(podman|docker|crictl)\s+(rm|stop|kill|restart|start|pull|run|rmi|create|pause|unpause|update|system\s+prune|volume\s+rm|network\s+rm)\b|"
    r"(rm|mv|cp|truncate|shred|chmod|chown|ln|touch|mkdir|rmdir|tee)\s|sed\s+(-\S+\s+)*(-i|--in-place)|.*[^0-9&]>\s*[^&\s])")
LOCAL_ASK = re.compile(
    r"^(systemctl\s+(-\S+\s+)*(start|stop|restart|reload|try-restart|enable|disable|mask|kill|isolate|reboot|poweroff|halt)\b|"
    r"(reboot|shutdown|poweroff|halt)\b|setenforce\b|mkfs\S*\b|wipefs\b|sgdisk\b|blkdiscard\b|dd\b.*\bof=/dev/|"
    r"(podman|docker)\s+(rm|stop|kill|restart)\b)")
READ_POST = re.compile(r"/(_search|_count|_msearch|_field_caps|_mapping|_validate/query)\b|/api/ds/query\b|/api/v\d+/query(_range)?\b")
LOCAL_HOST = re.compile(r"^(https?://)?(localhost|127\.\d+\.\d+\.\d+|\[?::1\]?|0\.0\.0\.0)(:\d+)?([/?#]|$)", re.I)
MCP_READ = {"get", "list", "show", "describe", "search", "query", "read", "find", "lookup", "fetch", "count", "explain", "resolve",
            "status", "stats", "health", "check", "inspect", "view", "ping"}
MCP_WRITE = {"create", "delete", "destroy", "remove", "update", "modify", "set", "patch", "put", "post", "apply", "add", "resize",
             "rename", "move", "restore", "enable", "disable", "restart", "reboot", "start", "stop", "write", "edit", "deploy",
             "install", "upgrade", "reset", "clear", "kill", "regenerate", "rotate", "recount", "reconsider", "decommission",
             "purge", "silence", "acknowledge", "import", "save"}


def words(text):
    try:
        return shlex.split(text, posix=True)
    except ValueError:
        return text.split()


def positional(args):
    """the command's own words: options removed, and the value of an option that takes one"""
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
        elif a.startswith("-"):
            skip = a in VALUE_OPTS
        else:
            out.append(a)
    return out


def starts(pos, table, depth=4):
    return any(tuple(pos[:n]) in table for n in range(1, depth + 1))


def unwrap(w):
    """drop VAR=value prefixes and wrappers (sudo -u x, timeout 5, env ...)"""
    while w:
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", w[0]):
            w = w[1:]
        elif os.path.basename(w[0]) in WRAPPERS:
            name, w = os.path.basename(w[0]), w[1:]
            while w and w[0].startswith("-"):
                w = w[2:] if name == "sudo" and w[0] in ("-u", "-g", "-h", "-p", "-C", "-D") else w[1:]
            if name in ("timeout", "watch") and w and re.match(r"^\d+(\.\d+)?[smhd]?$", w[0]):
                w = w[1:]                                # timeout 5 cmd; watch -n 5 cmd
        else:
            break
    return w


def ceph(args):
    pos = [p.lower() for p in positional(args)]
    if not pos:
        return None
    if pos[0] in ("tell", "daemon") and len(pos) >= 3:
        return None if starts(pos[2:], TELL_READ, 3) else f"ceph {pos[0]} {pos[1]} {' '.join(pos[2:4])} changes or is not a known read"
    if pos[0] == "pg" and len(pos) >= 3 and re.match(r"^\d+\.[0-9a-f]+$", pos[1]) and pos[2] in ("query", "list_unfound", "list_missing"):
        return None
    if pos[:2] in (["auth", "ls"], ["auth", "get"], ["auth", "export"], ["auth", "print-key"], ["config-key", "get"], ["config-key", "dump"]):
        return f"ceph {' '.join(pos[:2])} prints keys (rule 4)"
    if pos[:2] in (["health", "mute"], ["health", "unmute"]):
        return f"ceph {' '.join(pos[:2])} changes what the cluster reports"
    if pos[:2] == ["orch", "ls"] and "--export" in args:
        return "ceph orch ls --export prints full service specifications (they can hold TLS private keys)"
    return None if starts(pos, CEPH_READ) else f"ceph {' '.join(pos[:3])} is not a known read-only command"


def radosgw(args, whole):
    pos = [p.lower() for p in positional(args)]
    if not pos:
        return None
    if tuple(pos[:2]) == ("user", "info") and re.search(r"radosgw-admin[^|;&]*\buser\s+info\b[^|;&]*\|\s*jq\b", whole):
        return None
    if tuple(pos[:2]) in RGW_KEYS:
        return (f"radosgw-admin {' '.join(pos[:2])} returns secret keys (rule 4): for user info give the user the command "
                "with a projection, | jq '{user_id,tenant,suspended,max_buckets,user_quota,bucket_quota}'") \
            if pos[1] in ("info", "get") else f"radosgw-admin {' '.join(pos[:2])} changes identities"
    return None if starts(pos, RGW_READ, 3) else f"radosgw-admin {' '.join(pos[:3])} is not a known read-only command"


def curl(prog, args, text):
    method = ""
    for i, a in enumerate(args):
        if a in ("-X", "--request") and i + 1 < len(args):
            method = args[i + 1].upper()
        elif a.startswith("-X") and len(a) > 2:
            method = a[2:].upper()
    body = any(a in ("-d", "-F", "-T", "--form", "--upload-file", "--json") or a.startswith(("--data", "-d", "--post-")) for a in args)
    if method in ("", "GET", "HEAD", "OPTIONS") and not body:
        return None, ""
    urls = [a for a in args if re.match(r"^(https?://|[\w.-]+(:\d+)?/)", a)]
    if urls and all(LOCAL_HOST.match(u) for u in urls):
        return None, ""
    if any(READ_POST.search(u) for u in urls) and method in ("", "POST", "GET"):
        return None, ""
    return "ask", f"{prog} {method or 'POST'} sends data to another host"


def one(w, whole, remote, depth):
    """(level, why) for one command: level None | 'ask' | 'block'"""
    w = unwrap(w)
    if not w:
        return None, ""
    prog, args = os.path.basename(w[0]), w[1:]
    text = " ".join([prog] + args)
    if prog in ("bash", "sh", "zsh", "dash", "ksh") and "-c" in args and depth < 4:
        i = args.index("-c")
        return check(args[i + 1] if i + 1 < len(args) else "", remote, depth + 1)
    if prog == "ssh" and depth < 4:
        i = 0
        while i < len(args) and args[i].startswith("-"):
            i += 2 if len(args[i]) == 2 and args[i][1] in SSH_VALUE_OPTS else 1
        rest = []
        for a in args[i + 1:]:
            if re.match(r"^\d*[<>]", a):                # > out.txt, 2>/dev/null: this machine's shell, not the remote command
                break
            rest.append(a)
        return check(" ".join(rest), True, depth + 1) if rest else (None, "")
    if prog in ("podman", "docker") and args[:1] == ["exec"] and depth < 4:
        rest = args[1:]
        while rest and rest[0].startswith("-"):
            rest = rest[2:] if rest[0] in ("-u", "--user", "-e", "--env", "-w", "--workdir") else rest[1:]
        return check(" ".join(shlex.quote(x) for x in rest[1:]), True, depth + 1) if len(rest) > 1 else (None, "")
    if prog == "cephadm":
        pos = positional(args)
        if pos[:1] == ["shell"]:
            if "--" not in args:
                return "block", "an interactive cephadm shell cannot be checked: give the single command after --"
            return check(" ".join(shlex.quote(x) for x in args[args.index("--") + 1:]), True, depth + 1)
        return (None, "") if pos[:1] and pos[0] in CEPHADM_READ or not pos else ("block", f"cephadm {pos[0]} changes the host or the cluster")
    why = None
    if prog == "ceph":
        why = ceph(args)
    elif prog == "radosgw-admin":
        why = radosgw(args, whole)
    elif prog == "rados":
        pos = positional(args)
        why = None if not pos or pos[0] in RADOS_READ else f"rados {pos[0]} writes or is not a known read"
    elif prog == "rbd":
        pos = positional(args)
        ok = not pos or pos[0] in RBD_READ or pos[:2] in (["snap", "ls"], ["snap", "list"], ["pool", "stats"]) or "status" in pos[1:3]
        why = None if ok else f"rbd {' '.join(pos[:2])} changes images or is not a known read"
    elif prog == "ceph-volume":
        pos = positional(args)
        why = None if pos[:2] in (["lvm", "list"], ["raw", "list"]) or pos[:1] == ["inventory"] or not pos else f"ceph-volume {' '.join(pos[:2])} changes devices"
    elif prog in ("ceph-objectstore-tool", "ceph-bluestore-tool", "ceph-authtool", "ceph-kvstore-tool", "ceph-monstore-tool"):
        why = f"{prog} works on a daemon's store or keys"
    elif prog == "aws":
        pos = positional(args)
        if "s3api" in pos:
            op = (pos[pos.index("s3api") + 1:] or [""])[0]
            why = None if op.startswith(("get-", "head-", "list-")) or not op else f"aws s3api {op} changes S3 data or configuration"
        elif "s3" in pos:
            sub = (pos[pos.index("s3") + 1:] or [""])[0]
            why = None if sub in ("ls", "") else f"aws s3 {sub} writes, deletes or signs (only ls is a read here)"
    elif prog == "s3cmd":
        pos = positional(args)
        why = None if not pos or pos[0] in S3CMD_READ else f"s3cmd {pos[0]} changes S3 data or configuration"
    elif prog == "mc":
        pos = positional(args)
        why = None if not pos or pos[0] in MC_READ or pos[:2] == ["admin", "info"] else f"mc {' '.join(pos[:2])} changes data, or prints keys"
    elif prog == "s5cmd":
        pos = positional(args)
        why = None if not pos or pos[0] in S5CMD_READ else f"s5cmd {pos[0]} writes or deletes"
    elif prog == "rclone":
        pos = positional(args)
        why = None if not pos or pos[0] in RCLONE_READ else f"rclone {pos[0]} writes, deletes, or prints keys"
    elif prog == "ilorest":
        pos = positional(args)
        why = None if not pos or pos[0].lower() in ILOREST_READ else f"ilorest {pos[0]} changes the server"
    elif prog == "ipmitool":
        why = "ipmitool command changes the server" if IPMI_CHANGE.search(text) else None
    elif prog in ("ssacli", "hpssacli", "storcli", "storcli64", "perccli"):
        why = None if re.search(r"\bshow\b|\bhelp\b|\bversion\b", text) else f"{prog}: only show commands are reads"
    elif prog == "smartctl":
        why = "smartctl test or setting change" if any(a in ("-t", "--test", "-X", "--abort", "-s", "--smart", "-o", "-S") or a.startswith(("--test=", "--smart=")) for a in args) else None
    elif prog in ("curl", "wget"):
        return curl(prog, args, text)
    else:
        if remote:
            if HOST_CHANGE.match(text):
                return "block", f"`{text[:80]}` changes a remote host"
            return (None, "") if prog in REMOTE_READ else ("ask", f"`{text[:80]}` on a remote host is not a known read command")
        if LOCAL_ASK.match(text):
            return "ask", f"`{text[:80]}` changes this machine"
        return None, ""
    return ("block", why) if why else (None, "")


def check(cmd, remote=False, depth=0):
    worst = (None, "")
    inner = [m.group(1) or m.group(2) for m in SUBST.finditer(cmd)] if depth < 4 else []      # $(...) and `...`
    for sub in inner:
        level, why = check(sub, remote, depth + 1)
        if level == "block":
            return level, why
        if level == "ask" and worst[0] is None:
            worst = (level, why)
    for seg in segments(cmd):
        level, why = one(words(seg), cmd, remote, depth)
        if level == "block":
            return level, why
        if level == "ask" and worst[0] is None:
            worst = (level, why)
    return worst


def inside(path, cwd, folder):
    """the path relative to folder ("" for the folder itself), or None when it is somewhere else"""
    if not path or not folder:
        return None
    p = os.path.realpath(os.path.join(cwd or os.getcwd(), os.path.expanduser(str(path))))
    root = os.path.realpath(folder)
    if p == root:
        return ""
    return p[len(root) + 1:].replace(os.sep, "/") if p.startswith(root + os.sep) else None


def protected(path, cwd):
    """a brain file only people change: the installed plugin, and everything in the team repository outside knowledge/
    and docs/ (the rules, the plugin's source, the connections, join.sh, the git folder)"""
    if inside(path, cwd, PLUGIN) is not None:
        return True
    rel = inside(path, cwd, ROOT)
    return rel is not None and not rel.startswith(WRITABLE)


def shell_touches_brain(cmd, cwd):
    """the protected brain file a shell command would write: a redirect or tee into it, sed / perl -i on it, rm, mv,
    truncate, chmod, git checkout of it, or cp / install / ln onto it. Reading or copying it elsewhere passes."""
    for seg in segments(cmd):
        targets = re.findall(r">>?\s*([^\s;|&]+)", seg)
        w = [t for t in words(re.sub(r"\d*>>?\s*\S+", " ", seg)) if t and not t.startswith("-")]
        prog = os.path.basename(unwrap(w)[0]) if unwrap(w) else ""
        rest = unwrap(w)[1:]
        if prog == "tee" or prog in ("rm", "mv", "truncate", "shred", "chmod", "chown") or \
                (prog in ("sed", "perl") and re.search(r"\s(-[a-zA-Z]*i|--in-place)", seg)):
            targets += rest
        elif prog in ("cp", "install", "ln", "rsync") and rest:
            targets.append(rest[-1])
        elif prog == "git" and rest[:1] and rest[0] in ("checkout", "restore", "rm", "mv"):
            targets += rest[1:]
        for t in targets:
            if protected(t.strip("'\""), cwd):
                return t
    return None


def allowed(cmd):
    try:
        with open(os.path.join(ROOT or os.devnull, "rules", "guard-allow.txt"), encoding="utf-8") as f:
            pats = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    except OSError:
        return False
    parts = segments(cmd)
    return bool(parts) and all(any(fnmatch.fnmatch(s, p if "*" in p else p + "*") for p in pats) for s in parts)


def own_search(cmd, cwd):
    """`python3 <this plugin>/tools/search.py ...` and nothing else on the line: the docs search without MCP"""
    if SUBST.search(cmd) or re.search(r"[<>]", cmd):
        return False
    parts = segments(cmd)
    w = words(parts[0]) if len(parts) == 1 else []
    if len(w) < 2 or os.path.basename(w[0]) not in ("python3", "python"):
        return False
    target = os.path.realpath(os.path.join(cwd or os.getcwd(), os.path.expanduser(w[1])))
    return target in {os.path.realpath(os.path.join(d, "tools", "search.py")) for d in (PLUGIN, os.path.join(ROOT, NAME)) if d}


def decide(data):
    name = str(data.get("tool_name") or "")
    inp = data.get("tool_input") or {}
    cwd = data.get("cwd") or os.getcwd()
    if name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        path = inp.get("file_path") or inp.get("notebook_path") or ""
        if protected(path, cwd):
            return 2, (f"BLOCKED: {path} is part of the brain's rules or code. Only people change it (in the team repository, "
                       "with a commit). Tell the user what you would change and why; facts go under knowledge/.")
        return 0, ALLOW if (inside(path, cwd, ROOT) or "").startswith("knowledge/") else ""
    if name == "Bash":
        cmd = str(inp.get("command", ""))
        hit = shell_touches_brain(cmd, cwd)
        if hit:
            return 2, f"BLOCKED: this command would change {hit}, part of the brain's rules or code. Only people change it."
        if own_search(cmd, cwd):
            return 0, ALLOW
        if allowed(cmd):
            return 0, ""
        level, why = check(cmd)
        if level == "block":
            return 2, (f"BLOCKED by the read-only rule: {why}. Storage, S3 data, hosts and hardware are read-only here: give "
                       "the user the exact command labelled 'to be run by you', with pre-checks, verification and rollback.")
        if level == "ask":
            return 0, json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                                         "permissionDecisionReason": f"Read-only guard: {why}. Allow?"}})
        return 0, ""
    if name.startswith("mcp__"):
        own = name.startswith(OWN_MCP)
        if own and name[len(OWN_MCP):].startswith(("docs-local__", "docs-http__")):
            return 0, ALLOW
        toks = [t for t in re.split(r"[_\-.\s]+", re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name.split("__", 2)[-1]).lower()) if t]
        bad = [t for t in toks if t in MCP_WRITE]
        if toks and toks[0] in MCP_READ:
            bad = [t for i, t in enumerate(toks) if t in MCP_WRITE and i and toks[i - 1] in ("and", "then", "or")]
        method = str(inp.get("method") or inp.get("http_method") or "").upper()
        if bad or method in ("POST", "PUT", "PATCH", "DELETE"):
            return 2, (f"BLOCKED by the read-only rule: {name} looks like a change ({', '.join(bad) or method}). Give the user "
                       "the steps to run instead.")
        return 0, ALLOW if own else ""
    return 0, ""


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(data, dict):
        return 0
    try:
        rc, msg = decide(data)
    except Exception:                                   # unexpected input: fail closed for shell and MCP calls
        name = str(data.get("tool_name") or "")
        rc, msg = (2, "BLOCKED by the read-only rule: the guard could not read this call's input.") \
            if name == "Bash" or name.startswith("mcp__") else (0, "")
    if msg:
        print(msg, file=sys.stderr if rc == 2 else sys.stdout)
    return rc


if __name__ == "__main__":
    sys.exit(main())
