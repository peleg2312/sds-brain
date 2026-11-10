# Red Hat Offline Knowledge Portal (optional)

If you run the Red Hat Offline Knowledge Portal (RHOKP) internally, Red Hat's `okp-mcp` container lets Claude search
it: RHCS and RHEL manuals, knowledge base solutions, CVEs and errata. This is the way to cover the Red Hat
documentation that is not in `docs/` (the other way: put the manuals under `docs/redhat/`, see the main README).

The plugin's `okp` server connects to it: nothing to install per person. Nothing here starts the service itself.

## Connect
The plugin looks for the service in this order:
- `SDS_OKP_URL` in a person's shell profile, e.g. `export SDS_OKP_URL=http://127.0.0.1:8000/mcp` (the service on this
  machine, or a tunnel to the team's host: `ssh -N -L 8000:127.0.0.1:8000 <host>`);
- `"url"` in `connections/okp/config.json`, committed: the team's shared endpoint, for everyone at once;
- `SDS_OKP_TOKEN` (shell profile only, never in git): a bearer token, when a proxy in front of the service asks for one.

Start a new session; `/mcp` lists `plugin:brain-sds:okp`. Check any time:
`python3 ~/.claude/sds-brain/connections/okp/launch.py --check`. Not configured, or the service does not answer when the
session starts: the server offers one tool, `okp_setup`, that says what is missing. A shared endpoint needs a TLS proxy
with authentication in front (the service has none of its own).

## Run the service (Linux host with Podman 4.6+, rootless Quadlet units in `podman/`)
The images are not shipped: `quay.io/redhat-user-workloads/rhel-lightspeed-tenant/rhel-knowledge-bridge` (okp-mcp) and,
for a new portal, `registry.redhat.io/offline-knowledge-portal/rhokp-rhel9` with your RHOKP access key
(https://access.redhat.com/offline/access). Pull them on a connected host, `podman save`, transfer, `podman load`.

- **You already have a portal**: copy `podman/existing-portal/sds-okp.container.example` to
  `~/.config/containers/systemd/sds-okp.container`; set `Image=` and `MCP_SOLR_URL=` (the portal's Solr base URL as
  seen from inside the container, without `/solr/portal/select`).
- **New portal**: copy the four files of `podman/new-portal/` to `~/.config/containers/systemd/` (drop `.example`),
  set both `Image=` lines, and create `~/.config/sds-brain/rhokp.env` (mode 0600) from `podman/rhokp.env.example`
  with the access key.

```bash
systemctl --user daemon-reload
systemctl --user start sds-okp.service
curl -fsS --max-time 30 http://127.0.0.1:8000/mcp -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"check","version":"1"}}}'
```
Only port 8000 is published, on loopback; `Pull=never` keeps the unit from fetching anything. A new portal needs
time to index before searches return results.

## Using its answers for Ceph
The okp-mcp search has no product filter and can label a result "RHEL" whatever the product is. Read the returned
title, product and version before applying a result to RHCS, and check once that a known RHCS document is found in
your portal. The portal is shared: do not put cluster names, credentials or incident data into its queries.
