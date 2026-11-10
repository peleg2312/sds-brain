---
name: ceph-slow-ops
description: Triage Ceph slow operations, stuck or degraded placement groups, recovery and backfill - tell a busy cluster from a stalled recovery or a failing device. Use for "slow ops", "slow requests", "PG stuck", "degraded", "backfill", "recovery is slow", "OSD latency".
---
# Ceph slow operations, PG recovery and backfill

Read-only (rule 1). Run `ceph-health` first and keep its verified FSID.

## 1. Locate what is affected
```bash
set -o pipefail
ceph osd tree --format json | jq -e '{nodes:(.nodes|length),sample:(.nodes[0:40]|map({id,name,type,status}))}'
ceph osd df --format json | jq -e '{nodes:(.nodes|length),sample:(.nodes[0:40]|map({id,name,status,kb,kb_used,kb_avail,utilization}))}'
ceph osd perf | sed -n '1,41p'
ceph pg stat
for s in inactive stale unclean; do
  ceph pg dump_stuck $s --format json | jq -e 'if type=="object" and (.stuck_pg_stats|type)=="array" then .stuck_pg_stats | {reported:length,sample:(.[0:20]|map({pgid,state,up,acting}))} else error("unexpected PG schema") end'
done
```
The `jq` caps limit what is shown, not the work the cluster does: on an overloaded or very large cluster use existing
telemetry and one PG already named by the health output. A schema error is an evidence gap, not "healthy". Samples
are incomplete when `reported` exceeds the cap. Take a second snapshot after an agreed interval and compare
progress: not every non-clean state is stuck.

One PG in detail: `ceph pg <pgid> query` (keep object and topology details out of notes).

## 2. Test the explanations
| Observation | Evidence to get |
|---|---|
| Affected OSDs share a host, rack or switch | host pressure (`linux-resource-pressure`), network (`linux-network-path`), hardware events (`hardware-triage`) |
| One OSD with abnormal latency | disk / controller errors, workload, verified device identity |
| Backfill blocked by capacity | fullness of the destination OSDs and the pool's placement rule |
| Recovery progresses while client latency rises | workload versus background recovery contention |
| PG cannot go active, incomplete or unfound data | exact PG state and acting set, then vendor escalation |

A slow OSD may be waiting for another OSD: the daemon that reports is not automatically the faulty device. Compare
every member the evidence implicates before anyone proposes a replacement.

## 3. Recovery versus tuning
Recovery (from PG log history) and backfill (full comparison) are different mechanisms: use the difference to read
progress, never to force one. Scheduler settings, as stored by the monitors, for one implicated OSD:
```bash
ceph config get osd.<id> osd_op_queue
ceph config get osd.<id> osd_mclock_profile
```
`config get` shows the monitor database or the default: local files, command-line options and runtime overrides can
make the running daemon differ, so do not call it the effective configuration. Read the mClock reference in the
library (product `squid`) before discussing tuning; older IBM throttle examples are not recommendations for this
fleet.

## Not here
Recovery rates, OSD flags, CRUSH weights, PG counts, full ratios, scrub settings, repair, purge, zap, benchmarks,
object deletion: reviewed changes for the user to run.

## Result
Which hypothesis the evidence supports, what would disprove it, the next safe observation. An escalation carries:
versions, PG / OSD ids, capacity and latency evidence, recent changes, and whether recovery is improving or stalled.
