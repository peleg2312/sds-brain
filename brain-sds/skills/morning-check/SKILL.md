---
name: morning-check
description: Daily health check of every storage system the brain can reach - Ceph clusters, StorageGRID grids, OneView appliances and the iLO fleet - in one table with what needs attention first. Use for "morning check", "daily check", "how is everything", "status of all clusters", "anything red today".
---
# Morning check

Read-only. Every system in the inventories, one overview call each, then one table. Systems whose server is not set
up (their only tool is `*_setup`) are listed as "not connected", not skipped silently.

## 1. Collect (independent calls together, in one turn)
- each Ceph cluster (`ceph_clusters`): `ceph_overview`
- each StorageGRID grid (`sg_grids`): `sg_overview`
- each OneView appliance (`ov_appliances`): `ov_overview`
- the iLO fleet: `ilo_fleet_health` (all servers, problems first)
Many systems: hand a domain to its analyst agent (ceph-analyst, storagegrid-analyst, hardware-analyst) with "morning
check, return the table rows only", to keep this conversation small.

## 2. Judge
- **Red**: data at risk or service down: HEALTH_ERR, PGs inactive or down, objects lost, OSDs down without noout during
  planned work, a grid node not connected, critical alerts, metadata used above 90% of allowed, a certificate expiring
  within 14 days, a failed drive or DIMM without redundancy.
- **Amber**: HEALTH_WARN, degraded PGs recovering, pools or tenants above 80%, ILM backlog growing, major alerts,
  a server not OK, NTP not locked, a profile not compliant.
- **Green**: none of the above. Thresholds the team agreed in `knowledge/notes.md` win over these.

## 3. Report
One table: system | state | the one or two facts that decide it (tool: value) | next step. Red first, then amber; greens
on one line. Then what changed since yesterday where it matters (`what-changed` skill). Offer to file a new problem as
a capture (brain-learn); never write changes, never acknowledge or silence an alert.
