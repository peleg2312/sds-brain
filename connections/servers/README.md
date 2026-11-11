# Read-only MCP servers: StorageGRID, Ceph, HPE OneView, HPE iLO

No vendor publishes an MCP server for these four (checked November 2026: NetApp has one for ONTAP and Harvest's
monitoring data; HPE for GreenLake and networking; the community Ceph, OneView and Redfish servers include power,
profile or configuration writes). So the brain has its own, built on the official MCP Python SDK and on what each
vendor itself uses:

| Server | Talks to | The vendor's own way | Account to give it |
|---|---|---|---|
| `storagegrid` | the Grid Management API of an admin node | as NetApp's Harvest collector and `netapp.storagegrid` Ansible collection do: `GET /api/versions`, `POST /api/v<n>/authorize`, Bearer token, Prometheus metrics at `/metrics/api/v1/query` | a Grid Manager group with read-only access |
| `ceph` | the Ceph Dashboard REST API of the active manager (RHCS 8 / Squid, RHCS 9) | `POST /api/auth`, then each GET with its media version from Ceph's own `openapi.yaml` (`sds_mcp/ceph_api.json`, `gen_ceph_api.py`) | a dashboard user with the built-in `read-only` role |
| `oneview` | the OneView appliance | HPE's `hpeOneView` SDK | the `Read only` role |
| `ilo` | each server's iLO 4 / 5 / 6 (Redfish) | HPE's `python-ilorest-library` | the iLO `Read Only` role (Login privilege only) |

## Read-only, in code, not only by convention
- StorageGRID and Ceph: the HTTP client sends GET only; the one sign-in request is allowed by its exact path. Anything
  else raises before it leaves the process.
- OneView and iLO: the vendor library's connection is wrapped, so even a write method of the SDK (power, profiles,
  resets) is refused before it is sent; only the sign-in and sign-out pass.
- Generic reads (`sg_get`, `ceph_api_get`, `ilo_get`) are limited to lists: NetApp's documented grid reads; the GET paths
  of Ceph's API description minus the ones that hand out credentials (iSCSI CHAP, SMB join, dashboard users,
  multi-cluster tokens); Redfish under `/redfish/v1/` minus accounts, sessions, certificates and security.
- Answers are cut to a size Claude can use, and every key that looks like a secret (`password`, `token`, `keys`,
  `secret_key`...) is replaced by `<redacted>`; RGW user keys are removed outright.
- TLS is always verified: a `ca_file` per system or the system trust store. iLO needs a `ca_file` or the certificate's
  SHA-256 `fingerprint` (HPE's library does not verify otherwise). There is no switch to turn verification off.
- iLO: every call signs in and signs out (an iLO has few session slots).
- Tools carry `readOnlyHint` and no destructive hint.
- The accounts should still be read-only ones: that is the real guarantee.

## Inventory and credentials
`targets.json` (copy `targets.example.json`): names and addresses of the grids, clusters, appliances and iLOs, and their
CA files. No secrets: they come from the environment (a Kubernetes or Podman secret), `SDS_<KIND>_<NAME>_USERNAME` /
`_PASSWORD`, or one shared read-only account per kind, `SDS_<KIND>_USERNAME` / `_PASSWORD`. The tools take the name:
`sg_health(grid_name="grid-a")`, `ceph_status(cluster_name="prod-a")`, `ilo_logs(server_name="osd-02")`.

## Running them: OpenShift (recommended), Podman, or each person's machine
- **OpenShift**: `connections/openshift/sds-mcp-servers.yaml` (one image, four pods, the inventory as a ConfigMap,
  one secret per server). Then `python3 connections/http/use.py ceph https://sds-ceph.<apps domain>/mcp --token-file
  ceph.token` (and storagegrid, oneview, ilo), commit, push.
- **Podman on the VM**: the same image, `podman run ... localhost/sds-brain/sds-mcp:<tag> ceph --http 0.0.0.0:8000`
  with the inventory mounted at `/config` and the secrets as environment.
- **Each person's machine** (stdio, the plugin's default entries): `pip install -r requirements.txt` and a
  `targets.json`; without them the plugin's entry offers one tool that says what is missing.

The image: `python3 connections/http/build.py servers --save sds-mcp.tar` on a machine with PyPI; inside the internal
network with your PyPI mirror (`--pip-index-url`) or a wheelhouse made on a connected machine (`build.py
--download-wheels <dir>`, then `--wheelhouse <dir>`; `jsonpath-rw`, needed by HPE's iLO library, exists only as
source and is built offline from it).

## Tools
- **storagegrid**: `sg_grids`, `sg_version`, `sg_health`, `sg_alerts` (current alerts, most severe first),
  `sg_alert_history` (resolved), `sg_node_health`, `sg_topology`, `sg_tenants` (logical usage against quota), `sg_ilm`,
  `sg_metrics` (Prometheus query on the grid's own metrics, `*_over_time` for a period), `sg_get`.
- **ceph**: `ceph_clusters`, `ceph_status` (release, health checks), `ceph_alerts` (active Prometheus alerts through
  the dashboard's Alertmanager), `ceph_metrics` (Prometheus query, now or over the last N minutes, through the
  dashboard), `ceph_perf_counters`, `ceph_capacity`, `ceph_osds`, `ceph_osd`,
  `ceph_pools`, `ceph_hosts`, `ceph_services`, `ceph_daemons`, `ceph_logs`, `ceph_rgw_daemons`,
  `ceph_rgw_sync_status`, `ceph_rgw_buckets`, `ceph_rgw_user` (no keys), `ceph_config`, `ceph_api_get`.
- **oneview**: `ov_appliances`, `ov_version`, `ov_alerts` (with corrective actions), `ov_utilization` (CPU, power,
  temperature samples per server or enclosure, as OneView collects them from the iLO), `ov_server_hardware`,
  `ov_server`, `ov_enclosures`, `ov_interconnects`, `ov_server_profiles`, `ov_tasks`.
- **ilo**: `ilo_servers`, `ilo_summary` (aggregate health), `ilo_logs` (IML / IEL: the iLO's events, its alerts),
  `ilo_storage`, `ilo_thermal` and `ilo_power` (current readings), `ilo_firmware`, `ilo_get`.

Metrics and alerts at a glance: StorageGRID `sg_metrics` + `sg_alerts`; Ceph `ceph_metrics` + `ceph_alerts` (and the
health checks in `ceph_status`); OneView `ov_utilization` + `ov_alerts`; iLO readings (`ilo_thermal`, `ilo_power`)
and events (`ilo_logs`). History beyond what each system keeps is Grafana's job (the grafana server).

## Tests
`python3 connections/servers/test_servers.py` (needs `requirements.txt`): stand-ins of the four APIs over TLS with a
test CA; every request they receive is recorded, so the tests prove that no write left a server, that the SDK and
library guards refuse writes, that RGW keys never come back, that each iLO session is signed out, and that HTTP mode
requires the token. `test_brain.py` runs it when the packages are installed. The image itself was tested the same way
(random user id, read-only root).

What is not tested here: real StorageGRID, Ceph, OneView and iLO systems. The calls follow the vendors' own code and
API descriptions, but field names in the answers can differ between releases: the tools return what the system
sends, and say so when a field is missing. Try each against one system before relying on it.
