# Objectify: the read-only integration contract in detail

(From the first SDS brain. `README.md` beside this file is the short version; this is the reference for whoever
enables the reads with the Objectify owner.)

## Delivered state

The repository contains a runnable, dependency-free Python adapter, a disabled configuration template, a screenshot-derived endpoint inventory, and automated boundary tests. It has **not connected to your internal Objectify service**, and it does not claim that screenshot labels establish API semantics. The example exposes only `objectify_status`, which performs no network access.

Objectify maps an internal S3 account to a Ceph RGW user or a StorageGRID tenant, as reported by the user. Its account identifier, backend-routing rules, authentication mechanism, request parameters, response structure, and RBAC are still unknown. The adapter does not guess them.

Files:

- `connections/objectify/server.py`: stdio MCP server and HTTPS client.
- `connections/objectify/config.example.json`: disabled configuration; safe to run for local status.
- `connections/objectify/observed-endpoints.json`: exact screenshot transcription and disposition.
- `connections/objectify/test_objectify.py`: synthetic contracts and local/mocked transport tests, never production traffic.

## Screenshot evidence and tool mapping

| Observed API route | Candidate tool | Initial state |
|---|---|---|
| `GET /back` | `objectify_get_backend` | Disabled pending schema, semantics, scope, and projection review |
| `GET /account/obj_acc` | `objectify_get_account` | Disabled pending the same review |
| `GET /account/obj_acc/epg` | `objectify_get_account_epg` | Disabled; the meaning and sensitivity of EPG fields also need confirmation |
| `GET /getAllSink` | `objectify_list_accounts` | Disabled; requires upstream scoping plus customer and cluster checks on every response record |
| `GET /account/parlay` | None | Explicitly blocked because its purpose and side effects are unknown |
| `POST`, `PATCH`, `DELETE` routes | None | Explicitly blocked; no provisioning, resize, regeneration, recount, modification, or deletion tools |

The screenshot shows `/openapi.json`. Export that document from the internal service using your normal authenticated access. Do not infer that `obj_acc` is a path placeholder: it appears literally in the screenshot. The implementation uses only the four fixed candidate paths above. If the real contract differs, update and review the adapter rather than rewriting a path from model input.

## What is required to enable a tool

The service owner must supply or verify:

1. The actual OpenAPI 3 JSON document, its operation IDs, query parameter definitions, and response schemas. YAML and externally referenced schemas must first be resolved into a reviewed JSON document.
2. Read-only behavior of each candidate endpoint, including absence of reconciliation, lazy provisioning, or key rotation triggered by reads. A GET label alone is insufficient.
3. The internal HTTPS origin, any API base-path prefix, and the approved CA certificate chain.
4. A read-only credential whose **server-enforced authorization** is limited to the intended customer and cluster. A prompt, a `customer_id` argument, or a local configuration flag cannot replace upstream authorization.
5. Scalar response fields approved for model exposure. Account lookups may contain keys even when the request itself is read-only; never expose the raw response.
6. For **every enabled operation**, response fields that identify both customer and cluster on each record. This includes backend, individual-account, and EPG reads as well as lists. If the API cannot provide this evidence or cannot constrain the credential, leave the operation disabled until a reviewed server-side adapter supplies trustworthy scope evidence. A local claim that a response belongs to a customer cannot substitute for response evidence.

The `reviewed` and `upstream_context_scoped` flags record an operator's completed review. The adapter verifies their presence and the contract's checksum; **it cannot independently prove the service's real RBAC or business semantics**. Validate both with the service owner before setting those flags.

## Local setup

Use Python 3.9 or newer. No package installation is needed. Run these from the repository root:

```bash
python3 connections/objectify/server.py --config connections/objectify/config.example.json --check
python3 -m unittest connections/objectify/test_objectify.py -v
```

For a deployment, copy the example to a private, ignored configuration file. Keep the exported internal OpenAPI document, real endpoint names, and customer mappings outside shared documentation. Prefer a separate configuration and separate upstream credential for each customer/cluster pair.

```bash
cp connections/objectify/config.example.json connections/objectify/config.local.json
sha256sum /path/to/reviewed-objectify-openapi.json
```

Populate `contract.openapi_file` with an absolute path or a path relative to the configuration file. Set `openapi_sha256` to the actual digest, and record the reviewer alias and review date. A changed export requires a new review and pin. The adapter does not fetch the schema automatically.

Configure `authentication.type` as `bearer` or `env_header` **only after confirming the real API mechanism**. `token_env` names an environment variable populated by your approved secret-management process. `env_header` also requires the actual header name. No token is stored in the configuration. Basic authentication, cookie sessions, mTLS client authentication, arbitrary custom headers, and dynamic path parameters are not implemented in this release.

The operation configuration contains:

