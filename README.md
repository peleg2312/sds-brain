# SDS brain

Turns Claude Code into the SDS team's object-storage assistant: Ceph / RGW, S3, NetApp StorageGRID, the RHEL hosts and
HPE servers under them, Grafana and Elasticsearch. It knows the team's rules, searches the vendor documentation
offline, follows the team's investigation procedures, and writes down what it learns for everyone. Read-only toward
infrastructure by design.

The same structure as the storage team's brains: one team repository holding the plugin, the rules and the knowledge.

```
.claude-plugin/marketplace.json   what makes this repository installable in Claude Code
brain-sds/                        the plugin: skills/ (22), agents/, hooks/, .mcp.json, team.json, tools/
rules/                            main.md (golden rules), persona.md, storage.md (identity, versions, evidence, each
                                  domain), guard-allow.txt: the team's own, loaded every session
knowledge/                        environment.md, notes.md, tool-map.md (loaded every session), notes/, runbooks/,
                                  captures/, incidents/, INDEX.md (generated): what the team learns
templates/                        topic, capture, page, runbook, incident, metric: copied into knowledge/
docs/                             the vendor documentation the library is built from (LIBRARY.md)
connections/                      Grafana (bundled, read-only), Objectify, Red Hat offline portal (okp); http/: the
                                  images; openshift/: the same as pods
join.sh  vm-setup.py  check.py  test_brain.py
```

## Start (each person, once)
Needs: Claude Code, `python3` 3.9 or newer, `git`. Linux, macOS or WSL.

