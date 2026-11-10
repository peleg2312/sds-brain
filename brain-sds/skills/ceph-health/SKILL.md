---
name: ceph-health
description: First look at a Ceph cluster warning - collect the health baseline, list the exact health checks and route to the right follow-up. Use for "HEALTH_WARN", "HEALTH_ERR", "ceph health", "cluster warning", "what is wrong with the cluster", any Ceph health check name.
---
# Ceph health baseline

Read-only (rule 1). Scope first: which cluster (`knowledge/environment.md`), its RHCS release, when the impact began (UTC)
and which client operations fail. Check that `ceph fsid` is the cluster asked about before going on. Admin-socket and
other version-sensitive commands differ between Reef and Squid: check the command's help or the release's
documentation before suggesting one. Short bounded samples, not repeated full PG / OSD dumps.

## 1. Snapshot (admin host of that cluster)
```bash
ceph fsid
ceph -s --format json
ceph health detail --format json
ceph versions
ceph quorum_status --format json
ceph osd stat
ceph pg stat
ceph df --format json
```
Compare the FSID with `environment.md` before reading anything else: a mismatch or no monitor answer is a stop, never a
reason to try another cluster's configuration. If the cluster is overloaded, prefer existing Grafana data to more
commands; no continuous polling.

## 2. Triage the health checks
List every check name with its affected daemons or PGs, and search each in the library
(`search_docs("<CHECK_NAME>", product="squid")` for RHCS 8.1, `"reef"` for 7.1). Overall severity is not client
impact: note both.

| Evidence | Go to |
|---|---|
| Monitor down, clock skew, command timeout | quorum / time / network first (skill `linux-network-path`), before any OSD analysis |
| OSD down, slow requests, recovery or backfill warnings | skill `ceph-slow-ops` |
| PG inconsistent, incomplete, unfound objects | keep the PG / OSD evidence, escalate to the storage owner and the vendor |
| RGW failures while RADOS is healthy | skill `rgw-request-triage` |
| Failed cephadm daemon | skill `ceph-daemon-triage` |
| Capacity checks (nearfull, backfillfull, full) | per-OSD and per-pool capacity before proposing anything |

## 3. Make it an investigation
Ask what changed before the impact (maintenance, upgrade, workload). Compare with a recent healthy interval of the same
cluster. When metrics, logs and CLI disagree, report the disagreement.

A warning can vanish because the condition cleared, because monitoring lost sight of it, or because someone muted it:
say which.

## Not here
Muting a warning, archiving a crash, changing full ratios, marking OSDs out, repair or recovery actions: the user's to
run, as a reviewed change (rule 1).

## Result
Cluster and FSID, health checks, affected services, client impact, a UTC timeline, and the next diagnostic question.
Cause stays "unknown" without independent evidence. Quorum lost, data possibly inaccessible or redundancy badly
reduced: tell the user to involve the storage owner now and keep the original outputs.
