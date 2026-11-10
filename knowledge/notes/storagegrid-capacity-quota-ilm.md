# StorageGRID: capacity, tenant usage and ILM are different measurements

| Measurement | Question it answers | Mistake to avoid |
|---|---|---|
| Tenant logical usage / quota | How much object data is attributed to this tenant? | Reading it as the physical cost of all protected copies |
| Physical object-data space | Which nodes / sites can accept protected object data? | Assuming grid-wide free space makes every placement possible |
| Allowed metadata space | How much room is left for metadata under the supported limit? | Counting all filesystem free space as usable for metadata |
| ILM work and placement | Is the grid evaluating and meeting the required placement? | Equating a finished scan with finished protection |

- Object data and metadata are stored and reported separately. Keep the node / site dimension; an aggregate
  dashboard hides the constrained site (monitor/monitoring-storage-capacity).
- Metadata has an allowed allocation plus space reserved for database work. Going over the allowed amount is not a
  cosmetic alarm (troubleshoot/troubleshooting-metadata-issues).
- ILM rules describe protection and placement over time. First resolve the bucket's policy tag to its active policy:
  11.9 can have several active policies, and untagged buckets use the Default tag's policy (ilm/ilm-policy-overview).
  Policy design and observed placement are two things.
- Tenant quota usage is an estimate of logical object data; it excludes copies and metadata. Note the calculation
  time when comparing Objectify, Tenant Manager and monitoring values (tenant/understanding-tenant-manager-dashboard).
- Object Lock can keep versions from being deleted even when capacity is tight. Collect retention and legal-hold
  status; never remove protection.

## Elasticsearch is not the object inventory
StorageGRID's search integration exports object metadata asynchronously, so an index can lag behind object
operations. Whether the team's Elasticsearch receives this feed, operational logs or something else is recorded in
`environment.md`: check before using a count or a search miss as evidence of object loss
(tenant/understanding-search-integration-service).

Pages above are in the library under netapp/storagegrid-119 (same paths in -118 and -120: use the installed version).
