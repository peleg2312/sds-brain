# The offline documentation library (docs/)

Everything under `docs/<vendor>/<product>/` is searched by the `sds-docs` server (and `python3 tools/search.py`).
The index is built on each machine (`.cache/docs.db`, a few seconds) and refreshed when files here change.

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
add a one-line `SOURCE.md` saying where they came from, commit and push. Everyone's next session indexes them.
PDF files need the `pypdf` Python package on the machine; without it they are skipped and the rest is indexed.
Check what is indexed with `python3 tools/docs_server.py --index`.

## Terms
These are copies of public vendor documentation, kept for internal offline reference; each remains under its
publisher's terms (NetApp's legal notices are in each `netapp/*/_include/` and `legal-notices.adoc`). Do not publish
this folder outside the organization.
