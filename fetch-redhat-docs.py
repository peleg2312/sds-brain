#!/usr/bin/env python3
"""Add a Red Hat documentation set to the library (docs/redhat/<name>/), one single-page HTML file per guide, with a
manifest.json so every search result cites the guide's docs.redhat.com address.

    python3 fetch-redhat-docs.py rhcs 9                     Red Hat Ceph Storage 9  -> docs/redhat/rhcs-9/
    python3 fetch-redhat-docs.py rhcs 8.1                   -> docs/redhat/rhcs-8.1/
    python3 fetch-redhat-docs.py rhel 9 --guides managing_storage_devices,configuring_and_managing_networking
    python3 fetch-redhat-docs.py rhcs 9 --from-dir ~/Downloads/rhcs9     files you saved in a browser (below)
    python3 fetch-redhat-docs.py rhcs 9 --list              only list the guides

Run it on a machine where docs.redhat.com opens in a browser (your laptop, a connected jump host): Red Hat refuses
some networks and automated clients ("Access Denied", HTTP 403). This script does not try to get around that; when it
happens, use the browser instead: open each guide, choose "Single-page HTML" (or the PDF), save the page into one
folder, and run the script with --from-dir on that folder.

Then commit docs/redhat/<name>/ and push. Every machine without docs-http indexes it at its next session; for the
VM run `sudo python3 vm-setup.py` again; for OpenShift rebuild the docs image (connections/openshift/README.md).
The documentation stays under Red Hat's terms: internal reference only (LIBRARY.md). Standard library, Python 3.9."""
import argparse
import html
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PRODUCTS = {"rhcs": ("red_hat_ceph_storage", "Red Hat Ceph Storage"),
            "rhel": ("red_hat_enterprise_linux", "Red Hat Enterprise Linux")}
AGENT = "sds-brain-docs-fetch/1.0 (internal offline documentation mirror; python-urllib)"


def get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def guides(base, product, version):
    """[(slug, title)] from the product's landing page: its links to /html/<slug>"""
    page = get(f"{base}/en/documentation/{product}/{version}")
    rx = re.compile(r'<a[^>]+href="(?:https://docs\.redhat\.com)?/en/documentation/' + re.escape(product) + "/" +
                    re.escape(version) + r'/html(?:-single)?/([a-z0-9_]+)(?:/[^"]*)?"[^>]*>(.*?)</a>', re.S | re.I)
    out = {}
    for slug, text in rx.findall(page):
        title = html.unescape(re.sub(r"<[^>]+>|\s+", " ", text)).strip()
        if slug not in out or (title and not out[slug]):
            out[slug] = title
    return sorted(out.items())


def save_manifest(dest, entries):
    path = os.path.join(dest, "manifest.json")
    try:
        old = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        old = {}
    old.update(entries)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(old, f, indent=2, sort_keys=True)
        f.write("\n")


