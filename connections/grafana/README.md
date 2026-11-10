# Grafana connection (read-only)

The official Grafana MCP server v2.2.0 (Apache-2.0, `LICENSE.upstream`) is shipped in `vendor/` for Linux x86-64 and
ARM64, macOS ARM64 and Windows x86-64. Nothing is downloaded: `launch.py` checks the archive against the sha256 in
`release-manifest.json`, unpacks it once into `.cache/bin/` and starts it with `--disable-write`.

## Configure (once per person)
Create a Grafana **service account with the Viewer role** and a token for it, then in your shell profile:

```bash
export SDS_GRAFANA_URL=https://grafana.example.internal
export SDS_GRAFANA_TOKEN=<the service-account token>
export SDS_GRAFANA_CA_FILE=/etc/pki/ca-trust/source/anchors/internal-ca.pem   # only if Grafana uses a private CA
```

Start a new Claude session. Check any time with `python3 ~/.claude/sds-brain/connections/grafana/launch.py --check`.

Until the two variables are set, the connection offers one tool, `grafana_setup`, that says what is missing.

The launcher passes only this connection to the server: Grafana, OpenTelemetry and web-proxy settings inherited from
your shell are removed, anonymous usage reporting is off, and the certificate is always verified (`SDS_GRAFANA_CA_FILE`
for a private CA; verification is never switched off). The server needs **Grafana 9.0 or later** for its datasource
tools; record the installed Grafana and Elasticsearch versions in `knowledge/environment.md`.

## Before relying on it (once, with the team)
In Grafana, check that the service account sees only the folders and datasources the team needs (a dashboard
variable or a query filter is not an access boundary). Then in one session: list the datasources, read one known
dashboard, run one known Elasticsearch query over a short window, and look at the output for anything sensitive.
Write what was confirmed (datasource uids, index names, timestamp and request-id fields) into
`knowledge/environment.md`. Until then, treat it as connected but not confirmed.

## What Claude can do with it
17 read tools: search dashboards and folders, read a dashboard and its panel queries, list and check datasources,
query Elasticsearch, query Prometheus (metric names, labels, instant and range queries). No tool that creates or
changes anything is registered. What the token may see is decided in Grafana, not here: give the service account
access only to the folders and datasources the team needs.

To add a category (for example `loki`), edit `FLAGS` in `launch.py`. To update the server, replace the four archives
and `release-manifest.json` (name, sha256, binary sha256 and size of each) from the official release page on a
connected machine.
