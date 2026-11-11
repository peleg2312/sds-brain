# Tool map
<!-- Loaded in every session: which tool answers what. Kept up to date by /brain-sds:brain-setup and by the team (no secrets). -->
- **docs-http** (the VM's docs service, when connected): the vendor library for every question about how a product
  works, plus the team's knowledge as of its last refresh. `search_docs` -> `read_chunk` on the best hits.
- **docs-local**: the team's knowledge as it is on this machine now (notes, runbooks, captures, incidents); the vendor
  library too when there is no docs-http. Questions about this environment or a past problem: here first.
- **grafana** (read only, when configured): `search_dashboards`, `get_dashboard_summary` then
  `get_dashboard_panel_queries` (cheaper than `get_dashboard_by_uid`), `list_datasources`, `query_elasticsearch`,
  `query_prometheus` / `list_prometheus_metric_names` (only if Prometheus is behind Grafana). Datasource uids per
  cluster: `environment.md`.
- **objectify**: `objectify_status` only, until its contract is supplied (`connections/objectify/INTEGRATION.md`).
  grafana and objectify run on each machine, or once on the VM over HTTP (`connections/http/README.md`): same tools.
- **okp** (Red Hat offline portal, when configured): RHCS / RHEL manuals and knowledge base; check product and version
  of each result. Not configured: `okp_setup` says what is missing.
- **storagegrid** (read only): `sg_health`, `sg_node_health`, `sg_tenants` (logical usage vs quota), `sg_ilm`,
  `sg_metrics` (Prometheus query: ILM queue, capacity), `sg_get`. **ceph** (read only, dashboard API): `ceph_status`
  (release, health checks), `ceph_osds`, `ceph_pools`, `ceph_capacity`, `ceph_daemons`, `ceph_logs`, `ceph_rgw_*`,
  `ceph_api_get`. **oneview** (read only): `ov_alerts`, `ov_server_hardware`, `ov_server`, `ov_tasks` (what changed).
  **ilo** (read only): `ilo_summary`, `ilo_logs` (IML / IEL), `ilo_storage`, `ilo_thermal`, `ilo_power`, `ilo_firmware`.
  Not set up: their `*_setup` tool says what is missing (`connections/servers/README.md`).
- **Shell, run by the user** (Claude runs read commands itself only on a machine that has them, when asked for live
  state): `ceph` / `radosgw-admin` / `cephadm` reads on an admin host, `aws s3api` / `s3cmd` reads, Grid Manager and
  Tenant Manager screens, `ilorest` / `ipmitool` / `smartctl -a` reads, `journalctl`, `sar`, `ss`, `ausearch`.
- Not tools: the skills (`/brain-sds:ceph-health`, `/brain-sds:sg-ilm-backlog`...) are procedures that name the reads.
