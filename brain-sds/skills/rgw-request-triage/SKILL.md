---
name: rgw-request-triage
description: Triage S3 errors or latency on Ceph RGW - separate RGW from RADOS, inspect the user without exposing keys, read RGW metrics correctly. Use for "RGW errors", "RGW is slow", "S3 on Ceph fails", "radosgw 5xx", "one gateway is slow", "bucket listing is slow".
---
# RGW S3 errors and latency

Read-only (rule 1). First make sure the request really goes to Ceph: an Objectify account can be an RGW user or a
StorageGRID tenant. Then collect: UTC interval, S3 operation, HTTP status, S3 error code, request ID, region,
addressing style, SDK / CLI version, proxy or load balancer in the path. Never ask for Authorization headers, secret
keys, session tokens or full signed URLs (rule 4).

## 1. RADOS or RGW?
Keep the FSID and baseline from `ceph-health`. For the RGW in question:
```bash
set -o pipefail
ceph orch ps --service-name <rgw-service> --daemon-id <daemon-id> --format json |
  jq -e 'if type=="array" then .[0:5] | map({daemon_type,daemon_id,hostname,status_desc,version,container_id,last_refresh}) else error("unexpected daemon schema") end'
```
Compare successful and failing requests by operation, endpoint and daemon over the same interval. A timeout with no
response is not an error response. A connectivity probe proves nothing about authentication or a specific S3 feature.

## 2. Follow the strongest evidence
| Evidence | Check next |
|---|---|
| Signature or authentication failure | skill `s3-signature-tls`: clock, credential identity, endpoint / region, addressing, request rewriting |
| Access denied | skill `s3-access-denied`: user suspended, action, bucket policy / ACL, ownership |
| Began after an SDK update | SDK options, signing / checksum behaviour, feature support of this RHCS release |
| Only one RGW is slow | that daemon's host: `linux-resource-pressure`, `linux-network-path`, its logs |
| Several RGWs degrade together with OSD warnings | skill `ceph-slow-ops` |
| Only listing, or one large bucket, is slow | per-operation latency and bucket / index evidence |

Ceph's S3 pages describe compatibility, not AWS parity; the vendor's patch notes decide whether a fix applies.

## 3. User metadata without the keys
Prefer the Objectify connection when it is enabled. Direct inspection, with the exact identity (`tenant$user` for a
named RGW tenant; a plain uid only when the empty legacy tenant is confirmed):
```bash
set -o pipefail
radosgw-admin user info --uid='<uid>' | jq -e '{user_id,tenant,suspended,max_buckets,user_quota,bucket_quota}'
```
The unfiltered output contains secret keys: never without the projection, never pasted or stored. A user record does
not prove which key signed a given request.

## 4. Metrics
RGW publishes operation counters and latency as sum / count pairs; the team's exporter may rename them. Check type,
unit, labels and reset behaviour first (`knowledge/notes/observability-exporter-dashboard.md`). A mean from sum / count
is not a p95. Keep the Grafana datasource and the cluster selector with every chart.

## Not here
Regenerating keys, editing policies, resharding buckets, raising log levels, test writes.

## Result
Affected operation, confirmed backend and release, the supported hypothesis, evidence gaps, the next read.
