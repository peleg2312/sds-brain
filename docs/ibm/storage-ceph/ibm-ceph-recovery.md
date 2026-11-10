# Differences between backfill, recovery and peering

IBM Support

# IBM Storage Ceph - What are the differences between backfill and recovery? What is peering?

### Troubleshooting

## Problem

- Ceph - What are the differences between backfill and recovery? What is peering?

## Environment

- IBM Ceph Storage 5 and above

## Resolving The Problem

Within Ceph, there are two methods of synchronizing data among OSDs within the cluster, recovery and backfill.  While both of these methods achieve the same end goal, there are slight differences in these two processes as outlined below.

- When is Recovery used instead of Backfill?

- Ceph OSD processes maintain a log per Placement Group ( PG ) called the pglog, which includes details on the last 3,000 to 10,000 changes to that PG.

- The number of log entries to maintain is adjustable via the osd_min_pg_log_entries and osd_max_pg_log_entries central config options.

- The max entry is the number of entries to keep when the PG is not active+clean.

- The min entry is the number of entries to keep when the PG is active+clean.

- If:

- An OSD was down but is now up

- And there are available but unapplied pglog updates for a given PG replica on this OSD

- Then:

- recovery is used for that PG.

- Else:

- backfill is used for that PG.

- Ok, what's the difference?

| recovery | backfill

Data Copied | Only new or changed objects | Only new or changed objects

Data Selection | pglog comparison (FAST) | Per object comparision (SLOW)

Access Blocked | Yes , access to unrecovered objects is blocked | No , client IO is serviced on all objects

- Why is access blocked during recovery, but not during backfill?

- This is a historical quirk from early choices made in the design of Ceph's data synchronization processes.

- In recent releases recovery no longer blocks RADOS object IO (async recovery).

- For details on the async recovery change, please see:

- Minimize log-based recovery in the acting set

- Implement asynchronous recovery in Ceph

- Can I force backfill instead of recovery so I don't ever block client IO?

- Yes!

- To accomplish this, adjust the min and max log options:

```
# the number of entries to keep in the pg log when trimming it. Defaults to 3000.
osd_min_pg_log_entries = 1

# the max entries, say when degraded, before we trim. Defaults to 10000.
osd_max_pg_log_entries = 2
```

- Important! We strongly recommend testing of these options in a test environment before implementing in production so that you can get an idea how they are going to behave. In most cases recovery proceeds more expeditiously than backfill, but there are exceptions.  For example, if OSDs due to bugs or mismanagement have grown extremely large omaps or other metadata, backfill may be faster.  Please contact IBM support before disabling recovery.

- Got it, now what is peering?

- peering is the process by which OSDs compare PG states to determine the proper current state of a PG.

- peering also makes note of which OSDs have the most recent data and metadata for various RADOS objects within the PG.

- peering occurs when an OSD is brought up (either a new OSD, or a previously down OSD) or down.

- Client access is blocked for the entire PG while peering is ongoing

- This prevents changes requested by client IO from invalidating the peering process

- Peering is very fast, so this rarely presents significant client impact

- Once peering is complete, the PG will enter either the backfill_wait or recovery_wait state.

- The PG should move from the wait state to backfilling or recovering as slots for these operations become available on the target OSD.

- Note: Agreeing on the state does not mean that they all have the latest contents.  This is what backfill and recovery accomplish.

- Can these processes lead to slow request log entries?

- If you monitor or review the cluster or Monitor logs, you may see slow request or blocked request entries.

- The tail end of the slow request message will indicate which type of operation is blocking that request.

- Type waiting on peering means that IO is blocked while a PG is peering.

- Type waiting on degraded objects it means that IO is blocked to those RADOS objects which are waiting for or are in active recovery.

- Can I prevent backfill or recovery from happening?

- Yes!

- To do this, we have nobackfill and norecover flags.

```
# ceph osd set nobackfill
# ceph osd set norecover
```

- When your maintenance is complete,  re-enable backfill and recovery by unsetting the flags:

```
# ceph osd unset nobackfill
# ceph osd unset norecover
```

- More details on these and other Ceph flags are available in the 'Administration Guide' for Red Hat Ceph Storage:

- Setting and Unsetting Overrides

Also review this article which describes a strategy for deferring and managing backfill to mitigate thundering herds when conducting large CRUSH topology changes including cluster expansion.

- OK, but what about the norebalance flag?

- This flag is more selective than nobackfill or norecover.

- Specifically, this flag will prevent data movement as long as a PG is remapped but not degraded

- What is the difference between remapped and degraded?

- The remapped PG state indicates that the PG has at least one copy of data in a non-optimal location.

- The degraded PG state indicates that the PG is missing at least one replica or shard of data.

- More data on PG states is available in the Administration Guide for IBM Storage Ceph:

## Document Location

Worldwide

[{"Type":"MASTER","Line of Business":{"code":"LOB69","label":"Storage TPS"},"Business Unit":{"code":"BU048","label":"IBM Software"},"Product":{"code":"SSEG27","label":"IBM Storage Ceph"},"ARM Category":[{"code":"a8m3p000000UoIPAA0","label":"Support Reference Guide"}],"ARM Case Number":"","Platform":[{"code":"PF025","label":"Platform Independent"}],"Version":"All Versions"}]

## Was this topic helpful?

### Document Information

Modified date:

10 September 2025

## UID

ibm17176025

Page Feedback
