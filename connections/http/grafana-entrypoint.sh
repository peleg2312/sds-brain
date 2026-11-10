#!/bin/sh
# Start the Grafana MCP server over HTTP with the brain's read-only profile. Everything comes from the environment
# (Podman secrets for the two tokens): GRAFANA_URL (https), GRAFANA_SERVICE_ACCOUNT_TOKEN (Viewer role),
# MCP_GRAFANA_SERVER_TOKEN (what Claude Code sends), MCP_ALLOWED_HOSTS (the name:port clients use, e.g.
# vm.example.internal:8444), optional GRAFANA_CA_FILE, MCP_TLS_CERT + MCP_TLS_KEY (HTTPS for the clients).
set -eu
fail() { echo "grafana-mcp: $*" >&2; exit 1; }
[ -n "${GRAFANA_URL:-}" ] || fail "GRAFANA_URL is not set"
case "$GRAFANA_URL" in https://*) ;; *) fail "GRAFANA_URL must be https://" ;; esac
[ -n "${GRAFANA_SERVICE_ACCOUNT_TOKEN:-}" ] || fail "GRAFANA_SERVICE_ACCOUNT_TOKEN is not set"
TOKEN=${MCP_GRAFANA_SERVER_TOKEN:-}
[ "${#TOKEN}" -ge 16 ] || fail "MCP_GRAFANA_SERVER_TOKEN must be set (16 characters at least): without it anyone could call the server"
[ -n "${MCP_ALLOWED_HOSTS:-}" ] || fail "MCP_ALLOWED_HOSTS is not set (the host:port Claude Code uses, e.g. vm.example.internal:8444)"
set -- -t streamable-http --address 0.0.0.0:8000 --disable-write --usage-stats=disabled \
  --enabled-tools=search,datasource,dashboard,elasticsearch,prometheus --allowed-hosts "$MCP_ALLOWED_HOSTS"
[ -n "${GRAFANA_CA_FILE:-}" ] && set -- "$@" --tls-ca-file "$GRAFANA_CA_FILE"
if [ -n "${MCP_TLS_CERT:-}" ]; then set -- "$@" --server.tls-cert-file "$MCP_TLS_CERT" --server.tls-key-file "$MCP_TLS_KEY"; fi
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
export GRAFANA_USAGE_STATS=disabled DO_NOT_TRACK=1
exec /usr/local/bin/mcp-grafana "$@"
