---
name: sg-capacity-metadata
description: Diagnose StorageGRID capacity - object data versus metadata, per site and node, trend and alerts. Use for "StorageGRID is full", "low object storage", "metadata capacity", "Low metadata storage alert", "how much space is left on the grid", "storage node full".
---
# StorageGRID object-data and metadata capacity

Read-only (rule 1), from Grid Manager views or the monitoring connection. Scope: grid, site, release / hotfix, UTC
interval. Written against 11.9: for 11.8 or 12.0 open the same page in that product before trusting labels or
thresholds (`product="storagegrid-118"` / `"storagegrid-120"`).

## Collect
1. Current and resolved capacity alerts: nodes / sites, onset, severity, the alert rule as deployed. Do clients see
   failed ingest, failed reads, or only less headroom?
2. **Object data and metadata separately**, used / available by site and by node, with trend and last sample time.
   Aggregate totals leave out nodes that have not reported for five minutes: an aggregate that looks better can be
   missing telemetry.
3. Metadata: used against **allowed** metadata space, not filesystem capacity and not the reserved space. In 11.9 the
   metrics are `storagegrid_storage_utilization_metadata_bytes` and
   `storagegrid_storage_utilization_metadata_allowed_bytes`; discover the real labels before querying.
4. Same interval: node availability, ingest changes, object-size distribution, ILM activity (`sg-ilm-backlog`),
   maintenance. A missing observation is not a zero.

## Interpret
- Metadata can be the limit while object-data space remains. 11.9 thresholds: 70 % of allowed space minor, 90 %
  major, 100 % critical; check the installed rule. Major or critical metadata: tell the user to escalate now.
- A trend estimate needs reliable samples and a stable workload: state the window and the uncertainty; never promise
  days from one sample. Free space at another site does not satisfy the active ILM placement.
- Tenant quota is a different number: `knowledge/notes/storagegrid-capacity-quota-ilm.md`, skill `sg-tenant-quota`.

Library: `search_docs("monitor storage capacity", product="storagegrid-119")`,
`search_docs("troubleshoot metadata", product="storagegrid-119")`.

## Not here
Deleting database files, repairs, starting an expansion, changing ILM or retention to free space.

## Result
A table: grid / site / node, metric, value, timestamp, denominator, trend, alert. Capacity pressure, placement
constraint and missing telemetry as separate hypotheses, the smallest next evidence, and the timeline of changes.
