---
name: linux-resource-pressure
description: Triage CPU, memory or disk latency pressure on a RHEL storage host (OSD or RGW node) with a short read-only sample. Use for "host is slow", "high load", "OOM", "memory pressure", "iowait", "disk latency on the host", "which process is using the CPU".
---
# RHEL CPU, memory and storage latency

Read-only (rule 1): a short evidence sample, not a benchmark or tuning. Scope: cluster, host, incident interval, the
affected service (which RGW / OSD). Start with the existing Grafana data for the failing interval: a command now
shows pressure now, not a past spike. Use PCP / sysstat history if it already exists; do not enable a recorder.

## Sample (on that host)
```bash
cat /etc/redhat-release; uname -r
rpm -q kernel-core podman procps-ng sysstat
uptime; free -h
vmstat 1 5
iostat -xz 1 5
lsblk -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS,MODEL
ps -p <pids-of-the-service> -o pid,ppid,comm,%cpu,%mem --sort=-%cpu | sed -n '1,21p'
journalctl -k --since "<start>" --until "<end>" --no-pager -n 200
```
The first `vmstat` / `iostat` row is the average since boot: read the interval rows. A missing package is an
evidence gap, not a reason to install it. The `ps` line has no arguments or environment on purpose. The kernel
journal can hold device identifiers: keep it out of shared notes.

## Read several signals together
| Hypothesis | Evidence needed |
|---|---|
| CPU contention | busy cores / run queue in the failing interval, and the implicated service's workload |
| Memory pressure | available memory, reclaim / swap, process and cgroup limits, kernel events |
| Block-device bottleneck | per-device latency and queue, correlated with the service delay |
| Hardware / device errors | kernel and controller events, with a verified device-to-OSD mapping (`hardware-triage`) |
| Container limit | the service's cgroup versus host-wide numbers |

A busy-device percentage, a high load average or low free memory alone names no cause: compare with a healthy
interval on this host and with a peer of the same role and hardware. Keep the full kernel build with any suspected
kernel issue (`knowledge/notes/linux-host-diagnostics.md`).

## Not here
Dropping caches, killing processes, filesystem repair, SMART tests, cgroup or kernel tuning, generating I/O load.

## Result
The constrained layer, the evidence, the uncertainty, the next diagnostic. A remediation proposal accounts for the
other services and OSDs on the host.
