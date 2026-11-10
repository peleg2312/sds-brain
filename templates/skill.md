---
name: <folder-name, e.g. rgw-bucket-index-triage>
description: <What it investigates and when to use it, with the words people type: health check names, error codes, symptoms. 1024 characters at most.>
---
# <Investigation title>

<!-- A new investigation procedure for brain-sds/skills/<name>/SKILL.md (from the first SDS brain's runbook template).
     Every command is a READ; changes go to knowledge/runbooks/ once a person has run and confirmed them. -->

Read-only (rule 1). Scope first: which cluster or grid (`knowledge/environment.md`), its exact release, the symptom,
the incident window in UTC, and the access the user has. Check the identity in the first output (`ceph fsid`, grid
name) before going on.

## 1. Bounded evidence
<Each read-only check: the command, what its output shows, its cost (time, size), the sensitive fields to leave out
(`jq` projection). Label commands as proposed until the user ran them.>
```bash
<read-only command>
```

## 2. Decision points
<For each hypothesis: the evidence that supports it, the evidence that weakens it, the one check that tells them
apart. Correlation is not a root cause.>

## 3. Escalation and exit
<When to stop, what to send to the owner or to Red Hat / NetApp / HPE support, how to know the investigation is
complete. Proposed changes are listed apart from the diagnosis, as steps for the user to run.>

## Sources
<Library documents (title + url + version) and knowledge files this procedure rests on; who reviewed it and when.>
