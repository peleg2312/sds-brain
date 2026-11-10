#!/usr/bin/env python3
"""UserPromptSubmit hook: search the offline library with every request about the SDS world and hand Claude the best
matching documents before it answers, plus the meaning of identifiers pasted in the request (Ceph health checks, S3
error codes, error messages: the same lookups as docs-hints.py).

Silent unless the request is about the library's world (Ceph, RGW, S3, StorageGRID, the hosts, hardware, monitoring:
a word below or a product name in the library) and the match is strong (MIN_WORDS words found and MIN_COVER of the
request's words in a hit); at most MAX_LEADS documents (~30 tokens each), each once per session. "yes", "continue" or a
coding request cost nothing. Searches this machine's index, else docs-http (a few seconds at most). Standard library
only; never blocks the prompt (always exit 0). Off: SDS_DOCS_LEADS=0."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

MAX_LEADS, MIN_WORDS, MIN_COVER, MAX_QUERY_WORDS = 4, 2, 0.6, 30
DOMAIN = set("""ceph rgw radosgw rados osd osds pg pgs mon mons mgr mds cephadm rbd cephfs crush pool pools bluestore scrub
deep-scrub backfill recovery peering nearfull backfillfull quorum mclock zone zonegroup realm multisite sync s3 bucket buckets
object objects multipart presigned presign sigv4 signature acl acls cors lifecycle versioning retention objectlock worm
quota quotas tenant tenants storagegrid grid ilm erasure replication metadata cassandra haproxy keepalived balancer endpoint
endpoints tls certificate certificates rhel selinux podman systemd chrony ntp mtu bond bonding nic hpe ilo redfish apollo
proliant raid smart smartctl grafana prometheus promql elasticsearch kibana exporter dashboard alert alerts objectify
sts iam sse kms throttling slowdown latency 503 403 404 409 500""".split())
WEAK = set("""disk disks node nodes cluster volume array controller network slow full down degraded error errors""".split())
CODE_ASK = re.compile(r"\b(bug|bugs|test|tests|pytest|refactor|commit|code|function|class|lint|typing|stack ?trace)\b|\.py\b", re.I)
NOISE = re.compile(r"^(changelog|release notes?|release \d|reference)\b", re.I)
WANTS_NOISE = re.compile(r"\b(release|version|changelog|upgrade|fixed|fix(es)? in)\b", re.I)
GENERIC = set("""guide admin reference docs kernel podman""".split())


def vocabulary(db):
    """DOMAIN plus the words of every product name in the local library"""
    vocab = set(DOMAIN)
    if db:
        try:
            import sqlite3
            c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            for v, p in c.execute("SELECT DISTINCT vendor, product FROM docs"):
                for w in re.split(r"[-_/]", f"{v}-{p}".lower()):
                    if len(w) >= 4 and not w.isdigit() and w not in GENERIC:
                        vocab.add(w)
        except Exception:
            pass
    return vocab


def main():
    if os.environ.get("SDS_DOCS_LEADS") == "0":
        return 0
    data = json.load(sys.stdin)
    prompt = (data.get("prompt") or "").strip()
    if not prompt or prompt.startswith("/"):
        return 0
    import docs_access as d
    if not d.b.ROOT or not (d.local_db() or d.b.docs_http()):
        return 0
    lines = []
    # 1. identifiers pasted in the request: their meaning
    hints_file = d.seen_file("docs-hints", data.get("session_id"))
    seen = d.read_seen(hints_file)
    hints = d.identifier_hints(prompt, seen, most=3, most_errors=1)
    if hints:
        d.write_seen(hints_file, seen)
        lines += hints
    # 2. the best documents for the request itself, when it is about the library's world
    words = [w for w in re.findall(r"\S+", re.sub(r"[^\x00-\x7f]+", " ", prompt)) if not re.search(r"[/~\\]|^https?:", w)][:MAX_QUERY_WORDS]
    toks = {w.lower() for x in words for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9-]*", x)}
    about = bool(toks & vocabulary(d.local_db())) or len(toks & WEAK) >= 2
    if about and not (CODE_ASK.search(prompt) and not toks & DOMAIN):
        q = " ".join(words).replace('"', " ")
        leads, docs = [], set()
        for r in d.search(q, limit=8):
            hit, _, n = str(r.get("matched", "0/1")).partition("/")
            if r.get("library") == "team knowledge" or not n:
                continue                                      # the team's notes: docs-local / the session catalog give those
            if r.get("matched") and (int(hit) < MIN_WORDS or int(hit) / int(n) < MIN_COVER):
                continue
            title, sec = (r.get("title") or "")[:90], r.get("section") or ""
            if NOISE.search(title) and not WANTS_NOISE.search(prompt):
                continue
            if r.get("path") in docs or (r.get("title"), sec) in docs:
                continue
            docs.update({r.get("path"), (r.get("title"), sec)})
            leads.append(f"{title}" + (f" :: {sec[:60]}" if sec and sec != title else "") + f" [{r['vendor']}/{r['product']}, chunk {r['chunk_id']}]")
            if len(leads) >= MAX_LEADS:
                break
        leads_file = d.seen_file("docs-leads", data.get("session_id"))
        shown = d.read_seen(leads_file)
        leads = [x for x in leads if x not in shown]
        if leads:
            d.write_seen(leads_file, shown | set(leads))
            lines += leads
    if lines:
        print(f"Docs leads ({d.server()}; verify with read_chunk before relying on them; ignore if unrelated):\n"
              + "\n".join("- " + x for x in lines))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
