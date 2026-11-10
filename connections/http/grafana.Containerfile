# The official Grafana MCP server (the verified binary from connections/grafana/vendor) over HTTP, read-only.
# Built by build.py, which verifies the archive's sha256 first and stages the binary; nothing is downloaded here.
ARG BASE=registry.access.redhat.com/ubi9/ubi-minimal:latest
FROM ${BASE}
COPY mcp-grafana /usr/local/bin/mcp-grafana
COPY grafana-entrypoint.sh /usr/local/bin/grafana-entrypoint.sh
COPY LICENSE.upstream /licenses/mcp-grafana-LICENSE
USER 1001
EXPOSE 8000
HEALTHCHECK CMD ["/bin/sh", "-c", "exec 3<>/dev/tcp/127.0.0.1/8000"]
ENTRYPOINT ["/bin/sh", "/usr/local/bin/grafana-entrypoint.sh"]