| Setting | Meaning |
|---|---|
| `method` | Must be exactly `GET` |
| `path` | Must match that tool's fixed candidate path and the pinned specification |
| `operation_id` | Must match the pinned OpenAPI `operationId` |
| `read_only_verified` | Operator confirmation after reviewing behavior |
| `parameters` | Exact query parameter set from OpenAPI, restricted to strings, integers, or booleans |
| `response.records_pointer` | JSON Pointer to the record or list; empty string means the JSON root |
| `response.many` | `false` for individual reads, `true` only for account listing |
| `response.fields` | Explicit scalar output projections; no pass-through objects or arrays |
| `response.scope_checks` | Mandatory record pointers compared to both configured `customer_id` and `cluster_id` on every operation |

Each local parameter rule specifies `type` and `required`. Strings also require `max_length` and a reviewed `pattern`; integers require `minimum` and `maximum`; an `enum` can narrow the accepted values. Enum members must match the declared scalar type; booleans never stand in for integers. The implementation checks parameter names, scalar types, and required flags against the pinned OpenAPI document. At call time, the value must satisfy **both the local rule and the supported constraints from the pinned request schema**: `enum`, integer `minimum`/`maximum`, string `minLength`/`maxLength`, and `pattern`. The tool's advertised schema includes both sets of constraints.

String enum members in local rules and supported OpenAPI schemas are capped at 256 characters, matching the adapter's maximum supported string input. The aggregate `tools/list` result is capped at 256 KiB of serialized ASCII-safe JSON, excluding the JSON-RPC envelope and request ID. Configuration fails at startup if expanded schemas exceed this cap, including repeated local `$ref` definitions or Unicode escaping; it does not start with a truncated or incomplete tool schema.

This is **not a complete OpenAPI or JSON Schema validator**. Request schema combinations, `format` (including date/date-time formats), nullable values, exclusive bounds, array/object parameters, and other unsupported schema keywords fail configuration rather than being silently ignored. Local `$ref` chains are bounded and resolved; external references and validation keywords beside a `$ref` are refused. Response projection fields are operator-reviewed mappings, **not automatically proved against the full OpenAPI response schema**.

### Supported validation patterns

Configured patterns use a small finite-state matcher with no backtracking. It accepts sequences of literals, dot, character classes/ranges and negated classes, escaped punctuation, ASCII `\d`/`\D`/`\w`/`\W`, and `\n`/`\r`/`\t`/`\f`/`\v` escapes. A single atom can use `?`, `*`, `+`, `{m}`, `{m,n}`, or `{m,}`. Optional `^` and `$` anchors are allowed only at the beginning and end. Dot excludes CR, LF, U+2028 and U+2029. Actual query and returned string values must also pass the adapter's control-character checks.

Groups, alternation, lookarounds, backreferences, lazy/possessive quantifiers, whitespace-category escapes (`\s`/`\S`), Unicode-category escapes, and other syntax are rejected during configuration. Patterns are capped at 256 characters, repetition counts at 256, the compiled automaton at 512 states, and matched values at 256 characters. These bounds and state-based evaluation prevent catastrophic regex backtracking, including on hostile model-supplied account IDs. OpenAPI patterns use substring-search semantics; local request and output patterns require full matches. This deliberately restricted language does not claim complete JSON Schema regular-expression support.

Common account-ID patterns such as `^[a-z0-9-]+$` and `[A-Za-z0-9_.-]{1,64}` are supported. If the real contract needs unsupported syntax, leave the operation disabled until the matcher or contract is deliberately adapted and reviewed; do not weaken the pattern merely to make configuration pass.

Each network tool call also has a deterministic budget of **2,097,152 validation work units**, shared by its request and response patterns. Before matching, each candidate string is charged `max(1, string length)` multiplied by the compiled automaton's state count plus the total possible atom-comparison cost across all transitions; a character class counts its own comparison and every member comparison. This is a conservative upper estimate, so an early match or failure does not refund work. All query patterns are budgeted before request matching, and all response patterns are budgeted before response matching. Response records beyond `max_records` still count because their fields are validated. Every record's customer and cluster scope is checked before response pattern budgeting. If the budget is exceeded, the complete result fails with a short error; narrow the upstream query or the reviewed projection. This limits accumulated matching work across large lists without claiming a whole-request wall-clock deadline.

Each output field specifies a scalar `pointer`, `type`, and optional `required`. Strings require a bounded `max_length` and a reviewed `pattern`; optional `enum` restricts values further. An output field named `account_id`, for example, must point to the **actual documented identifier field**, not a guessed property. The synthetic field names in the unit tests are test fixtures, not an Objectify integration contract.

Then validate without making a network request:

```bash
python3 connections/objectify/launch.py --check
```

Nothing to register: the plugin's `objectify` server runs `connections/objectify/launch.py`, which uses
`config.local.json` when it exists on the machine (it is ignored by git) and the disabled example otherwise.

The process inherits the named credential variable. Do not include the credential itself in a shared MCP configuration. After connecting, inspect `objectify_status`, confirm the bound context, and conduct a single approved metadata read before wider team rollout.

## Customer and cluster boundaries

The process binds one `customer_id`, `cluster_id`, and `environment` at startup. Every network tool requires the exact customer and cluster aliases again. Mismatches fail before the HTTP request. The model cannot supply a URL, HTTP method, headers, arbitrary query keys, or a path.

