---
name: sg-tenant-quota
description: Reconcile tenant quota and usage between Objectify, StorageGRID Tenant Manager and monitoring, or explain a quota rejection. Use for "tenant quota", "account full", "quota exceeded", "usage in Objectify does not match the grid", "how much is this tenant using".
---
# Objectify and StorageGRID tenant quota

Read-only (rule 1): no Objectify resize, recount, regenerate, modify or decommission call; a GET is not safe just
because it is a GET. Scope: Objectify account, grid, tenant ID, release, UTC observation time. Map the account to the
tenant from a verified source: similar names are not a mapping.

## Compare
1. **Objectify** (the `objectify` connection when its reads are enabled, else what the user pastes with keys
   removed): backend kind, tenant mapping, quota / usage and their units, update time.
2. **StorageGRID**: the tenant in Tenant Manager or its Tenant API read operation (take the operation from the
   installed Swagger, never from an old example). A tenant account is not one of its users or keys.
3. **Like with like**: StorageGRID quota usage is logical object data, without copies and metadata. It is an estimate
   and its refresh can take ten minutes or more: a delete followed at once by a re-ingest can still be rejected.
4. **Quota or something else?** Keep the provider error, HTTP status, time and operation. "Account full" from an
   application is not evidence: get the underlying response (`s3-access-denied` for a 403).

Quota is not the only limit: for bucket creation or listing failures check the release's bucket limits and the
tenant's bucket count.

Library: `search_docs("tenant manager dashboard quota", product="storagegrid-119")`; background:
`knowledge/notes/storagegrid-capacity-quota-ilm.md`.

## Result
A table: source, identity mapping, metric definition, units, sample time, value. Each difference classified:
unresolved mapping, different units or definition, stale observation, or a real quota condition. Then the smallest
missing read, or a change proposal for the user.
