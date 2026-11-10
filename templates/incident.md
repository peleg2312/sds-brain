---
title: "<Incident title>"
area: <ceph | rgw | s3 | storagegrid | linux | hardware | observability | objectify | general>
type: incident
applies_to: [<product-release, e.g. rhcs-8.1z9, storagegrid-11.9, rhel-9.6, apollo-4200-gen10>]
confidence: <observed | verified>
last_verified: <yyyy-mm-dd>
sources: [<title + url + version of a document, a knowledge file, a command output reference>]
clusters: [<cluster or grid names>]
severity: <sev1-sev4>
status: <open | mitigated | resolved>
---

# <the same title>

Started / detected / mitigated / resolved (UTC): <yyyy-mm-dd hh:mm> / <hh:mm> / <hh:mm> / <hh:mm>

## Impact
<Who and what was affected, for how long, user-visible symptoms, data durability at risk or not.>

## Timeline (UTC)
- <hh:mm> · <observation or action> · <who> · <evidence reference> · <result>
  <Mark suggested actions that were not executed.>

## Root cause
<The cause with a confidence word, and the alternative explanations it was weighed against. A correlated timing is
a lead, not the root cause.>

## Contributing factors

## What fixed it
<Only the changes actually made, and how they were verified.>

## What was tried and did not work

## Evidence
<Redacted request IDs, log lines, health checks, alerts, dashboard panels, document references (title + url +
version). Never keys, tokens or authorization headers.>

## Learning
<What becomes a fact line, a runbook or a change to a skill; who reviews it.>

## Action items
- [ ] <action> · <owner> · <due yyyy-mm-dd>
