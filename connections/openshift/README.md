# The brain's MCP servers on OpenShift

Every MCP server the plugin uses can run as a pod, reached through a Route over HTTPS with a bearer token. Members
then need nothing per person: no docs index on their machine, no Grafana token, no Objectify configuration, no
StorageGRID, Ceph, OneView or iLO account.

| Manifest | Pod | Image (built by `connections/http/build.py`) | In the plugin |
|---|---|---|---|
| `sds-docs.yaml` | the docs service: the SDS library in the image, the team's knowledge cloned from the team repository | `sds-brain/docs-mcp` | `docs-http` |
| `sds-grafana.yaml` | the official Grafana MCP server, read-only | `sds-brain/grafana-mcp` | `grafana` |
| `sds-objectify.yaml` | Objectify's read-only adapter behind the token gateway | `sds-brain/mcp-gateway` | `objectify` |
| `sds-okp.yaml` | Red Hat's okp-mcp (your existing portal) with the token gateway in the same pod | Red Hat's okp-mcp + `sds-brain/mcp-gateway` | `okp` |
| `sds-mcp-servers.yaml` | four pods, one image: the brain's read-only StorageGRID, Ceph, HPE OneView and HPE iLO servers (`connections/servers/README.md`) | `sds-brain/sds-mcp` | `storagegrid`, `ceph`, `oneview`, `ilo` |
| `networkpolicy.yaml` | only the OpenShift router reaches these pods | | |

All pods: one replica, not root, read-only root filesystem, no capabilities, `RuntimeDefault` seccomp, no service
account token, memory limits. They fit the default `restricted-v2` SCC; nothing needs a special permission.

## 1. Images into your registry
On a machine with podman or docker and this repository (`--base`: the UBI images from your registry when it has no
internet):
```bash
python3 connections/http/build.py docs    --save docs-mcp.tar
python3 connections/http/build.py grafana --save grafana-mcp.tar
python3 connections/http/build.py gateway --save mcp-gateway.tar
python3 connections/http/build.py servers --save sds-mcp.tar        # the StorageGRID / Ceph / OneView / iLO servers
# then, where the registry is reachable:
podman load -i docs-mcp.tar && podman tag localhost/sds-brain/docs-mcp:<tag> <registry>/sds-brain/docs-mcp:<tag> && podman push <registry>/sds-brain/docs-mcp:<tag>
```
(The same for the others. `build.py` prints each tag.) The docs image carries the library: rebuild and push it, and
change the tag in `sds-docs.yaml`, when documents are added under `docs/`. The team's knowledge needs no rebuild.

The `servers` image installs its Python packages (the MCP SDK, HPE's `hpeOneView` and `python-ilorest-library`,
`httpx`) while it is built: on a machine with PyPI, or inside the network with your PyPI mirror
(`--pip-index-url https://<mirror>/simple`) or a wheelhouse prepared on a connected machine
(`build.py --download-wheels wheels/`, carry the folder, then `build.py servers --wheelhouse wheels/`).

## 2. Project, secrets, manifests
```bash
oc new-project sds-brain
oc create secret generic sds-docs --from-literal=MCP_SERVER_TOKEN=$(head -c 24 /dev/urandom | base64 | tr -d '/+=') \
   --from-literal=SDS_REPO_TOKEN=<a read-only deploy token of the team repository>
oc create secret generic sds-grafana --from-literal=GRAFANA_SERVICE_ACCOUNT_TOKEN=<Grafana Viewer token> \
   --from-literal=MCP_GRAFANA_SERVER_TOKEN=$(head -c 24 /dev/urandom | base64 | tr -d '/+=')
# objectify and okp: the commands at the top of their manifests
```
In each manifest set the `<...>` values: the image and tag, the Route host (`<name>.<apps domain>`), the team
repository's https url, the Grafana url and the same Route host in `MCP_ALLOWED_HOSTS` (Grafana refuses any other Host
header), the portal's Solr url. Then:
```bash
oc apply -f connections/openshift/networkpolicy.yaml -f connections/openshift/sds-docs.yaml -f connections/openshift/sds-grafana.yaml
oc get pods -l app.kubernetes.io/part-of=sds-brain
curl -s https://sds-docs.<apps domain>/health
```
The docs pod clones the team repository with the deploy token (given to git by a credential helper from the secret;
never written into a url or a file), indexes the knowledge, and pulls again every 10 minutes and at once when a
member's note is pushed (the brain's notes hook calls `/refresh`).

