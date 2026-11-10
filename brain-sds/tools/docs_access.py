"""The vendor documentation for the docs-leads and docs-hints hooks: the index on this machine when there is one (the VM's
library, or docs/ indexed here), else docs-http (the VM's docs service) over HTTP with a short timeout. Plus the
identifiers the library documents: Ceph health checks (PG_DEGRADED) and S3 error codes (SignatureDoesNotMatch), read
from the index, or from identifiers.json beside this file where the index is on the VM only. Standard library only."""
import json
import os
import re
import stat
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "engine")]
import brainlib as b  # noqa: E402

CEPH_CODE = re.compile(r"(?<![\w-])([A-Z][A-Z0-9]{1,15}(?:_[A-Z0-9]+){1,6})(?![\w-])")
S3_CODE = re.compile(r"(?<![\w-])((?:[A-Z][a-z0-9]+){2,6})(?![\w-])")
ERROR_CODE_HEADINGS = "%error codes%"


def tmpdir():
    """a private per-user folder for the per-session 'already said' files (a shared /tmp name can be a planted symlink)"""
    uid = os.getuid() if hasattr(os, "getuid") else None
    d = os.path.join(tempfile.gettempdir(), f"sds-brain-{uid if uid is not None else 'w'}")
    try:
        os.makedirs(d, mode=0o700, exist_ok=True)
        st = os.lstat(d)
        if (uid is None or st.st_uid == uid) and stat.S_ISDIR(st.st_mode):
            return d
    except OSError:
        pass
    return os.path.join(os.devnull, "x")


def seen_file(kind, session):
    return os.path.join(tmpdir(), f"{kind}-{re.sub(r'[^A-Za-z0-9-]', '', str(session or 'x'))}")


def local_db():
    """the index this machine searches itself, or "" when the library is reached through docs-http only"""
    if not b.ROOT:
        return ""
    vm = b.vm_library()
    if vm:
        return vm
    if b.docs_http():
        return ""
    db = os.path.join(b.CACHE, "docs.db")
    return db if os.path.isfile(db) else ""


def server():
    """the MCP server whose chunk ids these results carry"""
    return "docs-local" if local_db() else "docs-http"


_ENGINE = None


def _engine():
    global _ENGINE
    if _ENGINE is None:
        import docs_server
        import search_cli as lib
        lib._SYN.clear()
        lib._SYN.update({w: g for g in docs_server.SYNONYMS for w in g})
        _ENGINE = lib
    return _ENGINE


def search(query, vendor="", product="", limit=8, timeout=3):
    """search_docs results (chunk_id, vendor, product, title, section, matched, snippet...) or [] on any problem"""
    db = local_db()
    if db:
        try:
            lib = _engine()
            return lib.search_docs(lib.connect(db), query, vendor=vendor, product=product, limit=limit).get("results") or []
        except Exception:
            return []
    cfg = b.docs_http()
    if not cfg:
        return []
    url, auth, ca = cfg
    import ssl
    import urllib.request
    handlers = [urllib.request.ProxyHandler({})]                    # the VM is on the internal network
    if url.startswith("https"):
        ctx = ssl.create_default_context()
        if ca:
            ctx.load_verify_locations(ca)
        handlers.append(urllib.request.HTTPSHandler(context=ctx))
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "search_docs", "arguments": {
        "query": query, "vendor": vendor, "product": product, "limit": limit}}}).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json, text/event-stream", **({"Authorization": auth} if auth else {})})
    try:
        with urllib.request.build_opener(*handlers).open(req, timeout=timeout) as r:
            msg = json.loads(r.read())
        return json.loads(msg["result"]["content"][0]["text"]).get("results") or []
    except Exception:
        return []


def known():
    """{"ceph": set of documented health checks, "s3": set of documented S3 error codes}: from the local index (cached per
    build), else from identifiers.json (written by `docs_access.py --save` from the library this plugin ships with)"""
    db = local_db()
    if db:
        cache = os.path.join(tmpdir(), f"identifiers-{abs(hash(db)) % 10 ** 8}-{int(os.path.getmtime(db))}.json")
        try:
            with open(cache, encoding="utf-8") as f:
                got = json.load(f)
            return {k: set(v) for k, v in got.items()}
        except (OSError, ValueError):
            pass
        got = from_index(db)
        try:
            with open(cache, "w", encoding="utf-8") as f:
                json.dump({k: sorted(v) for k, v in got.items()}, f)
        except OSError:
            pass
        return got
    try:
        with open(os.path.join(HERE, "identifiers.json"), encoding="utf-8") as f:
            return {k: set(v) for k, v in json.load(f).items()}
    except (OSError, ValueError):
        return {"ceph": set(), "s3": set()}