def from_dir(src, dest, product, version, label, base):
    """files saved in a browser: the guide's address from the page itself when it says it (canonical / og:url)"""
    entries, n = {}, 0
    for name in sorted(os.listdir(src)):
        p = os.path.join(src, name)
        if not os.path.isfile(p) or not name.lower().endswith((".html", ".htm", ".pdf")):
            continue
        target = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
        shutil.copy2(p, os.path.join(dest, target))
        url, title = f"{base}/en/documentation/{product}/{version}", os.path.splitext(name)[0].replace("_", " ")
        if name.lower().endswith((".html", ".htm")):
            text = open(p, encoding="utf-8", errors="replace").read(400_000)
            m = re.search(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"', text) or re.search(r'<meta[^>]+property="og:url"[^>]+content="([^"]+)"', text)
            if m and "docs.redhat.com" in m.group(1):
                url = m.group(1)
            t = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
            if t:
                title = html.unescape(re.sub(r"\s+", " ", t.group(1))).strip()
        entries[target] = {"title": title[:200] or f"{label} {version}", "url": url}
        n += 1
    if not n:
        sys.exit(f"fetch: no .html, .htm or .pdf files in {src}")
    save_manifest(dest, entries)
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("product", choices=sorted(PRODUCTS))
    ap.add_argument("version", help="as in the documentation's address: 9, 8.1, 7 ...")
    ap.add_argument("--guides", help="only these guides (comma-separated names from --list)")
    ap.add_argument("--from-dir", help="a folder of pages or PDFs saved in a browser, instead of downloading")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--to", help="default docs/redhat/<product>-<version>")
    ap.add_argument("--base-url", default="https://docs.redhat.com", help=argparse.SUPPRESS)   # tests
    ap.add_argument("--pause", type=float, default=1.0, help="seconds between pages (be gentle with the site)")
    a = ap.parse_args()
    product, label = PRODUCTS[a.product]
    if not re.fullmatch(r"[0-9][0-9.]*", a.version):
        sys.exit("fetch: version like 9 or 8.1")
    dest = a.to or os.path.join(HERE, "docs", "redhat", f"{a.product}-{a.version}")
    base = a.base_url.rstrip("/")
    if a.from_dir:
        os.makedirs(dest, exist_ok=True)
        n = from_dir(os.path.expanduser(a.from_dir), dest, product, a.version, label, base)
        print(f"{n} files into {os.path.relpath(dest, HERE)}; commit and push them (git add {os.path.relpath(dest, HERE)})")
        return 0
    try:
        found = guides(base, product, a.version)
    except urllib.error.HTTPError as e:
        sys.exit(f"fetch: {base} answered HTTP {e.code} for the {label} {a.version} page. Red Hat refuses some networks and "
                 "automated clients: save the guides in a browser instead (Single-page HTML or PDF, all into one folder) "
                 "and run this again with --from-dir <that folder>.")
    except OSError as e:
        sys.exit(f"fetch: {base} is not reachable from this machine ({e}). Run it where docs.redhat.com opens, or use --from-dir.")
    if a.guides:
        want = {g.strip() for g in a.guides.split(",") if g.strip()}
        found = [(s, t) for s, t in found if s in want] + [(s, "") for s in sorted(want - {s for s, _ in found})]
    if not found:
        sys.exit(f"fetch: no guides found on the {label} {a.version} page (has the site changed?). Use --guides or --from-dir.")
    if a.list:
        for slug, title in found:
            print(f"{slug:55} {title}")
        return 0
    os.makedirs(dest, exist_ok=True)
    entries, failed = {}, []
    for i, (slug, title) in enumerate(found, 1):
        url = f"{base}/en/documentation/{product}/{a.version}/html-single/{slug}/index"
        try:
            page = get(url, timeout=120)
        except (urllib.error.URLError, OSError) as e:
            failed.append(f"{slug} ({getattr(e, 'code', '') or e})")
            continue
        with open(os.path.join(dest, slug + ".html"), "w", encoding="utf-8") as f:
            f.write(page)
        if not title:
            t = re.search(r"<title>(.*?)</title>", page, re.S | re.I)
            title = html.unescape(re.sub(r"\s+", " ", t.group(1))).strip() if t else slug.replace("_", " ")
        entries[slug + ".html"] = {"title": f"{label} {a.version} {title}".strip(), "url": url.replace(base, "https://docs.redhat.com", 1)}
        print(f"  [{i}/{len(found)}] {slug}")
        time.sleep(a.pause)
    if entries:
        save_manifest(dest, entries)
    print(f"{len(entries)} guides into {os.path.relpath(dest, HERE)}" + (f"; not saved: {', '.join(failed)}" if failed else "")
          + f"\nnext: git add {os.path.relpath(dest, HERE)} && git commit -m 'docs: {label} {a.version}' && git push")
    return 0 if entries else 1


if __name__ == "__main__":
    sys.exit(main())
