# Objectify connection (read-only, off until its API contract is supplied)

`server.py` is a dependency-free MCP adapter for the team's internal Objectify API. As shipped it exposes one tool,
`objectify_status`, which contacts nothing and reports what is still missing. Claude sees it as connection
`objectify`.

## What is known
From a Swagger screenshot only (`observed-endpoints.json`): four GET routes are candidates for reads (`/back`,
`/account/obj_acc`, `/account/obj_acc/epg`, `/getAllSink`); every POST / PATCH / DELETE route and the unclear
`GET /account/parlay` are excluded. Parameters, authentication, response fields and what each GET really does are
not known yet, so nothing is enabled.

## To enable reads
1. Export the real `/openapi.json` from Objectify and keep it outside this repository's commits.
2. Copy `config.example.json` to `config.local.json` (ignored by git) and fill in: `base_url` (https), `tls.ca_file`,
   `authentication` (`bearer` or `env_header`; the token itself stays in an environment variable named by
   `token_env`), `contract.openapi_file` and its `openapi_sha256`, and the operations you approve with the response
   fields Claude may see (never keys).
3. Check without contacting anything: `python3 ~/.claude/sds-brain/connections/objectify/launch.py --check`
4. Start a new Claude session; `objectify_status` lists the enabled operations.

The adapter was written for separate customers: each call carries the `customer_id` and `cluster_id` set in the
configuration's `context`, and every returned record must match them. With one organization, use fixed names (for
example your organization and the cluster) in `context`.

The full contract (what the owner must supply, every setting, the request and response safeguards, the protocol
limits): `INTEGRATION.md`.

Tests: `python3 -m unittest connections/objectify/test_objectify.py` (65 tests, no network).
