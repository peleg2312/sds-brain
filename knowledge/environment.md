# Environment
<!-- Loaded in every session. Fill in the tables (or type /brain-sds:brain-setup and let Claude ask you). No passwords, keys or tokens. -->

Reported for the whole fleet on 2026-11-09, not yet confirmed per cluster (replace with the tables below):
- **Ceph**: Red Hat Ceph Storage, cephadm, containerized, with RGW. Releases in use: 7.1z7, 8.1z3, 8.1z6, 8.1z7, 8.1z8, 8.1z9.
- **StorageGRID**: 11.8, 11.9 and 12 (the minor / build of 12 is not confirmed).
- **Hosts**: RHEL 9.6 and 9.8.
- **Servers**: HPE Apollo 4200 (XL420), XL170r, XL190r, ProLiant DL385 (generations, controllers and iLO firmware not confirmed).
- **Monitoring**: Grafana, a custom exporter, Elasticsearch (whether Prometheus is behind Grafana is not confirmed).
- **Objectify**: internal API; an account is an RGW user on Ceph and a tenant on StorageGRID.

## Ceph clusters
| Cluster | FSID | RHCS release | Site | RGW endpoints / zones | Hosts (model) | Notes |
|---|---|---|---|---|---|---|
| | | | | | | |

## StorageGRID grids
| Grid | Version / build | Sites | S3 endpoints | Admin nodes | Notes |
|---|---|---|---|---|---|
| | | | | | |

## Servers
| Model | Generation | iLO | Storage controller | Used for |
|---|---|---|---|---|
| | | | | |

## Monitoring
- Grafana: url, version; one datasource per cluster? (name -> cluster):
- Custom exporter: where it runs, what scrapes it, the metrics that matter (name, unit, labels):
- Elasticsearch: what it holds (RGW logs, StorageGRID audit, object metadata?), index names, timestamp field, request-id field:

## Objectify
- Base url, how to authenticate (no secrets here), which backends it fronts:

## Still to confirm (each answer unlocks something; remove a line once it is answered above)
- Per cluster / grid: FSID or grid name, exact release (StorageGRID "12": which minor and build), endpoints.
- Servers: generation, storage controller, iLO firmware of each model (XL420 / XL170r / XL190r / DL385 is the
  reported mapping, not a confirmed one).
- Grafana and Elasticsearch versions; one datasource per cluster?; whether Prometheus is behind Grafana; the custom
  exporter's metric names, types and labels (one reviewed sample).
- Objectify: its `/openapi.json`, authentication scheme and one redacted successful response per read
  (`connections/objectify/INTEGRATION.md`).
- Red Hat documentation: which RHCS / RHEL manuals the team may add under `docs/redhat/`, or the offline portal.
