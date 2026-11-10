# SDS brain

Turns Claude Code into the SDS team's object-storage assistant: Ceph / RGW, S3, NetApp StorageGRID, the RHEL hosts and
HPE servers under them, Grafana and Elasticsearch. It knows the team's rules, searches the vendor documentation
offline, follows the team's investigation procedures, and writes down what it learns for everyone. Read-only toward
infrastructure by design.

## Start
Needs: Claude Code, `python3` 3.9 or newer, `git`. Linux, macOS or WSL.

```bash
git clone <this repository's url> sds-brain
cd sds-brain
claude
```
The first time, Claude Code asks whether you trust the folder (it has hooks and MCP servers): answer yes. Then type
`/brain-setup` once: Claude asks about your clusters and grids and fills `knowledge/environment.md`.

Always start `claude` from this folder: the rules, skills, hooks and connections are this folder's.

## What is inside
| Part | Where | What it does |
|---|---|---|
| Rules | `CLAUDE.md` | Who the team is and 9 golden rules: read-only, never invent, backend and version first, no secrets, search the docs, investigate by layers, memory, token economy |
| Environment | `knowledge/environment.md` | Your clusters, grids, servers, monitoring. Loaded in every session |
| Skills | `.claude/skills/` | 19 investigation procedures (Ceph health, slow ops, daemons, RGW, multisite, S3 403 / signature / latency / multipart, StorageGRID capacity / ILM / connectivity / quota, host pressure / network / SELinux, hardware, Grafana, Elasticsearch) plus `brain-learn`, `docs-lookup`, `brain-setup`. Claude picks them by itself, or call `/<name>` |
| Docs library | `docs/` | StorageGRID 11.8 / 11.9 / 12.0 complete, Ceph Squid / Reef, IBM Storage Ceph, AWS S3, Grafana, Prometheus, Elasticsearch, HPE iLO. Searched offline by the `sds-docs` server. See `LIBRARY.md` |
| Team knowledge | `knowledge/` | `notes.md` (core facts), `notes/<topic>.md` (dated facts and pages), `runbooks/` (change procedures you ran and confirmed), `captures/` (drafts), `incidents/` (postmortems) |
| Hooks | `.claude/hooks/` | Session start (sync + status), the read-only guard, save-and-share of notes with a secret scan, a reminder to capture after a long session |
| Connections | `connections/` | Grafana (bundled, read-only), Objectify (status only until its API contract is supplied), Red Hat offline portal (optional) |

## How the team shares knowledge
Nothing to do by hand. When Claude saves a file under `knowledge/`, a hook checks it for keys and passwords, commits
it and pushes it to this repository's remote; every session start pulls. Two people adding facts to the same file at
once are merged automatically. Each person needs push access to the repository and a git identity
(`git config user.name` / `user.email`); without them the login name is used.

- "Remember that ..." or a solved problem: Claude writes a dated fact, or a capture when it is not sure.
- "Curate the captures": Claude proposes what to promote, merge or discard; you decide.
- "Save this as a runbook": after you ran a change and it worked.
- "Write a postmortem": an incident report under `knowledge/incidents/`.

## Connections
- **Docs**: works out of the box. The index is built on first start (a few seconds).
- **Grafana**: set `SDS_GRAFANA_URL` and `SDS_GRAFANA_TOKEN` (a Viewer service-account token) in your shell profile:
  `connections/grafana/README.md`. Until then Claude says it is not configured.
- **Objectify**: reports status only. To enable reads, supply the API's OpenAPI file: `connections/objectify/README.md`.
- **Red Hat offline portal** (RHCS and RHEL manuals, knowledge base): optional, one command to connect:
  `connections/okp/README.md`.

## The biggest gap: Red Hat manuals
The Red Hat Ceph Storage and RHEL documentation is **not** in the library (Red Hat's site refused the download when
it was assembled). Either connect the offline portal, or put the manuals (PDF or HTML) under `docs/redhat/<product>/`
and commit: see `LIBRARY.md`. Until then Claude says when an answer needs them.

## Read-only
Claude never changes Ceph, RGW, StorageGRID, S3 data, hosts or hardware: it gives you the commands to run, with
pre-checks and rollback. A guard hook blocks changing commands (also inside `ssh`, `cephadm shell`, `podman exec`)
and commands that print keys. It is a net against mistakes, not a wall: read-only accounts on every backend are the
real guarantee. A read command blocked by mistake: add its beginning to `.claude/hooks/guard-allow.txt`.

Web access is switched off in `.claude/settings.json` (the network is internal). If your machines do reach the
internet and you want it, remove `WebFetch` and `WebSearch` from `deny` there.

## Changing the brain
People change the rules (`CLAUDE.md`), skills, hooks and tools with normal commits; Claude is blocked from editing the
rules, hooks, tools and connections, and writes only under `knowledge/` (and `docs/` when you ask it to add a
document). Before pushing a change by hand:

```bash
python3 tools/check.py        # JSON, skills, hooks, no secrets in knowledge, runbook sections, archives
python3 tools/test_brain.py   # the guard (117 commands), save and sync, docs search, connections: about 20 s
```
`.gitlab-ci.yml` runs both on every push (point its `image` at your internal registry).

## Try it
- `the cluster shows HEALTH_WARN with PG_DEGRADED and slow ops, where do I start?`
- `S3 PUT to bucket X returns SignatureDoesNotMatch since yesterday`
- `Low metadata storage alert on the grid, what does it mean on 11.9?`
- `what changed in S3 between StorageGRID 11.9 and 12.0?`
- `which ILM policy applies to bucket Y?`  ·  `/sg-ilm-backlog`  ·  `/ceph-health`

## Credits
The search engine in `tools/engine/` comes from the storage team's SAN brain (docs-search server). The Grafana MCP
server in `connections/grafana/vendor/` is Grafana Labs' official release v2.2.0 (Apache-2.0, license beside it).
The documentation under `docs/` belongs to its publishers (`LIBRARY.md`).
