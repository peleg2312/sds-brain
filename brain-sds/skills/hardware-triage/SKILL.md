---
name: hardware-triage
description: Correlate HPE server hardware evidence (iLO / Redfish health, kernel events, drive and controller state) with a Ceph or StorageGRID symptom, and map an OSD to its physical drive. Use for "disk failure", "which drive is this OSD", "iLO shows degraded", "hardware error on the host", "controller", "replace a drive", "ECC errors".
---
# HPE hardware evidence for a storage symptom

Read-only (rule 1): inventory, health and existing event records only; no Redfish Actions. Scope: cluster, host, the
exact HPE model and generation, the Ceph daemon / OSD, RHEL and kernel build, incident interval
(`knowledge/notes/hardware-hpe-identity.md`). Serials and management addresses stay out of notes.

When the **oneview** and **ilo** servers are connected: `ov_alerts`, `ov_server`, then `ilo_summary`, `ilo_logs`
(IML), `ilo_storage` (drive status, bay, predicted failure), `ilo_thermal`, `ilo_power`, `ilo_firmware`.

## Evidence, in order
1. Existing host and iLO health. System, controller, drive and NIC firmware identifiers, before choosing a support
   document for that generation.
2. Host inventory:
   ```bash
   cat /etc/redhat-release; uname -r
   lsblk -o NAME,TYPE,SIZE,MODEL
   lspci -nn
   ```
3. Kernel journal for the incident interval (`journalctl -k --since ... --until ...`): transport errors, link resets,
   ECC / machine-check events, filesystem I/O errors, device timeouts, against the storage symptom's timeline. No
   error is not proof of healthy hardware.
4. iLO: start at the Redfish service root and follow the links it returns; never assume `/Systems/1` or a fixed
   controller path across generations. With iLOrest, only the read-only inventory functions of that version, and no
   debug output (it can capture authentication).
5. **OSD -> physical bay**: needs both the Ceph / OS device evidence and the controller's inventory. They disagree or
   the mapping is unclear: stop before anyone proposes a replacement.

Library: `search_docs("...", vendor="hpe")` (iLOrest, Redfish concepts and services).

## Hypotheses to keep apart
Drive / media failure, transport or backplane error, controller / cache behaviour, network retransmissions, memory
errors, thermal or power limits, and recovery load can all look like "slow". One hot OSD versus every OSD on a host
point to different next checks, not to a root cause.

## Escalate (tell the user) when
Risk of data loss, a device that keeps disappearing, uncorrected memory errors, power or thermal alarms, or a device
that cannot be mapped safely. Support packet: model / generation, firmware, affected components, bounded events,
cluster state. AHS / IML and support bundles are reviewed before they leave.

## Not here
Drive self-tests, destructive diagnostics, firmware updates, controller reconfiguration, power cycling, OSD
replacement: a maintenance plan with a recovery impact assessment, run by the user.
