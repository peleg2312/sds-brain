# Connections as HTTP servers (containers on the VM)

By default each person's plugin starts Grafana and Objectify on their own machine (stdio), with their own settings.
Run them once on the VM instead, and everyone connects over HTTP: no per-person Grafana token or Objectify
configuration, one place to change them. The plugin keeps the same server names, so nothing else changes.

| Connection | Image | How it serves HTTP |
|---|---|---|
| grafana | `localhost/sds-brain/grafana-mcp:v2.2.0` (UBI 9 minimal + the verified official binary) | The Grafana server's own streamable HTTP, read-only, bearer token required |
| objectify | `localhost/sds-brain/mcp-gateway:<commit>` (UBI 9 Python 3.12 + the adapter + the gateway) | `gateway.py`: the stdio adapter behind HTTP, bearer token required |
| okp | Red Hat's okp-mcp container (`connections/okp/README.md`) | Already HTTP, without a token of its own: put `mcp-gateway --upstream` in front (the OpenShift manifest does) |
| docs | the VM's docs service, or `localhost/sds-brain/docs-mcp:<commit>` (the library inside, the team's knowledge from git) | `vm-setup.py` writes docs-http for the VM; `use.py docs-http <url>` for a container |

## 1. Build (a machine with podman or docker and this repository)
```bash
python3 connections/http/build.py grafana   --save grafana-mcp.tar     [--base <internal registry>/ubi9/ubi-minimal:latest]
python3 connections/http/build.py gateway   --save mcp-gateway.tar     [--base <internal registry>/ubi9/python-312:latest]
python3 connections/http/build.py docs      --save docs-mcp.tar        [--base <internal registry>/ubi9/python-312:latest]
```
Nothing is downloaded except the base image: on the internal network, `--base` names the copy in your registry.
The Grafana archive and executable are checked against `connections/grafana/release-manifest.json` first.
Copy the tar files to the VM and `podman load -i grafana-mcp.tar` (same for the others). On OpenShift instead:
`connections/openshift/README.md`.

## 2. Run (the VM, Podman Quadlet)
Copy the unit from `quadlet/` to `/etc/containers/systemd/` (root) or `~/.config/containers/systemd/` (rootless),
set the lines marked in it (Grafana url, the name and port clients use, the Objectify configuration folder), create
the secrets as its header shows, then `systemctl [--user] daemon-reload && systemctl [--user] start sds-grafana-mcp`.

- Two tokens per server: the upstream one (Grafana Viewer service account, Objectify read-only token) stays in a
  Podman secret on the VM; the MCP token (`grafana-mcp.token`, generated) is what Claude Code sends.
- HTTPS: mount the VM's certificate as the unit shows; members who ran `join.sh` already trust it. Plain HTTP sends the
  token in clear: a lab only. Open the port (`firewall-cmd --add-port=8444/tcp --permanent`).
- The containers run read-only, with no capabilities and without root inside.
- Grafana checks the Host header: `MCP_ALLOWED_HOSTS` is the exact `name:port` the members' url uses.

## 3. Point the plugin at it, commit, push
```bash
python3 connections/http/use.py grafana   https://<vm>:8444/mcp --token-file grafana-mcp.token
python3 connections/http/use.py objectify https://<vm>:8445/mcp --token-file objectify-mcp.token
git add brain-sds/.mcp.json && git commit -m "SDS brain: grafana and objectify on the VM" && git push
```
Every member's plugin uses them from their next session (`/mcp` shows them as HTTP). Back to per-person stdio:
`use.py grafana --stdio`. As with docs-http, the MCP token sits in `brain-sds/.mcp.json`, readable by everyone with
access to the team repository: the upstream credentials behind it are read-only, and a new token (a new secret,
`use.py` again) shuts out someone who left.

## Check
```bash
curl -s https://<vm>:8444/healthz                 # grafana: ok
curl -s https://<vm>:8445/health                  # objectify: {"status": "ok"}
curl -s -o /dev/null -w '%{http_code}\n' -X POST https://<vm>:8444/mcp -d '{}'    # 401: the token is required
```
Tested: both images built from this repository, ran read-only without capabilities, refused calls without the token,
and Claude Code connected to both through the plugin and called their tools. Not tested: against your Grafana,
Objectify, registry, certificate or Podman version.
