---
name: docs-lookup
description: How to search the offline documentation library and the team knowledge - products, versions, exact terms, citing. Use whenever an answer depends on how Ceph, RGW, StorageGRID, S3, RHEL, HPE iLO, Grafana, Prometheus or Elasticsearch works, for error meanings, limits, procedures, "what does the documentation say", "is this supported".
---
# Docs lookup

The `sds-docs` MCP server searches everything under `docs/` plus `knowledge/` (notes, runbooks, captures, incidents).
Tools: `search_docs`, `read_chunk`, `read_document`, `related_docs`, `list_sources`. Without MCP:
`python3 tools/search.py "query" [--product storagegrid-119]`.

## Products (vendor / product; `list_sources` shows the current list and counts)
| Ask about | Use |
|---|---|
| StorageGRID 11.8 / 11.9 / 12.0 (full manuals: admin, ILM, S3, monitor, troubleshoot, maintain, upgrade...) | `netapp` / `storagegrid-118`, `storagegrid-119`, `storagegrid-120` |
| Ceph health checks, RGW admin, S3 API, multisite, multitenancy, cephadm, mClock, configuration, metrics | `ceph` / `squid` (RHCS 8.1), `reef` (RHCS 7.1: health checks only) |
| IBM Storage Ceph: architecture book, recovery / backfill, throttles, release-to-package matrix | `ibm` / `storage-ceph` |
| AWS S3 reference: errors, SigV4, presigned URLs, multipart, versioning, lifecycle, Object Lock, 403 guide | `aws` / `s3` |
| Grafana (Elasticsearch / Prometheus datasources, service accounts), Prometheus, Elasticsearch APIs | `grafana`, `prometheus`, `elastic` |
| HPE iLOrest and Redfish | `hpe` / `ilo-redfish` |
| The team's own knowledge | results marked `library: team knowledge` |

**Not in the library unless the team added it**: Red Hat Ceph Storage and RHEL manuals and release notes, StorageGRID
fixed-issue PDFs, HPE service guides. When the answer needs one, say so and ask the user for the page, or use the
Red Hat offline portal connection (`sds-okp`) when it is connected. Never fill the gap from memory as if cited.

## Method
1. **Pick the version first** (rule 3): the installed release from `knowledge/environment.md` decides the product.
2. **Exact terms**: error text in "quotes", health check names (`PG_DEGRADED`), S3 error codes, command names.
   `read_top=2` returns the best sections inline. Weak hit (`matched` n/m): send `queries=[...]` with 2-3
   rephrasings in the vendor's words, replacing the `unmatched` words.
3. **Read before answering**: `read_chunk` on the best 2-3 hits (`context=1` for neighbours); `read_document` only
   when the answer spans a page. `also_in` lists the same page in other versions: open the installed one.
4. **Cite**: title + url + version for each statement. An AWS or upstream page backing a claim about RGW /
   StorageGRID: say that it is the reference behaviour, not proof for the installed release.
5. A hit titled "Unverified capture" is a teammate's draft: useful lead, say it is unverified.

## Adding documents
Files (PDF, HTML, Markdown, text) placed under `docs/<vendor>/<product>/` and committed are indexed at the next
session, for the whole team (for example `docs/redhat/rhcs-8.1/`, `docs/redhat/rhel-9/`, `docs/hpe/apollo-4200-gen10/`).
Tell the user this when a needed manual is missing; adding files there is the user's step.