```bash
git clone <this repository's url> sds-brain
sh sds-brain/join.sh
claude                                  # in any folder
```
`join.sh` links the clone as `~/.claude/sds-brain` (the brain's home), installs the plugin `brain-sds` from it and adds
one import line to `~/.claude/CLAUDE.md` so every session loads `rules/main.md`. Nothing else on the machine changes;
`sh join.sh --leave` undoes it. Keep the clone where it is (after moving it, run `join.sh` again).

The first time, type `/brain-sds:brain-setup`: Claude asks about your clusters and grids and fills
`knowledge/environment.md` for the whole team.

**Or straight from the marketplace**, without cloning first:
```bash
claude plugin marketplace add <this repository's git url>
claude plugin install brain-sds@brain-sds
```
The first session clones the team repository as `~/.claude/sds-brain` in the background and adds the import line
(that session gets the rules from the marketplace copy); from the second session on it is the same as after
`join.sh`. `join.sh` is still the way to trust the VM's HTTPS certificate on a machine without it.

## Docs: the VM's docs service, or each machine by itself
Two MCP servers and two hooks, as in the storage team's brains:

- **docs-http**: the docs service on the VM (the storage brain's `paas-docs`). It serves SDS its own library and the
  team's knowledge, over HTTPS with the service's token. Nothing is built on a member's machine.
- **docs-local**: the plugin's small server. It indexes the team's knowledge on the person's machine at every start,
  so a note written a minute ago is found. Without a VM it also indexes `docs/` locally (a few seconds, once). On the
  VM itself it opens the docs service's own index of the team's knowledge (`/var/lib/paas-docs/index/sds.db`) when it
  matches the clone, instead of building one per person.
- **docs-leads** (each request): the best matching documents and the meaning of pasted identifiers, before Claude
  answers. **docs-hints** (each result of a shell command or MCP tool): the meaning of the Ceph health checks
  (`PG_DEGRADED`), S3 error codes (`SignatureDoesNotMatch`) and error messages it shows. Both search the local index,
  else docs-http, and stay silent when nothing matches well.

To connect the VM, once, as root on the VM, from a clone whose `origin` is the team's git url:

```bash
sudo python3 vm-setup.py                # then commit and push the two files it names
```
It copies `docs/` into the VM's libraries (`/opt/paas/libraries/sds`) and builds the index there, registers the team
`sds` with the docs service (which then keeps the team's own small knowledge index, refreshed every 10 minutes and
right after each push), and writes the service's address and token into `brain-sds/.mcp.json`:
```json
"docs-http": {"type": "http", "url": "https://<vm>:8443/mcp?team=sds", "headers": {"Authorization": "Bearer <the docs token>"}}
```
That entry is not in the repository until `vm-setup.py` has run: the address and the token exist only on the VM. After the push every member has `docs-http` at their next session. The other teams
on the VM are not touched. Until then, and on a network without that VM, the brain works with `docs-local` alone.

## How the team shares knowledge
Nothing to do by hand. When Claude saves a file under `knowledge/`, a hook checks it for keys and passwords, commits
it and pushes it to this repository's remote; every session start pulls. Two people adding facts to the same file at
once are merged automatically. Each person needs push access to the repository and a git identity
(`git config user.name` / `user.email`); without them the login name is used.

- "Remember that ..." or a solved problem: Claude writes a dated fact, or a capture when it is not sure.
- "Curate the captures": Claude proposes what to promote, merge or discard; you decide.
- "Save this as a runbook": after you ran a change and it worked (`knowledge/runbooks/`, empty until then).
- "Write a postmortem": an incident report under `knowledge/incidents/`.

Each of these starts from a file in `templates/` (`templates/README.md` says which is for what); you can copy one by
hand too.

The 19 investigation procedures (Ceph health, slow ops, daemons, RGW, multisite, S3 403 / signature / latency /
multipart, StorageGRID capacity / ILM / connectivity / quota, host pressure / network / SELinux, hardware, Grafana,
Elasticsearch) are skills in `brain-sds/skills/`: Claude picks them by itself, or call `/brain-sds:<name>`.

## Connections
- **Grafana**: set `SDS_GRAFANA_URL` and `SDS_GRAFANA_TOKEN` (a Viewer service-account token) in your shell profile:
  `connections/grafana/README.md`. Until then Claude says it is not configured.
- **Objectify**: reports status only. To enable reads, supply the API's OpenAPI file: `connections/objectify/README.md`.
- **Red Hat offline portal** (RHCS and RHEL manuals, knowledge base): the plugin's `okp` server. Set `SDS_OKP_URL`
  (or the team's url in `connections/okp/config.json`): `connections/okp/README.md`.
- **Objectify**: the full contract for enabling reads is `connections/objectify/INTEGRATION.md`.
- **Once for everyone**: every MCP server (docs, Grafana, Objectify, okp) can run as a container that serves HTTP, so
  nobody needs their own index, token or configuration: on OpenShift (`connections/openshift/README.md`) or with
  Podman on the VM (`connections/http/README.md`); `use.py` points the plugin at them.

## The biggest gap: Red Hat manuals
The Red Hat Ceph Storage and RHEL documentation is **not** in the library (Red Hat's site refused the download when
it was assembled). Either connect the offline portal, or put the manuals (PDF or HTML) under `docs/redhat/<product>/`
and commit: see `LIBRARY.md`. Until then Claude says when an answer needs them.

## Read-only
Claude never changes Ceph, RGW, StorageGRID, S3 data, hosts or hardware: it gives you the commands to run, with
pre-checks and rollback. The guard hook (`brain-sds/hooks/guard.py`), in every folder Claude is started in:
- **blocks** commands that change storage (`ceph`, `radosgw-admin`, `rados`, `rbd`, `cephadm`, `ceph-volume` beyond a
  list of read commands; S3 writes and deletes with `aws`, `s3cmd`, `mc`, `s5cmd`, `rclone`; HPE `ilorest`, `ipmitool`,
  `ssacli`, `storcli`, `smartctl` tests), host changes on a remote machine, and commands that print keys
  (`radosgw-admin user info` without a `jq` projection), also inside `ssh`, `cephadm shell`, `podman exec`, `bash -c`,
  `sudo`, `timeout`, `watch` and `$(...)`;
- **asks you** for `curl` / `wget` writes to another host, a change on this machine, a remote command it does not know;
- **blocks** MCP tools whose names say they change something (`update_dashboard`, `create_incident`...);
- **blocks** Claude's writes to the brain itself (rules, plugin, connections, `join.sh`): only `knowledge/` and
  `docs/` are Claude's;
- **approves** without a prompt the brain's own read-only tools (docs, Grafana reads, Objectify status, OKP search),
  notes saved under `knowledge/`, and the shell docs search. It is a net against mistakes, not a wall:
read-only accounts on every backend are the real guarantee. A read command blocked by mistake: add its beginning to
`rules/guard-allow.txt` and push.

## Changing the brain
People change the rules (`rules/`), skills, hooks and tools with normal commits; Claude is blocked from editing
anything in this repository except `knowledge/` (and `docs/` when you ask it to add a document). A pushed change
reaches everyone at their next session: rules and knowledge at once, a changed skill or hook at the latest one session
later (where Claude Code keeps its own copy of the plugin, the brain updates that copy in the background). To try a plugin change before committing: `claude --plugin-dir ./brain-sds`.
Before pushing:

```bash
python3 check.py        # JSON, plugin shape, skills, hooks, rules length, no secrets in knowledge, runbook sections, archives
python3 test_brain.py   # the guard, save and sync, docs leads / hints, marketplace install, join.sh, the VM docs service, OKP: about 30 s
```
`.gitlab-ci.yml` runs both on every push (point its `image` at your internal registry).

## Try it
- `the cluster shows HEALTH_WARN with PG_DEGRADED and slow ops, where do I start?`
- `S3 PUT to bucket X returns SignatureDoesNotMatch since yesterday`
- `Low metadata storage alert on the grid, what does it mean on 11.9?`
- `what changed in S3 between StorageGRID 11.9 and 12.0?`
- `which ILM policy applies to bucket Y?`  ·  `/brain-sds:sg-ilm-backlog`  ·  `/brain-sds:ceph-health`

## Credits
The search engine in `brain-sds/tools/engine/` is the storage team's docs-search server, unchanged: the same code the
VM's docs service runs. The Grafana MCP server in `connections/grafana/vendor/` is Grafana Labs' official release
v2.2.0 (Apache-2.0, license beside it). The documentation under `docs/` belongs to its publishers (`LIBRARY.md`).
