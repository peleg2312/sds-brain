---
name: linux-selinux-denial
description: Check whether an SELinux denial explains an access failure of a service or container on a RHEL host, from existing audit events. Use for "SELinux", "AVC denied", "permission denied but file permissions look right", "avc:", "setroubleshoot".
---
# RHEL SELinux denial

Read-only (rule 1). Scope: cluster, host, the operation and its UTC time, the service / container. A permission error
alone does not prove SELinux. Use the events of the real failure; do not repeat an application write just to provoke
a denial.

## Existing evidence (on that host; `<pid>` is the process seen at the incident time)
```bash
set -o pipefail
getenforce; sestatus
systemctl is-active auditd
ausearch -m AVC,USER_AVC,SELINUX_ERR,USER_SELINUX_ERR -p <pid> -ts recent -i | sed -n '1,120p'
journalctl -t setroubleshoot --since "<start>" --until "<end>" --no-pager -n 100
ls -Zd -- <path>
ps -p <pid> -o pid,comm,label
matchpathcon -V <path>
```
`-ts recent` is relative to now: for an older failure give an explicit start / end. The 120-line cap can split an
event, and an empty sample does not prove there was no denial. Audit records can hold process arguments: read them
locally, pass on only the fields below. A PID can be reused: match timestamps. One path and one PID from the
incident, never a recursive search.

## Interpret
Record the denied permission, source context, target context, object class and path. Compare the observed label with
the label the policy expects. Also weigh ordinary file permissions, ownership, mount options and application
configuration: Red Hat's guidance is to check labelling and configuration before any local policy exception. For a
container, find the host path and security context behind it.

## Three possible reports
1. A relevant denial was found. 2. A denial was found but its link to the incident is uncertain. 3. The available
logs do not establish a denial (say what time range they cover and what is missing).
A proposed fix names the label, boolean, application setting or policy behaviour and why; it stays a proposal.

## Not here
`setenforce`, disabling dontaudit, relabelling, generating or installing an allow module, changing booleans,
restarting services. These are changes even when a vendor troubleshooting page shows them.
