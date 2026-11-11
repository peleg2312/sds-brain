# The SDS brain's read-only MCP servers (StorageGRID, Ceph, HPE OneView, HPE iLO): one image, the server chosen by its
# arguments: `<storagegrid|ceph|oneview|ilo> --http 0.0.0.0:8000`. build.py stages the package and, for a network
# without PyPI, a wheelhouse (wheels/); otherwise pip installs the pinned requirements from PyPI.
ARG BASE=registry.access.redhat.com/ubi9/python-312:latest
FROM ${BASE}
ARG PIP_INDEX_URL=
COPY requirements.txt /app/requirements.txt
COPY wheels /tmp/wheels
RUN if ls /tmp/wheels/*.whl >/dev/null 2>&1; then pip install --no-cache-dir --no-index --find-links /tmp/wheels -r /app/requirements.txt; \
    else pip install --no-cache-dir ${PIP_INDEX_URL:+--index-url "$PIP_INDEX_URL"} -r /app/requirements.txt; fi
COPY sds_mcp /app/sds_mcp
COPY stub_mcp.py /app/stub_mcp.py
USER 1001
WORKDIR /app
ENV PYTHONPATH=/app SDS_MCP_CONFIG=/config/targets.json PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]
ENTRYPOINT ["python3", "-m", "sds_mcp"]
CMD ["ceph", "--http", "0.0.0.0:8000"]