## 2b. The StorageGRID, Ceph, OneView and iLO servers (`sds-mcp-servers.yaml`)
One image, four Deployments, each started with its own name (`args: ["ceph", "--http", "0.0.0.0:8000"]`), each with a
Service and a Route. Deploy only the ones you need.

**Accounts first, read-only on each system** (that is the real guarantee; the servers also refuse writes in code):
- StorageGRID: a Grid Manager group with read-only access, and a local user in it.
- Ceph: a dashboard user with the built-in read-only role: `ceph dashboard ac-user-create <user> -i <password file> read-only`.
  For `ceph_metrics` and `ceph_alerts` the dashboard needs its Prometheus and Alertmanager addresses
  (`ceph dashboard set-prometheus-api-host`, `set-alertmanager-api-host`); without them those two tools say so.
- OneView: a user (or directory group) with the `Read only` role.
- iLO: a user with the `Read Only` role (Login privilege only) on every iLO, the same name and password everywhere or
  one per server.

**The inventory**: copy `connections/servers/targets.example.json` to `targets.json` and fill in your grids (admin node
or its VIP, https), clusters (the active manager's dashboard, https, port 8443 by default), OneView appliances and
iLOs. No secrets in it. Certificates: put the CA that signed each system's certificate beside it and name it in
`ca_file`; for an iLO with a self-signed certificate its SHA-256 `fingerprint` also works
(`openssl s_client -connect <ilo>:443 </dev/null | openssl x509 -noout -fingerprint -sha256`). Self-signed systems
without a CA (Ceph dashboards with their default certificate, for example): `"verify": false`, for one system or for
all of a kind at once (`"ceph": {"defaults": {"verify": false}, "prod-a": {"url": "https://10.1.2.3:8443"}, ...}`):
encrypted, but the certificate is not checked (`connections/servers/README.md`). Then one ConfigMap for the four pods,
mounted at `/config`:
```bash
oc create configmap sds-mcp-targets --from-file=targets.json --from-file=storagegrid.pem --from-file=ceph.pem \
   --from-file=oneview.pem --from-file=ilo.pem        # only the .pem files targets.json names
```

**One secret per server**: the MCP token Claude Code sends, and the read-only account. A shared account per kind is
`SDS_<KIND>_USERNAME` / `_PASSWORD`; one per system is `SDS_<KIND>_<NAME>_USERNAME` / `_PASSWORD` with the name from
the inventory (`prod-a` -> `SDS_CEPH_PROD_A_PASSWORD`).
```bash
T() { head -c 24 /dev/urandom | base64 | tr -d '/+='; }
oc create secret generic sds-storagegrid --from-literal=MCP_SERVER_TOKEN=$(T) \
   --from-literal=SDS_STORAGEGRID_USERNAME=<user> --from-literal=SDS_STORAGEGRID_PASSWORD=<password>
oc create secret generic sds-ceph --from-literal=MCP_SERVER_TOKEN=$(T) \
   --from-literal=SDS_CEPH_USERNAME=<user> --from-literal=SDS_CEPH_PASSWORD=<password>
oc create secret generic sds-oneview --from-literal=MCP_SERVER_TOKEN=$(T) \
   --from-literal=SDS_ONEVIEW_USERNAME=<user> --from-literal=SDS_ONEVIEW_PASSWORD=<password>
oc create secret generic sds-ilo --from-literal=MCP_SERVER_TOKEN=$(T) \
   --from-literal=SDS_ILO_USERNAME=<user> --from-literal=SDS_ILO_PASSWORD=<password>
```

**Apply** after setting the image and tag and each Route host (`sds-ceph.<apps domain>`...) in the manifest:
```bash
oc apply -f connections/openshift/networkpolicy.yaml -f connections/openshift/sds-mcp-servers.yaml
oc get pods -l app.kubernetes.io/part-of=sds-brain
curl -s https://sds-ceph.<apps domain>/health                                   # {"status": "ok"}
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://sds-ceph.<apps domain>/mcp   # 401: the token is required
```

**Network**: the pods call out to the admin nodes (443), the managers' dashboards (8443), the OneView appliances (443)
and every iLO (443). `networkpolicy.yaml` only limits who reaches the pods; if your cluster restricts egress
(EgressFirewall, egress NetworkPolicy, a proxy), allow those addresses for the project. The pods use no web proxy.

**Changes later**: a new system is a line in `targets.json`, then `oc create configmap sds-mcp-targets ... --dry-run=client
-o yaml | oc replace -f -` and `oc rollout restart deployment/sds-<kind>`. A new password: update the secret, restart.

## 3. Point the plugin at the Routes, commit, push
```bash
oc get secret sds-docs -o jsonpath='{.data.MCP_SERVER_TOKEN}' | base64 -d > docs.token
python3 connections/http/use.py docs-http https://sds-docs.<apps domain>/mcp?team=sds --token-file docs.token
python3 connections/http/use.py grafana   https://sds-grafana.<apps domain>/mcp --token-file grafana.token
python3 connections/http/use.py objectify https://sds-objectify.<apps domain>/mcp --token-file objectify.token
python3 connections/http/use.py okp       https://sds-okp.<apps domain>/mcp --token-file okp.token
for k in storagegrid ceph oneview ilo; do                                   # the read-only servers
  oc get secret sds-$k -o jsonpath='{.data.MCP_SERVER_TOKEN}' | base64 -d > $k.token
  python3 connections/http/use.py $k https://sds-$k.<apps domain>/mcp --token-file $k.token
done
git add brain-sds/.mcp.json && git commit -m "SDS brain: MCP servers on OpenShift" && git push
rm -f *.token
```
Every member's plugin uses them from their next session. With `docs-http` in the plugin, `docs-local` stops indexing
the library on each machine and keeps only the team's knowledge (a note is found the minute it is written). Check the
read-only servers once from Claude: `/brain-sds:morning-check` calls each one's overview tool (`sg_overview`,
`ceph_overview`, `ov_overview`, `ilo_fleet_health`) and shows which answered.

The Route uses the cluster's ingress certificate: machines that do not trust it yet get it once (the system store,
or `NODE_EXTRA_CA_CERTS` before starting `claude`). The tokens sit in `brain-sds/.mcp.json`, readable by everyone with
access to the team repository, as for every team's docs-http: the credentials behind them are read-only, and a new
secret value plus `use.py` again shuts out someone who left (`oc rollout restart deployment/<name>` after changing it).

## What was tested
Each image was run as OpenShift runs it (random user id, read-only root, no capabilities, a writable `/data` for the
docs pod only): the docs pod cloned a team repository, indexed it and answered library and knowledge searches;
Grafana and the gateway answered their tools; all three refused calls without the token. The `servers` image (built
offline from a wheelhouse) passed the StorageGRID, Ceph, OneView and iLO tests against stand-ins of the four APIs over
TLS, with a random user id and a read-only root: no write left a server, HTTP refused calls without the token. They
were not run against real systems here: try each overview tool against one system first. The manifests parse and
are checked by `test_brain.py`, but were not applied to a real cluster here: check them against your cluster
(`oc apply --dry-run=server -f ...`) first.
