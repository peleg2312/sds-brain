# Storage rules: identity, versions, evidence and each domain

Loaded with the golden rules (main.md) in every session. People change this file with a commit; Claude never does.

## Identity before evidence
- An investigation starts with: cluster or grid (`knowledge/environment.md`), backend, exact installed release / build,
  the endpoint or FSID that maps to it, the symptom, and the incident window in UTC (keep the user's local time beside
  it when they gave one). Never infer the cluster from a hostname, the last login, a shell's default context or a
  Grafana default datasource.
- Live output names its identity (FSID, grid name, endpoint, datasource uid): check it is the one asked about before
  using it; stop and say so when it differs. Never combine records from two clusters or grids without saying so.
- A Grafana dashboard variable, a query filter or an Elasticsearch index pattern is a view, not an access boundary:
  what a token may read is decided by the backend.

## Versions
- Ceph is cephadm-managed and containerized: the RHCS release (7.1z7, 8.1z9), the host's RHEL release, the daemon
  package / container version and the image digest are separate facts, and not every daemon is upgraded together
  (`ceph versions` shows the mix).
- The installed vendor's release notes, support matrix and versioned documentation decide what is supported. Upstream
  Ceph and IBM Storage Ceph pages explain behaviour; they do not establish Red Hat support. AWS pages explain AWS S3:
  check behaviour, IAM semantics, error meaning and consistency against the installed RGW / StorageGRID release.
- StorageGRID "12" needs its minor and build; unversioned NetApp pages may describe a newer release than the grid runs.
- Cite title + url (or the knowledge file) + version, and the date a note was verified. Report conflicts between
  sources and the evidence that is missing. Web or document research is never "tested on the cluster".
- The library is not complete: a catalog entry, a contents page or a "RHEL" label on a portal result is not the
  manual itself, and an empty filtered search does not prove the documentation lacks the answer (search wider).

## Reads are bounded, outputs are safe
- Bound every read: time window, page size, number of objects / accounts, fields (a `jq` projection). Prefer status
  and metadata to payloads, full cluster dumps, all-account listings or support bundles.
- Never print raw `radosgw-admin user info`, Objectify account responses, environment dumps or unfiltered support
  bundles: they carry keys. No deep scrub, rebalance tuning or write benchmark, even "to measure".

## Ceph / RGW
Start with the `ceph-health` and `ceph-slow-ops` skills. Separate monitor quorum, OSD availability, PG states, capacity
pressure, recovery / backfill, RGW service state and multisite replication. Admin-socket and other version-sensitive
commands differ between Reef and Squid: check the command's help or the release documentation before suggesting one.
Take short bounded samples; avoid repeated expensive PG / OSD dumps.

## S3 / StorageGRID
Record the backend, client SDK / CLI and version, API operation, request ID, endpoint and addressing style, where TLS
is terminated, signing region and the exact error. Separate identity, account / tenant, bucket policy and object
permissions. On StorageGRID separate the logical tenant quota from physical data and metadata capacity, and from ILM
placement and queue evidence. Check the installed release before proposing an AWS-documented setting.

## Monitoring: Grafana, the custom exporter, Elasticsearch
Read the dashboard first: datasource uids, variables, panel expressions, transformations, units, time settings. Never
invent a metric, label, index or field name. Prometheus behind Grafana is not confirmed until `environment.md` says
so. For exporter data know the metric's type, unit, scrape interval and counter-reset behaviour (one reviewed sample);
for Elasticsearch the authorized index, timestamp field, field mappings and request-ID field. Always a cluster
selector and a bounded window.

## RHEL hosts and HPE hardware
Confirm the server model, generation, BIOS / iLO / controller / drive firmware and the OS / kernel before choosing
documentation. Map an OSD to its device and bay with two independent pieces of evidence (Ceph / OS and the controller).
High latency alone does not mean a failed disk, and an OS device name alone does not identify the drive to replace.

## Objectify
Read-only, and off until its contract is supplied (`connections/objectify/INTEGRATION.md`). The Swagger screenshot is
an endpoint list, not an API contract; `obj_acc` is literal, not a placeholder; `/account/parlay` stays excluded. An
account read must return the identity asked for; check it.

## Red Hat offline portal (okp)
It searches a separate portal index and runs nothing. Its search has no product filter and can label a result "RHEL"
whatever the product: read the returned title, product and version before applying it to RHCS. Keep cluster names,
incident data and credentials out of its queries; the portal is shared.
