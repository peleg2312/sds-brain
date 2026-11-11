---
name: rgw-multisite-lag
description: Investigate RGW multisite replication lag or an object missing in the other zone - metadata sync versus data sync, direction, progress. Use for "multisite lag", "sync status behind", "object not replicated", "zone out of sync", "radosgw-admin sync status".
---
# RGW multisite lag

Read-only (rule 1). Only when the cluster really runs multisite: several RGWs behind one endpoint are not multisite.
Scope: source and destination clusters and FSIDs, realm, zonegroup, zones, and the policy that should copy the affected
bucket. Sync has a direction: a healthy status for another zone, realm or bucket says nothing about this object.

When the **ceph** server is connected: `ceph_rgw_sync_status` and `ceph_rgw_daemons`.

## 1. State (in the right zone's admin context; never switch the default realm to make a command work)
```bash
radosgw-admin sync status
radosgw-admin metadata sync status
radosgw-admin data sync status --source-zone <source-zone-id>
```
Check the installed command's help and the vendor guide for explicit realm / zone parameters; the source-zone id comes
from the verified topology, never from a display name. Do not collect the full zone configuration: it can expose
system-user credentials. Record cluster, local zone, source zone, time and status together.

## 2. What it means
- **Metadata sync** (users, buckets) and **data sync** (objects) fail and progress separately.
- Take a second bounded snapshot: is the lag shrinking, growing or flat? Keep error codes and source / destination.
- Correlate with both clusters' health (`ceph-health`), destination capacity, RGW availability, network / TLS events,
  and with policy changes or upgrades at that time.
- A sync policy that excludes the bucket or the destination makes "missing" correct: confirm the expectation with the
  owner.

Library: `search_docs("multisite sync status", product="squid")`.

## Not here
Promoting a zone, committing a period, re-initialising sync, trimming logs, changing policy, replaying a write: these
move data authority. A known issue applies only when its affected / fixed versions match both sides.

## Result
Failed direction, metadata or data, impacted scope, observed progress, patch levels on both sides, next evidence. No
topology or expected policy from the owner: stop at that gap.
