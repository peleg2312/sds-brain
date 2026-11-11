# The offline documentation library (docs/)

`docs/<vendor>/<product>/` holds the documents, and `library/docs.db` their index, built ahead and committed like the
storage team's libraries (`library/MANIFEST.md` says what is in it). Nobody indexes the library at first use:

| Where | The index | Searched through |
|---|---|---|
| A member's machine without a VM docs service | `library/docs.db`, copied to `.cache/docs.db` at the first session (instant) | `docs-local` |
| The storage team's VM | `/opt/paas/libraries/sds/docs.db`, loaded with the VM's own `paas-library import` (below) | `docs-http` from every machine; `docs-local` on the VM itself |
| OpenShift | inside the docs image (`connections/http/build.py docs` copies `library/docs.db`) | `docs-http` |

The team's own knowledge (`knowledge/`) is a second, small index that is never committed: `docs-local` builds it on
each machine at every start (`.cache/knowledge.db`), and the VM's docs service keeps one for the team from the
repository (every 10 minutes, and at once after a note is pushed).

## Loading the library into the VM's docs service (the storage team's way, no script of ours)
On a machine with a clone: `python3 brain-sds/tools/docs_server.py --bundle .` writes `sds-library-<date>.tar.gz` and
its `.sha256` (about 8 MB). On the VM, as root:
```bash
paas-library import sds sds-library-<date>.tar.gz           # the VM's own tool: checks the .sha256, loads docs/ and docs.db
install -d /opt/paas/teams/sds                              # the team, so the docs service also indexes its knowledge
printf '{"name": "sds", "title": "SDS object storage", "library": "sds", "remote": "https://<gitlab>/<group>/sds-brain.git"}\n' \
  > /opt/paas/teams/sds/team.json
paas-user git-token <gitlab host>                           # once per git host, if not stored yet: the service pulls with it
curl -s -X POST -H "Authorization: Bearer $(cat /etc/paas/docs-token)" "https://$(hostname -f):8443/refresh?team=sds"
```
Then, in a clone, point the plugin at the service and give members the VM's certificate (join.sh trusts it), commit, push:
```bash
cp /etc/paas/market/paas-ui.crt brain-sds/lib/paas-ui.crt   # from the VM (mkdir -p brain-sds/lib first)
python3 connections/http/use.py docs-http "https://<vm>:8443/mcp?team=sds" --token-file /etc/paas/docs-token
git add brain-sds/.mcp.json brain-sds/lib && git commit -m "SDS brain: docs-http on the VM" && git push
```
`vm-setup.py` does the same in one command, if you prefer it.

| Vendor / product | Contents | Source |
|---|---|---|
| `netapp/storagegrid-118`, `-119`, `-120` | The complete StorageGRID 11.8, 11.9 and 12.0 documentation (AsciiDoc sources, about 850 pages each) | github.com/NetAppDocs/storagegrid-118, -119, -120 at the commit in each `.source_commit`; rendered at docs.netapp.com |
| `ceph/squid`, `ceph/reef` | Health checks, monitoring, RGW admin / S3 / multisite / multitenancy / metrics, cephadm, configuration, mClock | docs.ceph.com (pages listed in `manifest.json`) |
| `ibm/storage-ceph` | Concepts and Architecture Guide (REDP-5721), recovery and backfill, throttles, release-to-package matrix | ibm.com/support, redbooks.ibm.com |
| `aws/s3` | S3 API and user guide pages: errors, SigV4, presigned URLs, multipart, versioning, lifecycle, Object Lock, 403 troubleshooting, IAM policy evaluation | docs.aws.amazon.com |
| `grafana/grafana`, `prometheus/prometheus`, `elastic/elasticsearch` | Datasources, service accounts, query editors, exposition formats, functions, search and health APIs | grafana.com, prometheus.io, elastic.co |
| `hpe/ilo-redfish` | iLOrest and Redfish concepts and services | servermanagementportal.ext.hpe.com |
| `redhat/rhcs-9` | Catalog of the Red Hat Ceph Storage 9.0 / 9.1 / 9.2 guides and release notes: what each covers and its PDF link, and the PDFs: 9.0 User Guide and chapter guides, 9.0 / 9.1 / 9.2 release notes, 9.1 User Guide | docs.redhat.com/en/documentation/red_hat_ceph_storage/9 |
| `redhat/okp-mcp`, `podman/podman`, `linux/kernel-admin` | okp-mcp configuration, Quadlet and container inspect, kernel admin guide index | their project sites |
| `netapp/storagegrid-landing` | The 11.8, 11.9 and 12.0 documentation landing pages (tables of contents) | docs.netapp.com, captured by the first SDS brain |
| `anthropic/claude-code` | Claude Code CLI reference, MCP configuration, memory (CLAUDE.md) | code.claude.com, captured by the first SDS brain |
| `modelcontextprotocol/spec-2025-11-25` | MCP specification 2025-11-25: basics, lifecycle, transports (stdio, HTTP), tools, schema | modelcontextprotocol.io, captured by the first SDS brain |
| `atlassian/confluence` | Confluence Cloud page API, Data Center page content through REST, the storage format (for exporting pages into the library) | developer.atlassian.com, support / confluence.atlassian.com, captured by the first SDS brain |

Each single page's original address and title are in its product's `manifest.json`; search results cite them. Every
document of the first SDS brain (github.com/SDS3-6789/sds-brain, `knowledge/vendor/`) is here: its 2,499 StorageGRID
pages as NetApp's own sources, and its 109 single-page snapshots under their original addresses.

## Not here
- **Red Hat Ceph Storage and RHEL** manuals and release notes (Red Hat's site refuses automated downloads from some
  networks, including the one the library was built on). Add them from a machine where docs.redhat.com opens:
  `python3 fetch-redhat-docs.py rhcs 9` (also `rhcs 8.1`, `rhel 9 --guides ...`) saves each guide as single-page HTML
  under `docs/redhat/rhcs-9/` with a manifest, so results cite the docs.redhat.com address; where the script is refused
  too, save the guides in a browser and run it with `--from-dir`. Or connect the Red Hat offline portal
  (`connections/okp/README.md`).
- **RHCS 9.1 chapter PDFs and the 9.2 User Guide** (access.redhat.com returned 404 for them on 2026-11-11; the 9.0
  chapter PDFs from IBM Docs cover the same topics).
- StorageGRID fixed-issue PDFs (support login), HPE model-specific service guides.

## Add your own documents
Put PDF, HTML, Markdown, AsciiDoc or text files in `docs/<vendor>/<product>/` (for example `docs/redhat/rhcs-8.1/`),
add a one-line `SOURCE.md` saying where they came from, rebuild the index (`python3 brain-sds/tools/docs_server.py
--build-library`; `check.py` fails until you do), commit `docs/` and `library/`, and push. Then:
- with the VM: a new bundle and `paas-library import sds` again (or `vm-setup.py`);
- without: nothing, everyone's next session copies the new index.

PDF files need the `pypdf` Python package on the machine that indexes; without it they are skipped and the rest is
indexed. What a machine searches: `python3 brain-sds/tools/docs_server.py --index`.

## Terms
These are copies of public vendor documentation, kept for internal offline reference; each remains under its
publisher's terms (NetApp's legal notices are in each `netapp/*/_include/` and `legal-notices.adoc`). Do not publish
this folder outside the organization.
