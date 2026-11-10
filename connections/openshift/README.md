# The brain's MCP servers on OpenShift

Every MCP server the plugin uses can run as a pod, reached through a Route over HTTPS with a bearer token. Members
then need nothing per person: no docs index on their machine, no Grafana token, no Objectify configuration.

| Manifest | Pod | Image (built by `connections/http/build.py`) | In the plugin |
|---|---|---|---|
| `sds-docs.yaml` | the docs service: the SDS library in the image, the team's knowledge cloned from the team repository | `sds-brain/docs-mcp` | `docs-http` |
| `sds-grafana.yaml` | the official Grafana MCP server, read-only | `sds-brain/grafana-mcp` | `grafana` |
| `sds-objectify.yaml` | Objectify's read-only adapter behind the token gateway | `sds-brain/mcp-gateway` | `objectify` |
| `sds-okp.yaml` | Red Hat's okp-mcp (your existing portal) with the token gateway in the same pod | Red Hat's okp-mcp + `sds-brain/mcp-gateway` | `okp` |
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
# then, where the registry is reachable:
podman load -i docs-mcp.tar && podman tag localhost/sds-brain/docs-mcp:<tag> <registry>/sds-brain/docs-mcp:<tag> && podman push <registry>/sds-brain/docs-mcp:<tag>
```
(The same for the other two. `build.py` prints each tag.) The docs image carries the library: rebuild and push it, and
change the tag in `sds-docs.yaml`, when documents are added under `docs/`. The team's knowledge needs no rebuild.

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

## 3. Point the plugin at the Routes, commit, push
```bash
oc get secret sds-docs -o jsonpath='{.data.MCP_SERVER_TOKEN}' | base64 -d > docs.token
python3 connections/http/use.py docs-http https://sds-docs.<apps domain>/mcp?team=sds --token-file docs.token
python3 connections/http/use.py grafana   https://sds-grafana.<apps domain>/mcp --token-file grafana.token
python3 connections/http/use.py objectify https://sds-objectify.<apps domain>/mcp --token-file objectify.token
python3 connections/http/use.py okp       https://sds-okp.<apps domain>/mcp --token-file okp.token
git add brain-sds/.mcp.json && git commit -m "SDS brain: MCP servers on OpenShift" && git push
rm -f *.token
```
Every member's plugin uses them from their next session. With `docs-http` in the plugin, `docs-local` stops indexing
the library on each machine and keeps only the team's knowledge (a note is found the minute it is written).

The Route uses the cluster's ingress certificate: machines that do not trust it yet get it once (the system store,
or `NODE_EXTRA_CA_CERTS` before starting `claude`). The tokens sit in `brain-sds/.mcp.json`, readable by everyone with
access to the team repository, as for every team's docs-http: the credentials behind them are read-only, and a new
secret value plus `use.py` again shuts out someone who left (`oc rollout restart deployment/<name>` after changing it).

## What was tested
Each image was run as OpenShift runs it (random user id, read-only root, no capabilities, a writable `/data` for the
docs pod only): the docs pod cloned a team repository, indexed it and answered library and knowledge searches;
Grafana and the gateway answered their tools; all three refused calls without the token. The manifests parse and
are checked by `test_brain.py`, but were not applied to a real cluster here: check them against your cluster
(`oc apply --dry-run=server -f ...`) first.
