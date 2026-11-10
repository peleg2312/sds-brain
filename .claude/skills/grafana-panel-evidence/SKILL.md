---
name: grafana-panel-evidence
description: Trace a Grafana alert or dashboard panel back to trustworthy evidence - the real query, datasource, units and freshness - before believing the number. Use for "the dashboard shows", "Grafana alert", "panel says latency is", "no data in Grafana", "is this graph right", "which datasource".
---
# From a Grafana panel to evidence

Read-only (rule 1): never save a dashboard, create a public snapshot, silence an alert or change a collection
interval. Needs: cluster, dashboard and panel, datasource, UTC interval, the reported impact. The `grafana` connection
(read-only tools: search, datasource, dashboard, Elasticsearch, Prometheus) does this directly when it is configured;
otherwise the user exports the panel JSON or pastes the query.

## Procedure
1. From the dashboard definition: panel expression, selected variables, transformations, unit, time override, and
   the datasource it queries.
2. What kind of datasource: Elasticsearch, Prometheus, or something else? A custom exporter does not imply
   Prometheus. Use the datasource UID from `knowledge/environment.md`; a display name is not enough when names repeat.
3. Run the same expression with the same selectors over a short interval around the event. Note the requested
   interval, the returned timestamps and the step. One cluster and one panel, not the whole retention.
4. Compare the raw result with the panel: a transformation, a repeated panel, an aggregation or a time shift can
   explain a difference. Elasticsearch: check the timestamp field and the query syntax of the installed editor
   (skill `es-request-correlation`).
5. Prometheus only if confirmed: read the metric's metadata before choosing a function; rate a counter over a
   suitable range, never read a cumulative counter as a current rate; mind resets and missing samples.
6. Correlate the interval with the matching backend skill (`ceph-health`, `rgw-request-triage`,
   `sg-capacity-metadata`...). A dashboard that cannot establish backend health is an observation gap, not a healthy
   backend.

Background: `knowledge/notes/observability-exporter-dashboard.md`. A metric or panel you worked out goes to
`knowledge/notes/observability.md` (rule 7).

## Four outcomes to tell apart
Real service degradation; stale or failed collection; a query / label mismatch; a visualization calculation.

## Result
Panel and datasource, interval, the actual expression, series count, units, freshness of collection, backend
observations, remaining hypotheses. When monitoring cannot say whether durability or availability is at risk, tell
the user to escalate.
