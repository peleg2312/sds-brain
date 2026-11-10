---
name: s3-latency-5xx
description: Investigate slow S3 requests or 5xx / 503 SlowDown errors on RGW or StorageGRID from existing telemetry - which operations, which layer, since when. Use for "S3 is slow", "high latency", "503", "SlowDown", "500 InternalError", "timeouts on uploads", "requests are slower since".
---
# S3 latency and server errors

Read-only (rule 1): existing telemetry and narrow reads only. No benchmark traffic, test uploads, concurrency
changes, gateway restarts or recovery tuning.

## 1. Define "slow"
Cluster / grid, a bounded UTC interval and a comparable baseline. Operation mix, object-size bands, concurrency,
client / SDK version, retry behaviour. Which latency: total application time, time to first byte, server processing,
multipart completion? Keep successful and failed requests apart.

## 2. Correlate
1. Request counts, error counts, latency distribution, bytes and retries over the **same** interval. A percentile
   from one dashboard does not combine with another time range or operation mix. Keep query, datasource, labels,
   aggregation and step (skill `grafana-panel-evidence`).
2. DNS / connect / TLS / client transfer time separately from backend service time.
3. The exact provider error: AWS lists `SlowDown` as a 503, but a 503 from a proxy or from another backend needs its
   own evidence. Request ID and the component that answered, before saying "throttling".
4. StorageGRID: traffic distribution and HA roles on the real S3 path; a standby with little traffic is normal
   (skill `sg-connectivity`). Node / site health, storage, ILM in the same interval (`sg-capacity-metadata`,
   `sg-ilm-backlog`).
5. Ceph RGW: continue with `rgw-request-triage`, then `ceph-health` / `ceph-slow-ops`; a frontend symptom does not
   name an OSD.

## 3. Hypothesis table
For each candidate (client retry storm, one degraded gateway path, a shift in object sizes, a backend placement
constraint, a datasource that stopped reporting): evidence for, evidence against, one next read. Add the timeline of
application, network, certificate, maintenance and storage changes.

## Result
Affected operations and population, the timing layer, the measured regression against the baseline, uncertainty, the
next scoped evidence. "More retries" or "more concurrency" is a change with load impact, not a diagnostic.
