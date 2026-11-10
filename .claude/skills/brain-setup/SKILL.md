---
name: brain-setup
description: First-time setup and later refresh of the brain's environment file and connections - fill knowledge/environment.md with the user, check the docs library, Grafana, Objectify and the Red Hat portal.
disable-model-invocation: true
---
# Brain setup

Goal: `knowledge/environment.md` describes the real clusters and grids, and the user knows which connections work.
Ask, do not guess (rule 2); no passwords, keys or tokens in any file (rule 4).

## 1. Connections (report each as: working / not configured / failing, with the fix)
- **sds-docs**: call `list_sources`; say how many documents per product, and what is missing for this team (Red Hat
  manuals: `docs-lookup`, "Adding documents").
- **grafana**: if its tools answer, list the datasources (name, type, uid). If it says it is not configured, show the
  user the two lines from `connections/grafana/README.md` (URL and read-only token in their shell profile).
- **objectify**: call its status tool and report what it says is still needed (`connections/objectify/README.md`).
- **sds-okp** (Red Hat offline portal): only if the user runs the portal; `connections/okp/README.md` has the one
  command that connects it.

## 2. Environment, one section at a time
Read `knowledge/environment.md`. For each table, ask the user for the real values and fill them in; keep what is
already filled. Where a read-only command gives the answer, offer it for the user to run and paste:
- Ceph cluster: `ceph fsid`, `ceph versions`, `ceph orch ls rgw --format json | jq 'map({service_name,placement})'`
- StorageGRID grid: version / build from Grid Manager (Help > About), sites, the S3 endpoint FQDNs and ports
- Servers: model and generation from iLO, or `dmidecode -s system-product-name`
- Monitoring: Grafana datasources (from the grafana connection), which one belongs to which cluster; what the custom
  exporter emits; what the Elasticsearch indices hold, with timestamp and request-ID fields

When a section is confirmed, delete the matching "reported, not yet confirmed" line at the top of the file.

## 3. Core notes
Ask for the few facts every session needs and put them in `knowledge/notes.md` (60 lines at most): naming prefixes for
clusters, zones, buckets, tenants; agreed thresholds; who owns what and how to escalate.

## 4. Finish
Summarize what was filled, what is still empty, and which connections remain to configure. The save hook has already
committed and pushed the files.
