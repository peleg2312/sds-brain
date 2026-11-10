# Ceph RGW: which evidence for which symptom

An incident is evidence from several connected layers: client request, endpoint / load balancer, RGW daemon, RADOS
pool and placement group, OSD, host, hardware. A symptom at one layer does not name the cause.

| Symptom | First evidence | Then |
|---|---|---|
| Cluster health warning | Exact health check names, FSID, time, client impact | skill `ceph-health`, then the OSD / PG or daemon skill |
| S3 403 or signature error | Operation, request ID, endpoint, timestamp, identity | skills `s3-access-denied`, `s3-signature-tls` |
| S3 latency up | Latency by operation and by RGW, error rate, workload change | RADOS health, OSD / host pressure, network path |
| Object missing at another site | Source and destination zone, expected sync policy | skill `rgw-multisite-lag`; metadata sync and data sync are separate |
| Failed daemon | Orchestrator state and service events | skill `ceph-daemon-triage` |

## Identities
- A **CephX** identity authorizes cluster operations. An **RGW S3 user** is a separate object-storage identity.
- "Account" has product meanings: here an Objectify account is an RGW user (Ceph) or a tenant (StorageGRID). Do not
  apply the newer upstream RGW "account" feature to it.
- The RGW admin interface returns key material when a user is inspected. Use a projection that leaves the keys out,
  and never store raw credentials in a note.

## S3 compatibility
Ceph documents its S3 feature support per release. Test the actual operation against the installed release and
patch level; record endpoint, region, addressing style, SDK version and options with any compatibility report. AWS
behaviour alone does not prove what RHCS supports.

## Scope
The team's Ceph use is RGW. RBD and CephFS pages in the library are background only.

Sources: IBM Storage Ceph Concepts and Architecture Guide (REDP-5721, in the library: ibm/storage-ceph); Red Hat Ceph
Storage 8 Object Gateway Guide; https://docs.ceph.com/en/squid/radosgw/admin/ ; https://docs.ceph.com/en/squid/radosgw/s3/
