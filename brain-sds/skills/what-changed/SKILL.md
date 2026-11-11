---
name: what-changed
description: What changed on the storage systems in a time window - commands run on Ceph, OneView tasks, alerts raised and resolved on StorageGRID, iLO events - to find the change behind an incident. Use for "what changed", "what happened since yesterday", "anything done before the incident", "who did what on the cluster".
---
# What changed

Read-only. Fix the window first (UTC; the user's local time beside it). Then, for the systems in scope, the record of
changes and events, newest first, side by side:

- **Ceph**: `ceph_logs which=audit` (commands run against the cluster: who, what, when), `ceph_logs which=clog
  only_warnings=true` (what the cluster reported), `ceph_daemons` (`started`: daemons restarted in the window),
  `ceph_services` (image changes), `ceph_api_get /api/cluster/upgrade/status`.
- **StorageGRID**: `sg_alert_history` (alerts raised and resolved), `sg_alerts` (still open), `sg_get grid/expansion`
  and `grid/recovery` (procedures under way).
- **OneView**: `ov_tasks` (firmware updates, profile changes, power operations: who and when), `ov_alerts state=""`.
- **iLO**: `ilo_logs log=IEL` (logins, resets, firmware updates on the iLO), `ilo_logs log=IML` (hardware events).
- **Monitoring**: Grafana annotations and the panels of the affected service, when the grafana server is connected.

Put them on one timeline (time UTC | system | what | who | source). A change just before the symptom is a lead to
test, not the cause: name the read that would confirm or rule it out. The team's incidents (`knowledge/incidents/`)
may hold the same pattern: search docs-local. File what was learned with brain-learn.
