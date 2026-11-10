# The SDS docs service: the library of the repository's docs/, indexed at build time, plus the team's knowledge
# from the team repository (docs-serve.py). Nothing is downloaded here; build.py stages the files.
ARG BASE=registry.access.redhat.com/ubi9/python-312:latest
FROM ${BASE} AS index
COPY tools /app/tools
COPY docs /src/docs
RUN python3 -c "import sys; sys.path.insert(0, '/app/tools/engine'); import docs_index; docs_index.build('/src/docs', '/tmp/docs.db', log=lambda *a: None)"

FROM ${BASE}
COPY tools /app/tools
COPY team.json docs-serve.py /app/
COPY --from=index /tmp/docs.db /app/docs.db
USER 1001
EXPOSE 8000
ENV SDS_DATA=/data
HEALTHCHECK CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]
ENTRYPOINT ["python3", "/app/docs-serve.py"]