def from_index(db):
    import sqlite3
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    ceph = {h.strip() for (h,) in c.execute(
        "SELECT DISTINCT f.heading FROM chunks_fts f JOIN chunks ch ON ch.id = f.rowid JOIN docs d ON d.id = ch.doc_id "
        "WHERE d.vendor IN ('ceph', 'ibm', 'redhat')") if h and CEPH_CODE.fullmatch(h.strip())}
    s3 = set()
    for (t,) in c.execute("SELECT f.text FROM chunks_fts f WHERE f.heading LIKE ?", (ERROR_CODE_HEADINGS,)):
        s3 |= set(S3_CODE.findall(t or ""))
    return {"ceph": ceph, "s3": s3}


def first_sentence(text, limit=150):
    text = re.sub(r"\s+", " ", re.sub(r"[«»]", "", text or "")).strip()
    m = re.match(r"(.{30,}?[.!?])(\s|$)", text)
    if m and len(m.group(1)) <= limit:
        return m.group(1)
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "..."


def ceph_hint(code):
    hits = [h for h in search(f'"{code}"', vendor="ceph", limit=6) if (h.get("section") or "").strip() == code]
    hits.sort(key=lambda h: h["product"] != "squid")              # the newest release first (RHCS 8.x)
    if not hits:
        return None
    h = hits[0]
    more = sorted({x["product"] for x in hits[1:] if x["product"] != h["product"]})
    return (f"{code} [{h['vendor']}/{h['product']}, chunk {h['chunk_id']}]: {first_sentence(h.get('snippet'))}"
            + (f" (also in {', '.join(more)})" if more else ""))


def s3_hint(code):
    hits = search(f'"{code}"', limit=10)
    where = []
    for h in hits:
        if "error code" in (h.get("section") or "").lower() or "error" in (h.get("title") or "").lower():
            key = f"{h['vendor']}/{h['product']}, chunk {h['chunk_id']}"
            if not any(w.startswith(f"{h['vendor']}/{h['product']},") for w in where):
                where.append(key)
    return f"{code} (S3 error code): the error-code tables [{'; '.join(where[:4])}]" if where else None


ERR = re.compile(r"(?:\b(?:error|Error|ERROR|failed|Failed|FAILED)(?: to [a-z]+)?: )([^\n\"]{12,240})")


def err_phrase(msg):
    """the longest run of 4-10 plain words in an error message (ids, numbers, paths and names with digits left out)"""
    best, cur = [], []
    for w in re.findall(r"[^\s,;:()\[\]{}'\"]+", msg):
        if re.fullmatch(r"[A-Za-z]+", w):
            cur.append(w)
            if len(cur) > len(best):
                best = cur[:]
        else:
            cur = []
    return " ".join(best[:10]) if len(best) >= 4 else None


def err_hint(phrase):
    words = phrase.split()
    while len(words) >= 4:
        hits = search('"' + " ".join(words) + '"', limit=3)
        if hits:
            h = hits[0]
            return (f'"{" ".join(words)}" [{h["vendor"]}/{h["product"]}, chunk {h["chunk_id"]}]: {h["title"][:100]}'
                    + (f" :: {h['section'][:70]}" if h.get("section") and h["section"] != h["title"] else ""))
        words = words[:-1]
    return None


def identifier_hints(text, seen, most=3, most_errors=2):
    """hint lines for the documented identifiers and error messages in text, skipping (and adding to) seen"""
    text = text[:300_000]
    ids = known()
    found = [(m.start(1), "ceph", m.group(1)) for m in CEPH_CODE.finditer(text) if m.group(1) in ids["ceph"]]
    found += [(m.start(1), "s3", m.group(1)) for m in S3_CODE.finditer(text) if m.group(1) in ids["s3"]]
    out, more = [], []
    for _, kind, code in sorted(found):
        if code in seen:
            continue
        seen.add(code)
        if len(out) >= most:
            more.append(code)
            continue
        h = ceph_hint(code) if kind == "ceph" else s3_hint(code)
        if h:
            out.append(h)
    if more:
        out.append("also documented: " + ", ".join(dict.fromkeys(more[:5])))
    errs = 0
    for m in ERR.finditer(text):
        phrase = err_phrase(m.group(1))
        if not phrase or phrase in seen:
            continue
        seen.add(phrase)
        h = err_hint(phrase)
        if h:
            out.append(h)
            errs += 1
        if errs >= most_errors:
            break
    return out


def read_seen(path):
    try:
        with open(path, encoding="utf-8") as f:
            return set(filter(None, f.read().splitlines()))
    except OSError:
        return set()


def write_seen(path, seen):
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(seen)) + "\n")
    except OSError:
        pass


if __name__ == "__main__":
    if sys.argv[1:2] == ["--save"]:            # refresh identifiers.json from this machine's index (check.py tells when stale)
        db = local_db() or os.path.join(b.CACHE, "docs.db")
        got = from_index(db)
        with open(os.path.join(HERE, "identifiers.json"), "w", encoding="utf-8") as f:
            json.dump({k: sorted(v) for k, v in got.items()}, f, indent=0)
            f.write("\n")
        print(f"identifiers.json: {len(got['ceph'])} Ceph health checks, {len(got['s3'])} S3 error codes")
