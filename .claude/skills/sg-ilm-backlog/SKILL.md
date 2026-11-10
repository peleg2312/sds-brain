---
name: sg-ilm-backlog
description: Investigate StorageGRID ILM queues and placement - is the backlog draining, which policy and rule applies to the bucket, can copies be placed. Use for "ILM backlog", "ILM queue growing", "objects awaiting ILM", "ILM placement unachievable", "which ILM rule applies", "objects not protected yet".
---
# StorageGRID ILM queues and placement pressure

Read-only (rule 1): observe; no policy activation, ingest-behaviour change, repair or retention edit. Scope: grid,
release, sites, bucket / tenant, first symptom, a UTC window. Ask which question it is: growing evaluation backlog,
copies that cannot be placed, ingest failures, or one object's protection. Written against 11.9; open the same pages
in the installed version's product.

## Read the evidence
1. Grid Manager ILM dashboard and the grid's ILM tab, same time window: queue size, client-driven arrivals, all
   arrivals, scan rate, evaluation rate. Spikes are normal; a queue that keeps rising and does not drain is not. A
   completed scan does not prove ILM was applied to every object.
2. The bucket's **ILM policy tag -> active policy**: 11.9 supports several active policies and an untagged bucket uses
   the Default tag's policy. No resolved mapping, no placement conclusion. Then: rule order, matching object
   attributes, placement targets, copy type, retention stages.
3. Placement targets against site / node availability, capacity (`sg-capacity-metadata`) and network telemetry. A
   recent policy change, workload change, recovery or site event is a hypothesis to test against timestamps.
4. One approved sample object: intended lifecycle stage versus recorded placement (metadata / placement views; note
   version and time). No broad object scan, no payload.

Library: `search_docs("monitoring information lifecycle management", product="storagegrid-119")`, "ILM policies",
"how ILM operates throughout an object's life".

## Interpret carefully
- Consistency of metadata and placement of copies are different: StorageGRID documents how consistency settings
  interact with ILM ingest. One successful S3 response does not prove the protection an application assumes.
- Object Lock and legal hold constrain any response: expiring or removing protection is never an automatic capacity
  fix (`knowledge/notes/s3-versioning-lifecycle-retention.md`).

## Result
Queue draining, stable or growing; which placements look constrained; what is unknown. Protection that cannot be
established, or constraints that persist: tell the user to escalate. A change proposal names the affected sites and
buckets, protection before / after, validation and rollback, separately from this report.
