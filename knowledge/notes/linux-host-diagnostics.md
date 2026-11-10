# RHEL hosts: reading host and container evidence

## Inventory first
Record the host release, the full running kernel version, the container runtime version, the server model and
firmware separately. Red Hat backports fixes: an upstream-looking kernel version does not tell whether a fix is
present; use the full package build and the erratum.

A container shares the host kernel. A process limit or memory failure can come from the service's cgroup and runtime
configuration: match a process to its daemon, container, systemd unit and host before reading host-wide metrics.

## Every observation carries
Cluster, host, UTC interval, tool and version, unit. Say whether a value is a sample or a cumulative counter, and
whether it was taken during the failing interval or after recovery: a healthy snapshot now does not disprove an
earlier incident.

- **CPU, memory, I/O**: start with the existing Grafana / exporter data and a short bounded host sample. No
  benchmark, persistent recorder or heavy trace in a first read-only diagnosis.
- **Block errors**: keep a verified mapping OSD -> device path -> WWN / serial -> enclosure slot. Device names
  change; use persistent identifiers. A device Linux sees is not automatically the disk to replace.

## Read-only also means careful with what is shown
Diagnostic output can contain names, paths, addresses or secrets: use focused fields and bounded log intervals; no
full process environments, container configurations or unit files in notes. Root is not needed for every check and
is not permission to change settings. A command that is missing is reported as unavailable: never install its
package or swap in another tool silently.

Package installation, kernel or firmware changes, network reconfiguration, service restarts, storage repair,
debug-level changes and load generation are changes: the user runs them (rule 1).

Sources (docs.redhat.com, RHEL 9): Managing, monitoring and updating the kernel; Building, running and managing
containers; Monitoring and managing system status and performance; Managing storage devices. Add them under
`docs/redhat/rhel-9/` to make them searchable.
