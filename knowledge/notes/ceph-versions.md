# Ceph and RHEL versions: what to record and which documentation to use

## Release families
| Reported | What the vendor documents | Rule |
|---|---|---|
| RHCS 7.1z7 | In the 7.1 release notes; a container-only update | 7.1 documentation plus its errata; verify the running image |
| RHCS 8.1z3, z6, z7, z8, z9 | All in the 8.1 release notes | A fix or feature arrives at a z-stream: keep each patch as its own value |
| RHEL 9.6, 9.8 | Release notes exist for both; the RHCS 8.1 compatibility matrix lists them | Record release RPM, running kernel, architecture per host |

RHCS 7.1 corresponds to upstream **Reef**, 8.1 to **Squid** (IBM's release / package matrix, in the library). One
z-stream can have several image rebuilds. IBM and Red Hat registries and support policies differ: never derive a
Red Hat image digest from an IBM tag.

## Three different facts per cluster
Vendor release (8.1z9), daemon-reported version, and container image reference + digest. Daemons are not always
upgraded together. An image tag can move; the digest the runtime reports is the evidence.

Read-only, on the cluster's admin host (compare the FSID with `environment.md` before reading anything else):
```bash
ceph fsid
ceph versions
cat /etc/redhat-release
uname -r
rpm -q redhat-release kernel-core podman
```
The host commands describe that host only. For one daemon's image: skill `ceph-daemon-triage`.

## Which document wins
1. The installed vendor's release notes for the exact release, the support matrix, the applicable advisory.
2. The vendor guide for procedures.
3. The pinned upstream family (Reef / Squid) to explain how something works.
Keep conflicts visible. A matching error string or a newer upstream patch does not prove an upgrade is the remedy:
it is a hypothesis until its conditions match this deployment.

Sources: RHCS 7.1 and 8.1 Release Notes, RHCS 8.1 Compatibility Matrix, RHEL 9.6 / 9.8 Release Notes (docs.redhat.com);
IBM "Red Hat and IBM Storage Ceph releases and corresponding Ceph package versions" (library: ibm/storage-ceph).
