# The token gateway (gateway.py) with Objectify's read-only adapter: serves Objectify over HTTP by default
# (--objectify, its configuration at $OBJECTIFY_CONFIG), or fronts another MCP server (--upstream <url>: okp-mcp).
# Nothing is downloaded here; build.py stages the files.
ARG BASE=registry.access.redhat.com/ubi9/python-312:latest
FROM ${BASE}
COPY server.py gateway.py config.example.json observed-endpoints.json /app/
USER 1001
EXPOSE 8000
ENV OBJECTIFY_CONFIG=/app/config.example.json
HEALTHCHECK CMD ["python3", "-c", "import socket; socket.create_connection(('127.0.0.1', 8000), 3)"]
ENTRYPOINT ["python3", "/app/gateway.py"]
CMD ["--listen", "0.0.0.0:8000", "--objectify"]
