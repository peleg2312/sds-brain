---
name: es-request-correlation
description: Find and correlate S3 request events in Elasticsearch (through Grafana or a pasted query result) by request ID, time and error, with a bounded query. Use for "find this request ID in Elasticsearch", "search the logs for the failed request", "correlate S3 errors in ES", "Kibana / Elasticsearch query for RGW or StorageGRID logs".
---
# Correlate S3 request failures in Elasticsearch

Read-only (rule 1). First the data contract (`knowledge/environment.md`, else ask): does the index hold gateway /
application events for this cluster at all? Index or alias, timestamp field, cluster field, request-ID field, status
field, duration units. Having Elasticsearch does not make it the log platform, and it may be StorageGRID's
metadata feed instead (`knowledge/notes/storagegrid-capacity-quota-ilm.md`). Start from a request ID the user knows.

## Investigation
1. Datasource and index alias from the environment. Never `_all`, a global wildcard or a catch-all alias. Narrow UTC
   interval.
2. Reuse the working dashboard query, or the template below. Ask only for the fields needed, small result size, no
   full hit counting; note partial results and timeouts.
3. Filter on the exact request ID; without one: cluster, time and the observed error. A short ID may not be unique.
4. Match gateway events with the client's request time and the backend's state. Retries create different request IDs:
   keep them apart.
5. No hits: check the index, the time mapping and ingestion delay before widening. Never search every index to make
   up for a missing mapping.

## Query template (replace every UPPERCASE name with a field verified in the mapping)
```json
{
  "size": 20, "timeout": "5s", "track_total_hits": false,
  "_source": ["TIMESTAMP_FIELD", "REQUEST_ID_FIELD", "STATUS_FIELD"],
  "query": {"bool": {"filter": [
    {"term": {"CLUSTER_FIELD": "CLUSTER"}},
    {"term": {"REQUEST_ID_FIELD": "REQUEST_ID"}},
    {"range": {"TIMESTAMP_FIELD": {"gte": "START_UTC", "lte": "END_UTC"}}}
  ]}}
}
```
Use keyword (exact-match) fields for `term`. Leave raw messages and whole `_source` payloads out unless checked for
credentials and personal data (rule 4).

## Search platform is not the storage service
An unhealthy Elasticsearch explains missing evidence; it does not prove a Ceph or StorageGRID failure.

## Result
Query and index, time window, field map, returned count, timeout / partial flags, a few redacted request events and
how they relate to backend observations. Fields missing: report the schema gap and use the product's own evidence
(`rgw-request-triage`, StorageGRID logs). A field map you established goes to `knowledge/notes/observability.md`.
