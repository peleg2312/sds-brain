# Managing backfill, recovery and rebalancing throttles

IBM Support

# Ceph: Managing backfill, recovery, and rebalancing throttles

### How To

## Summary

This article explains how to adjust backfill and recovery to balance time to complete against impact on the cluster according to your local needs.

## Objective

When adding, removing, or replacing OSDs in an IBM Storage Ceph Cluster, the CRUSH algorithm will balance the cluster by moving or replicating placement groups (PGs) to or from OSDs to restore desired redundancy and uniform distribution of data. These activities are backfill and recovery, which can impact client performance. To maintain operational performance, IBM Storage Ceph backfill operations are set to a lower priority than client read and write requests. To further reduce the impact to client operations, there are some tuning parameters that can be applied.

IBM Storage Ceph clusters populated with rotational HDDs that serve a heavy workload often chose to reduce the impact of backfill and recovery by throttling via central configuration options. Clusters populated with SSDs (SATA, SAS, or NVMe) or with clients migrating data in a maintenance window might choose to easy throttling to facilitate faster completion.

## Environment

- IBM Storage Ceph 5.x and above

## Steps

- Decreasing Backfilling (Throttling down)

Update these central configuration database options to their lowest possible values:

```
# ceph config set osd osd_max_backfills 1
# ceph config set osd osd_recovery_max_active 1
# ceph config set osd osd_recovery_op_priority 1
```

Verify the configuration settings using the following command:

```
# ceph config dump | grep osd
  osd      advanced osd_max_backfills                    1
  osd      advanced osd_recovery_max_active              1
  osd      advanced osd_recovery_op_priority             1
```

You may also consider setting osd_scrub_during_recovery to false, though with recent releases this has limited benefit and may lead to warnings about scrubs not completing in time.

Here's what each option means

```
osd_max_backfills
The maximum number of backfills allowed to or from a single OSD. Note that this is applied separately for read and write operations.

osd_recovery_max_active
The number of active recovery requests per OSD at one time. More requests will accelerate recovery, but the requests places an increased load on the cluster.

osd_recovery_op_priority
The priority of recovery operations vs client operations, if not specified by the pool’s recovery_op_priority. The default value prioritizes client ops (see above) over recovery ops. You may adjust the tradeoff of client impact against the time to restore cluster health by lowering this value for increased prioritization of client ops, or by increasing it to favor recovery.
```

- Increasing Backfilling (Throttling up)

IBM Storage Ceph clusters populated with SSD OSDs or with customers migrating data in a maintenance window might chose to increase these values to complete backfill and recovery more quickly, at the potential expense of slower client operations. There are three ways to expedite backfill and recovery. This list is in order by most impactful to least impactful

- Ensure SSDs are seen as such, not as rotational HDDs.

- Increase backfill and recovery parameters

- Disable scrubbing and deep scrubbing, addition by subtraction

Ensure solid state SSD OSDs are seen as such, not as rotational HDDs:  Follow KCS #3937321, SSD device detected as rotational (HDD). If KCS #3937321 applies to your Ceph Cluster, resolving this issue will give the biggest performance increase for backfill and recovery.

Addition by subtraction: By disabling scrubs, more I/O resources are available for backfill and recovery, allowing faster progress. We describe this for completeness, though the benefit is limited and in most cases scrubbing during recovery is best left enabled.

Note: Scrubbing and Deep Scrubbing should never be disabled for more than a week.

Disable Scrubbing and Deep Scrubbing:

```
# ceph osd set nodeep-scrub
nodeep-scrub is set
# ceph osd set noscrub
noscrub is set

```

Enable Scrubbing and Deep Scrubbing:

```
# ceph osd unset nodeep-scrub
nodeep-scrub is unset
# ceph osd unset noscrub
noscrub is unset
```

For signficant backfill performance increase, the below options can be adjusted. Very high values these parameters are aggressive and should be increased only if the IBM Storage Ceph Cluster is not in production or is in a maintenance window.

Values higher than the 2x increase values shown below are not recommended for HDD clusters systems unless used for a migration during a maintenance window.  Even in those situations higher values may actually slow progress by increasing rotational and seek latency.

Update the cluster's central configuration database:

```
**** 2x Increase  ****
# ceph config set osd osd_max_backfills 2
# ceph config set osd osd_recovery_max_active 8

**** 3x Increase  ****
# ceph config set osd osd_max_backfills 3
# ceph config set osd osd_recovery_max_active 12

**** 4x Increase  ****
# ceph config set osd osd_max_backfills 4
# ceph config set osd osd_recovery_max_active 16

**** Back to Defaults  ****
# ceph config set osd osd_max_backfills 1
# ceph config set osd osd_recovery_max_active 3
```

Verify the configuration settings using the following command:

```
# ceph config dump | grep osd

```

## Additional Information

Note that when running IBM Storage Ceph 7 or later the mclock scheduler is by default enabled.  This means that the above three config options will not take effect unless you revert to the wpq scheduler with the below commands:

ceph config set osd osd_op_queue wpq

ceph config set osd_mclock_override_recovery_settings true

When the default mclock scheduler is enabled, the tradeoff between clients and recovery/backfill is controlled via other settings as described in the documentation.

## Document Location

Worldwide

[{"Type":"MASTER","Line of Business":{"code":"LOB69","label":"Storage TPS"},"Business Unit":{"code":"BU048","label":"IBM Software"},"Product":{"code":"SSEG27","label":"IBM Storage Ceph"},"ARM Category":[{"code":"a8m3p000000UoIPAA0","label":"Support Reference Guide"}],"ARM Case Number":"","Platform":[{"code":"PF025","label":"Platform Independent"}],"Version":"All Versions"}]

## Was this topic helpful?

### Document Information

Modified date:

10 September 2025

## UID

ibm16963280

Page Feedback
