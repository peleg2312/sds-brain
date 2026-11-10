# Monitoring: understand the exporter and the dashboard before querying

The team has Grafana, a custom exporter and Elasticsearch. What the exporter emits, what stores it and what the
Elasticsearch indices hold (application logs, exporter output, object metadata) is recorded in `environment.md`.
Until it is, ask; never guess a metric or label name.

## What to learn from one dashboard
Dashboard UID and version, datasource UID and type, panel ID and title, query text, variables, units,
transformations, time overrides, refresh interval. Map each datasource to its cluster: a dashboard that looks like one
cluster's can query several backends.

## What to learn about each exporter metric
Original name, meaning, type, unit, labels, scope, collection interval, update timestamp, expected cardinality and
what an empty value means. Counters are not gauges. Check seconds versus milliseconds, bytes versus a displayed
conversion, and what "quota" means (logical tenant usage, bucket usage, provisioned limit or protected physical
capacity).

If the exporter speaks the Prometheus format, `HELP` / `TYPE` and a sample of the exposition are the starting
evidence; the exporter's code or the team's notes decide when they are missing or misleading.

## Query only after discovery
- Start from the existing panel's expression, bounded in time, keeping its cluster selector. Compare the raw data
  with the rendered value and note transformations and unit conversions before blaming the system.
- Prometheus: know whether a series is a counter, gauge, histogram or summary before choosing a function.
  Percentiles of separately computed summaries cannot be combined into a fleet percentile.
- Elasticsearch: note the index / alias, timestamp field, field types, request-ID field and the cluster field. A
  text field and its keyword field behave differently: read the mapping.

## No data and timing
Zero, null, absent series, stale scrape, exporter failure and datasource failure are six different things. Keep source
timestamps and time zone; compare the same interval across dashboards, Objectify, RGW and Grid Manager. A status
from ten minutes ago is not simultaneous with an incident that started two minutes ago.

A metric the team has understood is one fact line in `notes/observability.md`
(name · unit · type · labels · meaning · confidence · source).

Library: prometheus/prometheus (exposition formats, naming, histograms), grafana/grafana (Elasticsearch datasource and
query editor), elastic/elasticsearch.
