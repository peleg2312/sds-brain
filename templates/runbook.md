---
title: "<Verb phrase: Replace a failed OSD drive on an Apollo 4200>"
area: <ceph | rgw | s3 | storagegrid | linux | hardware | observability | objectify | general>
type: runbook
applies_to: [<product-release, e.g. rhcs-8.1z9, storagegrid-11.9, rhel-9.6, apollo-4200-gen10>]
confidence: verified
last_verified: <yyyy-mm-dd>
sources: [<title + url + version of a document, a knowledge file, a command output reference>]
---

# <the same title>

When to use: <the situation>   Impact while running: <client impact, degraded redundancy, duration>
Prerequisites: <access, maintenance window, approvals, spare parts>

Every command is run by a person. Placeholders (`<fsid>`, `<osd-id>`, `<tenant-id>`) come with the read-only command
that shows the value.

## Pre-checks
<Read-only commands and what each must show before going on (health, the right cluster: `ceph fsid`, capacity
headroom). Stop when one does not.>

## Procedure
1. <Why this step.>
   ```bash
   <command>
   ```

## Verification
<Commands that prove it worked, and what they must show.>

## Rollback
<How to undo each step, or "not reversible after step N", and what to do then.>

## Scope
<Clusters / grids, releases and hardware it was run on; where it was not tried.>

## History
- <yyyy-mm-dd>: created, run on <cluster, release> by <who> · verified
