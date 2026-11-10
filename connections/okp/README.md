# Red Hat Offline Knowledge Portal (optional)

If you run the Red Hat Offline Knowledge Portal (RHOKP) internally, Red Hat's `okp-mcp` container lets Claude search
it: RHCS and RHEL manuals, knowledge base solutions, CVEs and errata. This is the way to cover the Red Hat
documentation that is not in `docs/` (the other way: put the manuals under `docs/redhat/`, see the main README).

Nothing here is started by the brain. You run the container; each person connects to it with one command.

## Connect (once per person)
```bash
claude mcp add --transport http --scope user sds-okp http://127.0.0.1:8000/mcp
```
`/mcp` in Claude then lists `sds-okp`. The service on another host: keep it on that host's loopback and tunnel,
`ssh -N -L 8000:127.0.0.1:8000 <host>`; a shared endpoint needs a TLS proxy with authentication in front.
Remove with `claude mcp remove --scope user sds-okp`.

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
