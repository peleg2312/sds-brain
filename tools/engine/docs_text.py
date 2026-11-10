"""Tool texts of the SDS docs server (read by mcp_stdio.py). Standard library only."""

INSTRUCTIONS = """\
Read-only, OFFLINE search over the SDS team's documentation: NetApp StorageGRID 11.8 / 11.9 / 12.0 (full manuals), \
Ceph Reef / Squid (health checks, RGW, multisite, cephadm, configuration), IBM Storage Ceph, AWS S3 API reference, \
Grafana, Prometheus, Elasticsearch, HPE iLO / Redfish, and library "team knowledge" (the team's own notes, runbooks, \
captures and incidents). The urls are for the humans.
1. search_docs with the exact technical terms (error text in "quotes", health check names such as PG_DEGRADED, S3 \
error codes such as SignatureDoesNotMatch, commands). Filter by vendor / product when known (list_sources; \
by_product shows where the hits are). read_top=2 returns the top sections inline. Partial or off-target: \
queries=[2-3 rephrasings in the vendor's words], replacing the `unmatched` words.
2. read_chunk the best 2-3 hits before answering; read_document for a whole page. related_docs(chunk_id) lists what \
the page cites and what cites it. also_in = the same page in other versions: open the installed one \
(storagegrid-118 / -119 / -120).
3. Cite title + url + version for every statement; never invent commands, settings or bug numbers. `matched` \
(n/m query words) appears only on partial hits: weak evidence. A hit titled "Unverified capture" is a teammate's \
draft: say so.
AWS pages describe AWS S3: check the feature against the installed RGW / StorageGRID release before relying on it. \
Red Hat Ceph Storage and RHEL manuals are in the library only if the team added them (list_sources shows)."""

SEARCH_DOC = ('Search the vendor docs and the team knowledge. query: technical words; "quoted text" must match verbatim '
              '(error messages); synonyms apply (rgw = object gateway, pg = placement group...). vendor: '
              'netapp|ceph|ibm|aws|grafana|prometheus|elastic|hpe|redhat. product: substring (storagegrid-119, squid, '
              's3...). Up to `limit` hits, max 2 per document; chunk_id feeds read_chunk. read_top (0-3): the full text '
              'of the best hits comes inline (field text), so one call answers. queries: several phrasings at once '
              '(wins over query); merged, with partial / unmatched reported per query in by_query.')

EXPLAIN_DOC = 'Not used by the SDS docs server.'

RELATED_DOC = ('Pages a document links to and pages that link to it, inside the library: follow a hit to the pages it '
               'references without a second search; give the chunk_id of a hit, or a path or url')
