# The offline documentation library (docs/)

`docs/<vendor>/<product>/` holds the documents; who indexes and serves them depends on where the team runs:

| | Index (the database) | Searched through |
|---|---|---|
| The team has the VM docs service (`vm-setup.py` was run) | One, on the VM: `/opt/paas/libraries/sds/docs.db`, built from this folder | `docs-http` from every machine; `docs-local` reads it directly on the VM itself |
| No VM | One per machine: `.cache/docs.db` in the clone, built in a few seconds at the first session | `docs-local` |

The team's own knowledge (`knowledge/`) is a second, small index either way: `docs-local` builds it on each machine
at every start (`.cache/knowledge.db`), and the VM's docs service keeps one for the team from the repository
(every 10 minutes, and at once after a note is pushed). Neither database is ever committed.

| Vendor / product | Contents | Source |
|---|---|---|
| `netapp/storagegrid-118`, `-119`, `-120` | The complete StorageGRID 11.8, 11.9 and 12.0 documentation (AsciiDoc sources, about 850 pages each) | github.com/NetAppDocs/storagegrid-118, -119, -120 at the commit in each `.source_commit`; rendered at docs.netapp.com |
| `ceph/squid`, `ceph/reef` | Health checks, monitoring, RGW admin / S3 / multisite / multitenancy / metrics, cephadm, configuration, mClock | docs.ceph.com (pages listed in `manifest.json`) |
| `ibm/storage-ceph` | Concepts and Architecture Guide (REDP-5721), recovery and backfill, throttles, release-to-package matrix | ibm.com/support, redbooks.ibm.com |
| `aws/s3` | S3 API and user guide pages: errors, SigV4, presigned URLs, multipart, versioning, lifecycle, Object Lock, 403 troubleshooting, IAM policy evaluation | docs.aws.amazon.com |
| `grafana/grafana`, `prometheus/prometheus`, `elastic/elasticsearch` | Datasources, service accounts, query editors, exposition formats, functions, search and health APIs | grafana.com, prometheus.io, elastic.co |
| `hpe/ilo-redfish` | iLOrest and Redfish concepts and services | servermanagementportal.ext.hpe.com |
| `redhat/okp-mcp`, `podman/podman`, `linux/kernel-admin` | okp-mcp configuration, Quadlet and container inspect, kernel admin guide index | their project sites |

Each single page's original address and title are in its product's `manifest.json`; search results cite them.

## Not here
- **Red Hat Ceph Storage and RHEL** manuals and release notes (Red Hat's site refused the download when the library
  was built). Add them, or connect the Red Hat offline portal (`connections/okp/README.md`).
- StorageGRID fixed-issue PDFs (support login), HPE model-specific service guides.

## Add your own documents
Put PDF, HTML, Markdown, AsciiDoc or text files in `docs/<vendor>/<product>/` (for example `docs/redhat/rhcs-8.1/`),
add a one-line `SOURCE.md` saying where they came from, commit and push. Then:
- with the VM: `sudo python3 vm-setup.py` on the VM again (it copies the folder and rebuilds the VM's index);
- without: nothing, everyone's next session indexes them.

PDF files need the `pypdf` Python package on the machine that indexes; without it they are skipped and the rest is
indexed. What a machine searches: `python3 brain-sds/tools/docs_server.py --index`.

## Terms
These are copies of public vendor documentation, kept for internal offline reference; each remains under its
publisher's terms (NetApp's legal notices are in each `netapp/*/_include/` and `legal-notices.adoc`). Do not publish
this folder outside the organization.
