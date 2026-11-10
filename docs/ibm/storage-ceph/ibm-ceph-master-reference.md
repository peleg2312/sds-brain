# IBM Storage Ceph Master Troubleshooting and Operations Reference Guide

This is a landing page or contents index. Linked documents are not part of this individual snapshot.

IBM Support

# IBM Storage Ceph – Master Troubleshooting and Operations Reference Guide

### How To

## Summary

This guide consolidates key IBM Storage Ceph troubleshooting information, operational guidance, and references to high-value documentation used by administrators.

## Objective

- Provide recommended operational practices for IBM Storage Ceph clusters.

- Highlight common issues encountered during day-2 operations and link to their solutions.

## Environment

- IBM Storage Ceph 5.x and above

## Steps

* This article compiles IBM-recommended resources, validated guidance, and troubleshooting references to support administrators in operating and maintaining IBM Storage Ceph clusters.

IBM Storage Ceph Versions & Release Mappings

- Reference: IBM Storage Ceph release and package version matrix

Official Documentation

- IBM Storage Ceph Official Documentation

- Refer to the IBM Storage Ceph Supported Configurations for supported configurations

- Refer to the IBM Storage Ceph Hardware guide documentation for hardware configurations.

- Use the IBM Storage Ceph Strategies Guide for capacity and deployment planning

- Refer to the IBM Redbook for hardware and deployment plannng for RBD services. There is a wealth of general IBM Storage Ceph information here as well.

Frequently Used Knowledge Articles

Upgrade

- How to edit a CRUSH map and upload it back to the cluster?

- The CRUSH map reverted after a node reboot! Why?

- Some IBM Storage Ceph container images are pointing to the Red Hat registry instead of the IBM registry

RADOS

- IBM Storage Ceph RADOS: How to modify the failure domain for an existing pool?

- How to map a pool to a dedicated set of OSDs?

- BlueStore values for bluestore_min_alloc_size_hdd and bluestore_min_alloc_size_ssd change

- Ceph Scrubbing And Its Parameters

- What are the differences between backfill and recovery and what is peering?

Monitors (MONs)

- How to download, edit, and upload a Monitor map in a Ceph cluster?

- When does an election happen for a Ceph monitor?

- How to handle an IP address change of a Monitor in a Ceph cluster?

- Ceph: Monitor service crashes with "/src/mon/PaxosService.cc: 193: FAILED ceph_assert(have_pending)"

Managers (MGRs)

- Ceph - How to update the IP address or Port of the Ceph-dashboard

- Ceph health reports stray daemon(s)

Cephadm

- A Ceph Manager reports: mgr set_store mon returned -27: error: entry size limited to 65536 bytes

OSD

- What does OMAP and META in 'ceph osd df' output means?

- Ceph OSD weights and related configurations

- Ceph: Managing backfill, recovery, and rebalancing throttles

- Ceph - Cluster is 'FULL' how to fix it?

- Why does an Ceph cluster report the status of "HEALTH_WARN x near full osd(s)"?

- What are various full and near full ratios in Ceph?

- The distribution of data among OSDs is uneven, Why?

Placement Groups (PG)

- Red Hat Access Labs - Placement Group calculator

- What are the possible Placement Group states in an IBM Storage Ceph Cluster

- Ceph: How do I increase Placement Group (PG) count in a Ceph Cluster

- IBM Storage Ceph: How to handle Inconsistent Placement Groups?

- Ceph: HEALTH_WARN message "pool <pool> has too few pgs"

- # Ceph: HEALTH_WARN message "too many PGs per OSD"

RADOS Block Device (RBD)

- How to check RBD images are used by which clients ?

Rados Gateway (RGW)

- How multi-part upload(MPU) works in Ceph RGW?

- Ceph- Health shows warning "x large omap objects" in the rgw.meta pool

- IBM Storage Ceph: RGW and Ceph-exporter do not resume log activity after log rotation

- Python boto code for using S3 APIs with Ceph RadosGW

- How to deal with large omap object warning in various pools?

CephFS

- Ceph status in HEALTH_ERR with MDSs reporting damaged metadata

Erasure Coded pools

- An erasure coded pool with "4+2" chunks created on a ruleset with four OSD nodes, ends up moving the cluster status to HEALTH_WARN, why?

- What are the best practices for Erasure coded pools in IBM Storage Ceph?

Performance issues

- What are the performance benchmarking tools available for IBM Storage Ceph?

Nvme-Of

- IBM Storage Ceph NvmeoF Gateway discovery fails in multiple subsystem scenario, when a client NQN is added to one of subsytem's "host list" only

- IBM ceph upgrade from 7.1 to 7.1.z1 fails when the NVMeOF service is in use

Generic

- What information should be collected while debugging/opening a IBM Storage case?

- How to map an object to its respective Placement Groups and OSD disks, in IBM Storage Ceph?

Others

- Graceful cluster expansion and CRUSH changes

- NTP Strategies for time synchronization

## Document Location

Worldwide

[{"Type":"MASTER","Line of Business":{"code":"LOB69","label":"Storage TPS"},"Business Unit":{"code":"BU048","label":"IBM Software"},"Product":{"code":"SSEG27","label":"IBM Storage Ceph"},"ARM Category":[{"code":"a8m3p000000UoIPAA0","label":"Support Reference Guide"}],"ARM Case Number":"","Platform":[{"code":"PF025","label":"Platform Independent"}],"Version":"5.3.0;6.1.0;7.0.0;7.1.0;8.0.0;8.1.0;9.0.0"}]

## Was this topic helpful?

### Document Information

Modified date:

09 December 2025

## UID

ibm17239015

Page Feedback
