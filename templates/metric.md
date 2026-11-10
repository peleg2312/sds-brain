## <metric_name> (<exporter>)
<!-- One block per metric the team has understood, in knowledge/notes/observability.md. Never guess a field. -->
- Meaning: <what it measures, in one sentence>
- Type / unit: <counter | gauge | histogram | summary> · <bytes | seconds | ms | count>
- Labels: <label: meaning; which label names the cluster>
- Collected: <scrape or collection interval> · by <Prometheus / Elasticsearch / ...> · datasource uid <uid>
- Counter resets / missing values: <what a reset, a zero, a null and an absent series mean>
- Expected cardinality: <series count, roughly>
- Approved query: `<PromQL or Elasticsearch query, bounded, with the cluster selector>`
- Example: <dashboard uid / panel id that shows it>
- Confirmed: <yyyy-mm-dd> · <confidence> · <source: exporter code, HELP/TYPE sample, owner>