The upstream service must enforce the same boundary with its credential and routing. If one credential can inspect multiple customers, changing aliases in this adapter does not make it isolated. Use separate scopes or a server-side authorization gateway before enabling access. For stronger workstation separation, run customer processes under separate OS users/containers and separate credential stores; instructions alone do not isolate local filesystem access.

The adapter verifies every returned record's customer and cluster markers, including individual-account, backend, and EPG responses and list records beyond the output limit. A missing marker or mismatch fails the entire result. It never silently filters a global customer dump into an apparently safe answer.

These checks do **not** yet compare a requested logical account ID with a returned account ID. That mapping depends on the actual Objectify contract. Internal acceptance must prove that account requests resolve to the intended RGW user or StorageGRID tenant, and add an explicit request-to-response identity check when the contract exposes the required fields. A response from the correct customer and cluster can still describe the wrong account.

## Request and response safeguards

- HTTPS verification is mandatory. A custom CA file is supported; disabling certificate checks is not.
- Redirects are refused, and environment proxy settings are ignored. Credentials are sent only to the configured origin and fixed path.
- `timeout_seconds` configures a socket I/O timeout plus a separate body-phase deadline, each 1–30 seconds; the default is 10 seconds. **It is not an end-to-end wall-clock deadline**: DNS resolution and slow response headers can exceed it. Enforce an external process/network timeout where a hard deadline is required. Response bytes are capped at 1 KiB–8 MiB, with 1 MiB as the default.
- Account output is capped at 100 records at most, 50 by default. `locally_truncated` reports only whether this adapter omitted records from the received response. `upstream_completeness` remains `"unknown"`, even if an unreviewed upstream `has_more`, cursor, or total-count field appears. Use a bounded upstream query where the real API offers one. There is no implemented upstream pagination contract, automatic page traversal, or retry loop.
- Each successful MCP tool-result object is capped at **256 KiB of serialized ASCII-safe JSON**, including both `content` and `structuredContent` and the escaping needed on the wire. This cap excludes the small JSON-RPC envelope and the echoed client request ID. If a reviewed projection repeats fields, returns large numeric values, or expands through Unicode escaping beyond the cap, the adapter returns a short tool error without any partial records. Narrow the projection or lower `max_records`; the adapter does not silently omit fields to make the result fit.
- Responses must be JSON. Nesting is capped at 64 containers before parsing, for stdio messages, configuration/specification files, and API responses. Non-finite numbers, including exponent overflow, and escaped lone Unicode surrogates are rejected. Malformed input produces an error; a later valid stdio message can still be processed. Compressed bodies, unexpected types, missing required fields, and schema/scope mismatches fail closed.
- Only approved scalar fields are returned. Field names and JSON Pointer segments containing credential/key markers are prohibited. Known credential patterns and a reflected configured token are redacted.
- This projection is deliberately conservative, but pattern matching is not a complete secret detector. The service owner must review the selected fields; arbitrary secrets placed in an innocently named field cannot always be identified automatically.
- Raw bodies, error bodies, URLs, headers, tokens, and stack traces are not emitted to the model. No API payloads are written to disk by the adapter.

## Protocol compatibility and validation limits

The server implements a small **legacy stdio MCP** subset: `initialize`, the initialized notification, `ping`, `tools/list`, and `tools/call`. Its only supported protocol revision is **`2025-11-25`**. Initialize requests proposing older or newer revisions receive a `2025-11-25` counteroffer; the client must accept that revision or disconnect. The server does not claim compatibility with the `2025-03-26` batching requirement. `server/discover` returns method-not-found so clients with legacy fallback can use the handshake. Native modern-only MCP clients are unsupported. Error responses preserve readable request IDs and omit the ID when it cannot be read, as allowed by the supported revision.

It emits newline-delimited JSON-RPC on stdout and does not run an HTTP MCP listener. Standard object-valued `_meta` request metadata is accepted, including on `tools/list`; metadata is not sent to Objectify. Tools are advertised as read-only only after the local contract gates pass; protocol annotations are descriptive and do not replace the adapter's enforcement. Requests are processed sequentially; no sampling, prompts, resources, elicitation, tasks, or in-flight cancellation are claimed. Use the client's process supervision and an external hard timeout when a stalled DNS lookup or slow headers must not hold the session.

The protocol choices follow the official [legacy lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle), [stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports), and [tool interface](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) specifications, inspected on 2026-11-09.

Local tests cover contract pinning, response context checks for all operations, mutation and parlay rejection, supported OpenAPI constraints, exact scalar enum typing and string bounds, finite-state pattern behavior and aggregate work budgets, hostile-pattern/value rejection, output projection, serialized result and discovery limits including Unicode expansion, redaction, byte limits, redirect refusal with a loopback server, unknown upstream completeness, nested/Unicode malformed-input recovery, standard request metadata, and real subprocess stdio exchanges. **They do not establish end-to-end compatibility with your Claude Code build, real authentication, Objectify authorization, or production schemas.** Those require internal acceptance tests using the completed contract and read-only credentials.
