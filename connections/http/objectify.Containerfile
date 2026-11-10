# Objectify's read-only adapter (connections/objectify/server.py, stdio) served over HTTP by gateway.py.
# Its configuration (config.local.json, the reviewed OpenAPI file, the CA) is mounted at /config; its upstream token
# comes from the environment variable the configuration names (a Podman secret). Nothing is downloaded here.
ARG BASE=registry.access.redhat.com/ubi9/python-312:latest
FROM ${BASE}
COPY server.py gateway.py config.example.json observed-endpoints.json /app/
USER 1001
EXPOSE 8000
ENV OBJECTIFY_CONFIG=/app/config.example.json
HEALTHCHECK CMD ["python3", "-c", "import socket; socket.create_connection(('127.0.0.1', 8000), 3)"]
ENTRYPOINT ["/bin/sh", "-c", "exec python3 /app/gateway.py --listen 0.0.0.0:8000 -- python3 /app/server.py --config \"$OBJECTIFY_CONFIG\""]
