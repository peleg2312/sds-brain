---
name: ceph-daemon-triage
description: Triage a failed or restarting cephadm daemon or container - compare what the orchestrator says with what the host shows. Use for "daemon failed", "daemon keeps restarting", "ceph orch ps shows error", "container not starting", "CEPHADM_FAILED_DAEMON", "which image is this daemon running".
---
# Cephadm daemon and container failure

Read-only (rule 1), on the cluster and on the host. Scope: cluster and FSID, then the exact service, daemon and host.
A host can hold leftovers of another cluster: never treat every local container as part of this FSID.

## 1. Orchestrator view
```bash
ceph fsid
ceph orch status
ceph orch ls --service_name=<service>
ceph orch ps --service-name <service> --daemon-id <daemon-id> --format json
```
Note the daemon's host, state, version, image and event timestamps. Use the service summary only: a full service
specification export can contain inline TLS private keys. The orchestrator's view can be stale: keep both
observation times.

## 2. Host view (on the host the orchestrator named)
Take the systemd unit and the container ID from the scoped orchestrator output, never from a guessed naming pattern.
```bash
systemctl show <unit> -p ActiveState -p SubState -p Result -p ExecMainStatus -p NRestarts
podman container inspect <container-id> --format '{{.ID}} {{.Name}} {{.Image}} {{.State.Status}}'
journalctl -u <unit> --since "<start>" --until "<end>" --no-pager -n 200
```
Always keep the `--format` on `podman container inspect`: the full output holds the container's environment and
configuration. Check the journal for credentials before pasting it.

## 3. Explanations
| Observed | Evidence to get |
|---|---|
| Process exits repeatedly | exit status, first relevant error, crash time, resource pressure |
| Image cannot start or be pulled | approved image reference / digest, registry reachability, runtime error |
| Orchestrator cannot manage the host | host identity, SSH / connectivity errors, placement events |
| Service on an unexpected host | inventory, deployment history, change record |
| Failure began during an upgrade | upgrade stage, mixed daemon versions, image, supported upgrade path |

Match image, package architecture and runtime version before treating a public issue as the same failure.

## Not here
Restart, redeploy, remove or reconfigure a daemon, pause the orchestrator, pull images, rerun a deployment.

## Result
A timeline: last healthy state, trigger, first error, latest observation. Say whether the host process is dead, the
container is missing, or only the management view reports failure; if they disagree, the disagreement is the open
question. Name other services on the same host or failure domain as possible scope without assuming they failed.
