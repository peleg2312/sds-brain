#!/usr/bin/env python3
"""Tests of the brain's plugin (hooks, docs-local, connections), join.sh, vm-setup.py and check.py, in temporary copies:
nothing here, in ~/.claude or on a VM is changed, and Claude Code itself is replaced by a stand-in. Standard library.
    python3 test_brain.py          exits 1 on the first failure (about 40 s)"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
PLUGIN = "brain-sds"
ENV = {k: v for k, v in os.environ.items() if not k.startswith(("SDS_", "GIT_", "PAAS_", "CLAUDE"))}
ENV["PAAS_LIBRARIES"] = os.path.join(os.sep, "nonexistent")       # on the VM itself: its installed library is not part of the test


def hook(script, payload, cwd=ROOT, env=None, root=ROOT):
    """run a hook of the plugin in `root` (a team repository, or a bare plugin copy with root=<its parent>)"""
    r = subprocess.run([sys.executable, os.path.join(root, PLUGIN, "hooks", script)], input=json.dumps(payload),
                       capture_output=True, text=True, cwd=cwd, env=env or ENV, timeout=60)
    return r.returncode, r.stdout, r.stderr


def guard(tool, cwd=ROOT, root=ROOT, env=None, **inp):
    rc, out, err = hook("guard.py", {"tool_name": tool, "tool_input": inp, "cwd": cwd}, root=root, env=env)
    return "block" if rc == 2 else "ask" if '"ask"' in out else "approve" if '"allow"' in out else "allow"


# ---- 1. the read-only guard
ALLOW = """ceph -s
ceph fsid
ceph health detail --format json
ceph versions
ceph quorum_status --format json
ceph osd stat
ceph pg stat
ceph df --format json
ceph osd tree --format json | jq -e '{nodes:(.nodes|length),sample:(.nodes[0:40]|map({id,name,type,status}))}'
ceph osd perf | sed -n '1,41p'
ceph pg dump_stuck inactive --format json | jq -e 'if type=="object" then .stuck_pg_stats else error("x") end'
ceph pg 2.1f query
ceph config get osd.12 osd_op_queue
ceph orch ps --service-name rgw.main --daemon-id rgw.main.host1.abc --format json
ceph orch ls --service_name=rgw.main
ceph tell osd.3 perf dump
ceph daemon osd.3 dump_historic_ops
sudo ceph osd df
timeout 20 ceph status
watch -n 5 ceph -s
cephadm shell -- ceph osd tree
cephadm ls
ssh node1 'ceph health detail'
ssh -p 2222 admin@node1 "ceph osd tree | grep down"
ssh node1 "journalctl -u ceph-abc@osd.3 --since '1 hour ago' --no-pager -n 200" > /tmp/osd3.log 2>&1
ssh node1 uptime
ssh node1 'systemctl show ceph.target -p ActiveState'
ssh node1 "podman container inspect abc --format '{{.Image}}'"
podman exec ceph-mon-a ceph -s
radosgw-admin sync status
radosgw-admin metadata sync status
radosgw-admin data sync status --source-zone us-east
radosgw-admin bucket stats --bucket=logs
radosgw-admin user info --uid='t$u' | jq -e '{user_id,tenant,suspended,max_buckets,user_quota,bucket_quota}'
rados df
rbd ls
aws --profile p --endpoint-url https://s3.x --region r --cli-connect-timeout 5 s3api head-bucket --bucket b
aws --profile p --endpoint-url https://s3.x s3api list-multipart-uploads --bucket b --prefix x --max-uploads 20 --no-paginate
aws --endpoint-url https://s3.x s3 ls s3://bucket/
s3cmd ls s3://b
ilorest get --select ComputerSystem.
ipmitool sdr list
ipmitool chassis status
smartctl -a /dev/sda
curl -sk https://grid.example/api/v3/grid/health
curl -s -X POST https://es.example:9200/rgw-*/_search -H 'Content-Type: application/json' -d '{"size":1}'
curl -X POST http://localhost:8080/test -d x
chronyc tracking
vmstat 1 5
iostat -xz 1 5
getenforce; sestatus
ls -Zd -- /var/lib/ceph
rm /tmp/scratch.txt
python3 some_script.py --flag
cat rules/main.md
cp rules/main.md /tmp/rules-copy.md
grep -ri srdf knowledge/notes > /tmp/hits.txt
git status""".splitlines()
BLOCK = """ceph osd out 12
ceph osd set noout
ceph osd pool delete p p --yes-i-really-really-mean-it
ceph osd reweight 3 0.8
ceph pg repair 2.1f
ceph pg deep-scrub 2.1f
ceph config set osd osd_max_backfills 4
ceph orch daemon restart rgw.main.host1.abc
ceph orch apply -i spec.yaml
ceph orch ls --export
ceph health mute OSD_DOWN
ceph auth get client.admin
ceph tell osd.* injectargs --osd_max_backfills 4
sudo ceph osd purge 3 --yes-i-really-mean-it
cephadm shell
cephadm shell -- ceph osd out 3
cephadm rm-daemon --name osd.3 --fsid abc
ssh node1 'ceph osd out 3'
ssh node1 "ceph osd tree | grep down; ceph osd set noout"
ssh node1 'systemctl restart ceph-abc@osd.3.service'
ssh node1 sudo reboot
ssh node1 'setenforce 0'
ssh node1 "echo 1 > /proc/sys/vm/drop_caches"
ssh node1 'dnf install -y sysstat'
bash -c 'ceph osd out 3'
echo $(ceph osd out 3)
podman exec ceph-mon-a ceph osd out 3
radosgw-admin user info --uid=bob
radosgw-admin user create --uid=bob --display-name=Bob
radosgw-admin key create --uid=bob
radosgw-admin zone get
radosgw-admin bucket rm --bucket=logs --purge-objects
radosgw-admin period update --commit
radosgw-admin quota set --quota-scope=user --uid=bob --max-size=1G
rados -p data rm obj1
rados bench -p data 10 write
rbd rm pool/img
aws --endpoint-url https://s3.x s3 rm s3://bucket/key
aws --endpoint-url https://s3.x s3 cp file s3://bucket/key
aws --endpoint-url https://s3.x s3 presign s3://bucket/key
aws --endpoint-url https://s3.x s3api delete-object --bucket b --key k
aws --endpoint-url https://s3.x s3api put-bucket-policy --bucket b --policy file://p.json
s3cmd del s3://b/k
mc rm --recursive --force alias/bucket
ilorest reboot
ipmitool chassis power cycle
smartctl -t long /dev/sda
ssacli ctrl slot=0 ld 1 delete
echo x >> rules/main.md
sed -i 's/Read-only/Read-write/' rules/main.md
rm brain-sds/hooks/guard.py
cp /tmp/evil.py brain-sds/tools/brainlib.py
echo 'ceph *' > rules/guard-allow.txt
git checkout -- brain-sds/hooks/hooks.json
mv join.sh /tmp/join.sh""".splitlines()
ASK = """curl -X POST https://grid.example/api/v3/authorize -d '{"username":"x"}'
curl -X DELETE https://objectify.example/account/obj_acc
ssh node1 'some-unknown-tool --flag'
systemctl restart ceph.target
sudo reboot""".splitlines()
for want, cmds in (("allow", ALLOW), ("block", BLOCK), ("ask", ASK)):
    for c in cmds:
        got = guard("Bash", command=c)
        assert got == want, f"guard: expected {want}, got {got}: {c}"
for path, want in (("rules/main.md", "block"), ("rules/guard-allow.txt", "block"), ("brain-sds/hooks/guard.py", "block"),
                   ("brain-sds/hooks/hooks.json", "block"), ("brain-sds/tools/docs_server.py", "block"), ("brain-sds/.mcp.json", "block"),
                   ("brain-sds/skills/ceph-health/SKILL.md", "block"), ("connections/grafana/launch.py", "block"),
                   ("join.sh", "block"), (".claude-plugin/marketplace.json", "block"), (".git/config", "block"),
                   ("templates/runbook.md", "block"),
                   ("knowledge/notes/ceph.md", "approve"), ("knowledge/captures/2026-11-10-x.md", "approve"),
                   ("knowledge/environment.md", "approve"), ("docs/redhat/rhcs-8.1/notes.md", "allow"),
                   ("/tmp/elsewhere/main.md", "allow")):
    got = guard("Write", file_path=path if path.startswith("/") else os.path.join(ROOT, path), content="x", cwd="/tmp")
    assert got == want, f"guard: Write {path}: expected {want}, got {got}"
OWN = "mcp__plugin_brain-sds_"
for tool, want in ((OWN + "docs-local__search_docs", "approve"), (OWN + "docs-http__read_chunk", "approve"),
                   (OWN + "grafana__query_prometheus", "approve"), (OWN + "grafana__list_datasources", "approve"),
                   (OWN + "grafana__update_dashboard", "block"), (OWN + "grafana__create_incident", "block"),
                   (OWN + "objectify__objectify_status", "approve"), (OWN + "objectify__objectify_get_account", "approve"),
                   (OWN + "objectify__resize_account", "block"), (OWN + "okp__search_documentation", "approve"), ("mcp__sds-okp__search_documentation", "allow"),
                   ("mcp__other__delete_volume", "block")):
    assert guard(tool) == want, f"guard: {tool}: expected {want}, got {guard(tool)}"
# the docs search without MCP is approved only as the whole command
SEARCH = os.path.join(ROOT, PLUGIN, "tools", "search.py")
assert guard("Bash", command=f'python3 {SEARCH} "PG_DEGRADED" --product squid', cwd="/tmp") == "approve"
assert guard("Bash", command=f"python3 {SEARCH} x; ceph osd out 3", cwd="/tmp") == "block"
assert guard("Bash", command=f"python3 {SEARCH} x > /tmp/out.txt", cwd="/tmp") == "allow"
print(f"guard ok ({len(ALLOW)} allowed, {len(BLOCK)} blocked, {len(ASK)} asked)")


# ---- 2. two people, one team repository: notes are saved, shared, merged; secrets stay out
def sh(*cmd, cwd=None, check=True):
    r = subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True, env=ENV, timeout=120)
    assert not check or r.returncode == 0, (cmd, r.stdout, r.stderr)
    return r.stdout.strip()


work = tempfile.mkdtemp(prefix="sds-brain-test-")
ENV["TMPDIR"] = work                  # the hooks' once-per-session files: this run's own, never a previous run's
try:
    bare, alice, bob = (os.path.join(work, n) for n in ("remote.git", "alice", "bob"))
    shutil.copytree(ROOT, alice, ignore=shutil.ignore_patterns(".git", ".cache", "__pycache__"))
    sh("git", "init", "-q", "--bare", "-b", "main", bare)
    sh("git", "init", "-q", "-b", "main", alice)
    for k, v in (("user.name", "alice"), ("user.email", "alice@example.test")):
        sh("git", "config", k, v, cwd=alice)
    sh("git", "add", "-A", cwd=alice); sh("git", "commit", "-qm", "SDS brain: test copy", cwd=alice)
    sh("git", "remote", "add", "origin", bare, cwd=alice); sh("git", "push", "-qu", "origin", "main", cwd=alice)
    sh("git", "clone", "-q", bare, bob)
    for k, v in (("user.name", "bob"), ("user.email", "bob@example.test")):
        sh("git", "config", k, v, cwd=bob)

    def save(who, relpath, text, mode="w"):
        p = os.path.join(who, relpath)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, mode) as f:
            f.write(text)
        return hook("notes-save.py", {"tool_name": "Write", "tool_input": {"file_path": p}}, cwd=who, root=who)

    remote_log = lambda: sh("git", "log", "--format=%an %s", "main", cwd=bare)
    rc, out, _ = save(alice, "knowledge/notes/ceph.md", "# Ceph: clusters and quirks\n- 2026-11-10 · cluster prod-a nearfull ratio is 0.80 · verified · ceph osd dump\n")
    assert rc == 0 and out == "" and "alice brain: knowledge/notes/ceph.md" in remote_log(), (out, remote_log())
    index = sh("git", "show", "main:knowledge/INDEX.md", cwd=bare)          # regenerated in the same commit
    assert "[ceph.md](notes/ceph.md): Ceph: clusters and quirks (1 facts)" in index and "## Runbooks" in index, index
    # a secret: reported to Claude, nothing committed
    rc, out, _ = save(alice, "knowledge/captures/2026-11-10-keys.md", '# RGW user\n"secret_key": "wJalrXUtnFEMIK7MDENGbPxRfiCYEXAMPLEKEYab"\naccess AKIAIOSFODNN7EXAMPLE\n')
    msg = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "2 secret(s)" in msg and "wJalrXU" not in msg and "captures/2026-11-10-keys.md" not in remote_log(), msg
    os.remove(os.path.join(alice, "knowledge/captures/2026-11-10-keys.md"))
    # a file outside knowledge/ is never committed by the hook
    rc, out, _ = save(alice, "scratch.txt", "x")
    assert out == "" and "scratch.txt" in sh("git", "status", "--porcelain", cwd=alice)
    os.remove(os.path.join(alice, "scratch.txt"))

    # bob's session start pulls alice's note and names it
    rc, out, _ = hook("session-start.py", {}, cwd=bob, root=bob)
    assert rc == 0 and out.startswith(f"SDS brain: Home: {os.path.realpath(bob)} ") and "Team repository: in sync" in out, out
    assert "Docs: docs-local" in out and "docs-http" not in out, out
    assert "notes/ceph.md (1 facts): Ceph: clusters and quirks" in out and "notes/ceph-versions.md" in out, out
    assert "Team changes in the last 14 days: notes/ceph.md (alice); read" in out, out      # not the commit that built the brain
    assert "only the reported fleet summary" in out and "grafana not configured" in out, out

    # both add a fact to the same file at the same time: both lines reach the remote (merge=union), no conflict
    save(alice, "knowledge/notes/ceph.md", "- 2026-11-10 · alice's fact · observed · test\n", "a")
    save(bob, "knowledge/notes/ceph.md", "- 2026-11-10 · bob's fact · observed · test\n", "a")
    merged = sh("git", "show", "main:knowledge/notes/ceph.md", cwd=bare)
    assert "alice's fact" in merged and "bob's fact" in merged and "nearfull" in merged, merged
    rc, out, _ = hook("session-start.py", {}, cwd=alice, root=alice)
    assert "in sync" in out and "bob's fact" in open(os.path.join(alice, "knowledge/notes/ceph.md")).read(), out

    # a runbook and a capture are listed; the checks catch a runbook without its sections and a secret
    save(bob, "knowledge/runbooks/ceph-replace-osd-drive.md", "---\ntitle: Replace a failed OSD drive\narea: ceph\ntype: runbook\n"
         "applies_to: [rhcs-8.1z9]\nconfidence: verified\nlast_verified: 2026-11-10\nsources: [ceph-volume lvm list]\n---\n\n"
         "# Replace a failed OSD drive\n## Pre-checks\n## Procedure\n## Verification\n## Rollback\n")
    save(bob, "knowledge/captures/2026-11-10-slow-list.md", "# Bucket listing slow on prod-a\n## Symptom\nlisting takes 40 s\n")
    rc, out, _ = hook("session-start.py", {}, cwd=bob, root=bob)
    assert "runbooks: 1 tested procedures" in out and "ceph-replace-osd-drive" in out and "captures: 1 waiting" in out, out
    index = sh("git", "show", "main:knowledge/INDEX.md", cwd=bare)      # the title comes from the runbook's header
    assert "[ceph-replace-osd-drive.md](runbooks/ceph-replace-osd-drive.md): Replace a failed OSD drive" in index, index
    assert subprocess.run([sys.executable, "check.py"], cwd=bob, capture_output=True, text=True, env=ENV).returncode == 0
    with open(os.path.join(bob, "knowledge/runbooks/bad.md"), "w") as f:
        f.write("# Bad\n## Procedure\n")
    with open(os.path.join(bob, "knowledge/notes/ceph-old-page.md"), "w") as f:                  # a page with a broken header
        f.write("---\ntitle: Old page\narea: ceph\ntype: page\napplies_to: [rhcs-7.1]\nconfidence: sure\nlast_verified: 2026-11-10\nsources: [x]\n---\n# Old page\n")
    with open(os.path.join(bob, "knowledge/notes/leak.md"), "w") as f:
        f.write("# Leak\n- 2026-11-10 · password=Hunter2!x · observed · test\n")
    r = subprocess.run([sys.executable, "check.py"], cwd=bob, capture_output=True, text=True, env=ENV)
    assert r.returncode == 1 and "FAIL runbook knowledge/runbooks/bad.md" in r.stdout and "FAIL no secret in knowledge/notes/leak.md" in r.stdout, r.stdout
    assert "FAIL header knowledge/runbooks/bad.md" in r.stdout and "FAIL header confidence knowledge/notes/ceph-old-page.md" in r.stdout, r.stdout
    for x in ("knowledge/runbooks/bad.md", "knowledge/notes/leak.md", "knowledge/notes/ceph-old-page.md"):
        os.remove(os.path.join(bob, x))
    print("team sync, save hook and checks ok")

    # ---- 3. the capture nudge: once per long session without a save
    tr = os.path.join(work, "t.jsonl")
    with open(tr, "w") as f:
        f.write('{"type":"tool_use"}\n' * 25)
    rc, out, _ = hook("capture-nudge.py", {"session_id": "s1", "transcript_path": tr}, cwd=bob, root=bob)
    assert json.loads(out)["decision"] == "block", out
    assert hook("capture-nudge.py", {"session_id": "s1", "transcript_path": tr}, cwd=bob, root=bob)[1] == ""
    with open(tr, "a") as f:
        f.write('{"type":"tool_use","name":"Write","input":{"file_path":"%s/knowledge/notes/ceph.md"}}\n' % bob)
    assert hook("capture-nudge.py", {"session_id": "s2", "transcript_path": tr}, cwd=bob, root=bob)[1] == ""
    print("capture nudge ok")

    # ---- 4. the docs server: vendor docs and the team's knowledge in one search
    def mcp(args, calls, cwd, env=None):
        msgs = [{"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                                                                              "clientInfo": {"name": "test", "version": "1"}}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"}]
        msgs += [{"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": n, "arguments": a}} for i, (n, a) in enumerate(calls, 1)]
        msgs.append({"jsonrpc": "2.0", "id": 99, "method": "tools/list"})
        r = subprocess.run([sys.executable] + args, input="".join(json.dumps(m) + "\n" for m in msgs), capture_output=True, text=True,
                           cwd=cwd, env=env or ENV, timeout=180)
        out = {}
        for line in r.stdout.splitlines():
            try:
                m = json.loads(line)
            except ValueError:
                continue
            out[m.get("id")] = m.get("result")
        assert 0 in out and 99 in out, (r.stdout[-400:], r.stderr[-400:])
        return out

    text = lambda res: json.loads(res["content"][0]["text"])
    o = mcp([PLUGIN + "/tools/docs_server.py"], [("search_docs", {"query": "PG_DEGRADED", "limit": 3}),
                                       ("search_docs", {"query": "ILM policy tag default policy", "product": "storagegrid-119", "limit": 3}),
                                       ("search_docs", {"query": "nearfull ratio prod-a", "limit": 3}),
                                       ("search_docs", {"query": "bucket listing slow prod-a", "limit": 3}),
                                       ("list_sources", {})], cwd=bob)
    assert [t["name"] for t in o[99]["tools"]] == ["search_docs", "read_chunk", "read_document", "related_docs", "list_sources"]
    hit = text(o[1])["results"][0]
    assert hit["section"] == "PG_DEGRADED" and hit["url"].startswith("https://docs.ceph.com/"), hit
    hit = text(o[2])["results"][0]
    assert hit["product"] == "storagegrid-119" and hit["url"].startswith("https://docs.netapp.com/us-en/storagegrid-119/ilm/"), hit
    hit = text(o[3])["results"][0]                 # one fact of the team's notes, not the whole file
    assert hit.get("library") == "team knowledge" and "nearfull" in json.dumps(hit) and "bob's fact" not in json.dumps(hit), hit
    hit = text(o[4])["results"][0]
    assert hit.get("library") == "team knowledge" and "Unverified capture" in json.dumps(hit), hit
    src = json.dumps(text(o[5]))
    assert "storagegrid-118" in src and "storagegrid-120" in src and "squid" in src, src[:400]
    r = subprocess.run([sys.executable, PLUGIN + "/tools/search.py", "SignatureDoesNotMatch", "--limit", "2"], cwd=bob, capture_output=True, text=True, env=ENV)
    assert r.returncode == 0 and "aws/s3" in r.stdout, r.stdout[:300]
    # the first SDS brain's library checks: each query's best hit comes from the right product (and release)
    GOLDEN = [("BLUEFS_SPILLOVER db partitions metadata", "", "ceph/"), ("radosgw-admin sync status metadata caught up shards", "", "ceph/squid"),
              ("HeadObject missing object ListBucket 403 404", "", "aws/s3"), ("SignatureDoesNotMatch SlowDown 503", "", "aws/s3"),
              ("metadata allowed space smallest site 100%", "storagegrid-119", "netapp/storagegrid-119"),
              ("ILM policy tags Default untagged buckets", "storagegrid-119", "netapp/storagegrid-119"),
              ("TYPE before sample histogram le +Inf x_count", "", "prometheus/prometheus"),
              ("Elasticsearch time field @timestamp Lucene", "", "grafana/grafana"),
              ("ilorest parallel different cache directory", "", "hpe/ilo-redfish"),
              ("podman container inspect Go template --latest", "", "podman/podman")] + [
              ("ILM rule reference time ingest time", f"storagegrid-{v}", f"netapp/storagegrid-{v}") for v in ("118", "119", "120")]
    o = mcp([PLUGIN + "/tools/docs_server.py"], [("search_docs", {"query": q, "product": p, "limit": 3}) for q, p, _ in GOLDEN], cwd=bob)
    for i, (q, _, want) in enumerate(GOLDEN, 1):
        top = text(o[i])["results"][0]
        assert f"{top['vendor']}/{top['product']}".startswith(want), (q, top["vendor"], top["product"])
    print(f"docs-local ok (no VM: the repository's docs/ and the team's knowledge; {len(GOLDEN)} library checks)")

    # ---- 4b. docs leads (each request) and docs hints (each result) on the local index
    def prompt_hook(text, sid, root=bob, env=None):
        return hook("docs-leads.py", {"session_id": sid, "prompt": text, "cwd": work}, cwd=work, root=root, env=env)[1]

    def result_hook(tool, response, sid, root=bob, env=None):
        out = hook("docs-hints.py", {"session_id": sid, "tool_name": tool, "tool_response": response}, cwd=work, root=root, env=env)[1]
        return json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else ""

    out = prompt_hook("Low metadata storage alert on the StorageGRID grid, what does it mean on 11.9?", "lead1")
    assert out.startswith("Docs leads (docs-local;") and "storagegrid-119" in out and "metadata" in out.lower(), out
    assert prompt_hook("Low metadata storage alert on the StorageGRID grid, what does it mean on 11.9?", "lead1") == ""   # once
    for quiet in ("yes continue", "fix the bug in this python function", "/brain-sds:ceph-health"):
        assert prompt_hook(quiet, "lead2") == "", quiet
    out = prompt_hook("clients get SignatureDoesNotMatch and the cluster shows PG_DEGRADED", "lead3")
    assert "PG_DEGRADED [ceph/squid, chunk" in out and "SignatureDoesNotMatch (S3 error code)" in out and "aws/s3" in out, out
    health = "HEALTH_WARN 1 nearfull osd(s)\n[WRN] OSD_NEARFULL: 1 nearfull osd(s)\n[WRN] PG_DEGRADED: Degraded data redundancy\nHTTP_PROXY PATH_INFO"
    ctx = result_hook("Bash", {"stdout": health, "stderr": ""}, "hint1")
    assert "OSD_NEARFULL [ceph/squid" in ctx and "PG_DEGRADED [ceph/squid" in ctx and "HTTP_PROXY" not in ctx, ctx
    assert result_hook("Bash", {"stdout": health, "stderr": ""}, "hint1") == ""                  # each once per session
    assert result_hook("mcp__plugin_brain-sds_docs-local__search_docs", "PG_DEGRADED", "hint2") == ""  # never on the docs' own results
    assert "PG_DEGRADED" in result_hook("mcp__plugin_brain-sds_grafana__query_prometheus", {"text": "alert PG_DEGRADED firing"}, "hint3")
    print("docs leads and docs hints ok (local index)")

    # ---- 5. the installed plugin: a copy outside the repository (Claude Code's cache), the home found through join.sh's link
    cache, cfg, fake = (os.path.join(work, n) for n in ("cache", "cfg", "fakebin"))
    shutil.copytree(os.path.join(bob, PLUGIN), os.path.join(cache, PLUGIN), ignore=shutil.ignore_patterns("__pycache__"))
    os.makedirs(cfg); os.makedirs(fake)
    with open(os.path.join(fake, "claude"), "w") as f:                 # Claude Code's stand-in: records what it was asked
        f.write('#!/bin/sh\necho "$@" >> "$FAKE_CLAUDE_LOG"\ncase "$*" in "plugin list") cat "$FAKE_CLAUDE_LOG.installed" 2>/dev/null;; '
                '"plugin install "*) echo "$3" > "$FAKE_CLAUDE_LOG.installed";; "plugin uninstall "*) rm -f "$FAKE_CLAUDE_LOG.installed";; esac\nexit 0\n')
    os.chmod(os.path.join(fake, "claude"), 0o755)
    calls = os.path.join(work, "claude-calls")
    env = dict(ENV, HOME=os.path.join(work, "home"), CLAUDE_CONFIG_DIR=cfg, FAKE_CLAUDE_LOG=calls, PATH=fake + os.pathsep + ENV.get("PATH", ""))
    os.makedirs(env["HOME"])
    # not joined: the session says how, the guard still guards, the servers answer with the setup hint
    rc, out, _ = hook("session-start.py", {}, cwd=work, root=cache, env=env)
    assert rc == 0 and "not set up on this machine" in out and "join.sh" in out, out
    assert guard("Bash", command="ceph osd out 3", cwd=work, root=cache, env=env) == "block"
    o = mcp([os.path.join(cache, PLUGIN, "tools", "docs_server.py")], [("docs_setup", {})], cwd=work, env=env)
    assert [t["name"] for t in o[99]["tools"]] == ["docs_setup"] and "join.sh" in o[1]["content"][0]["text"]
    o = mcp([os.path.join(cache, PLUGIN, "tools", "connect.py"), "grafana"], [("grafana_setup", {})], cwd=work, env=env)
    assert "join.sh" in o[1]["content"][0]["text"]
    # installed from the marketplace without join.sh: the first session sets the home up itself
    known = os.path.join(cfg, "plugins", "known_marketplaces.json")
    os.makedirs(os.path.dirname(known))
    with open(known, "w") as f:                                     # a marketplace added from a clone's folder: linked
        json.dump({"brain-sds": {"source": {"source": "directory", "path": bob}, "installLocation": bob}}, f)
    rc, out, _ = hook("session-start.py", {}, cwd=work, root=cache, env=env)
    assert "home was linked now" in out and os.path.realpath(os.path.join(cfg, "sds-brain")) == os.path.realpath(bob), out
    assert open(os.path.join(cfg, "CLAUDE.md")).read().count("sds-brain/rules/main.md") == 1
    os.remove(os.path.join(cfg, "sds-brain")); os.remove(os.path.join(cfg, "CLAUDE.md"))
    with open(known, "w") as f:                                     # a git marketplace: cloned in the background
        json.dump({"brain-sds": {"source": {"source": "git", "url": bare}, "installLocation": bob}}, f)
    rc, out, _ = hook("session-start.py", {}, cwd=work, root=cache, env=env)
    assert "is being cloned now" in out and "The team's rules for this session:" in out and "Golden rules" in out, out
    for _ in range(300):
        if os.path.isdir(os.path.join(cfg, "sds-brain", "knowledge")):
            break
        time.sleep(0.1)
    assert os.path.isdir(os.path.join(cfg, "sds-brain", ".git")) and not os.path.islink(os.path.join(cfg, "sds-brain"))
    assert "sds-brain/rules/main.md" in open(os.path.join(cfg, "CLAUDE.md")).read()
    rc, out, _ = hook("session-start.py", {}, cwd=work, root=cache, env=env)
    assert out.startswith(f"SDS brain: Home: {os.path.join(cfg, 'sds-brain')} ") and "in sync" in out, out
    shutil.rmtree(os.path.join(cfg, "sds-brain")); os.remove(os.path.join(cfg, "CLAUDE.md")); os.remove(known)
    print("marketplace install ok (linked folder, background clone)")

    # joined (the link): the copy works on the team repository from any folder
    os.symlink(bob, os.path.join(cfg, "sds-brain"))
    rc, out, _ = hook("session-start.py", {}, cwd=work, root=cache, env=env)
    assert out.startswith(f"SDS brain: Home: {os.path.join(cfg, 'sds-brain')} ") and "in sync" in out and "plugin" not in out.split("Docs:")[0], out
    note = os.path.join(cfg, "sds-brain", "knowledge", "notes", "ceph.md")          # written through the link, as Claude does
    assert guard("Write", file_path=note, cwd=work, root=cache, env=env) == "approve"
    assert guard("Edit", file_path=os.path.join(cfg, "sds-brain", "rules", "main.md"), cwd=work, root=cache, env=env) == "block"
    assert guard("Edit", file_path=os.path.join(cache, PLUGIN, "hooks", "guard.py"), cwd=work, root=cache, env=env) == "block"
    with open(note, "a") as f:
        f.write("- 2026-11-10 · written from another folder · observed · test\n")
    hook("notes-save.py", {"tool_name": "Edit", "tool_input": {"file_path": note}}, cwd=work, root=cache, env=env)
    assert "written from another folder" in sh("git", "show", "main:knowledge/notes/ceph.md", cwd=bare)
    # a teammate changed a skill: the copy is stale, an update is started once, then the person is told
    with open(os.path.join(bob, PLUGIN, "skills", "ceph-health", "SKILL.md"), "a") as f:
        f.write("\nA new step.\n")
    rc, out, _ = hook("session-start.py", {}, cwd=work, root=cache, env=env)
    assert "is being updated and applies from the next session" in out, out
    for _ in range(50):
        if os.path.exists(calls) and "plugin update" in open(calls).read():
            break
        time.sleep(0.1)
    assert "plugin marketplace update brain-sds" in open(calls).read() and "plugin update brain-sds@brain-sds" in open(calls).read()
    rc, out, _ = hook("session-start.py", {}, cwd=work, root=cache, env=env)
    assert "an update did not change that" in out and "join.sh" in out, out
    sh("git", "checkout", "--", PLUGIN, cwd=bob)
    print("installed plugin ok (not joined, joined through the link, stale copy)")

    # ---- 6. join.sh: link, marketplace + plugin, one import line; again changes nothing; --leave undoes it
    os.remove(os.path.join(cfg, "sds-brain")); open(calls, "w").close()
    r = subprocess.run(["sh", os.path.join(bob, "join.sh"), "--no-sudo"], capture_output=True, text=True, env=env, cwd=work, timeout=180)
    assert r.returncode == 0 and "FAIL" not in r.stdout and "done: start claude in any folder" in r.stdout, r.stdout + r.stderr
    md = open(os.path.join(cfg, "CLAUDE.md")).read()
    imp = "@" + os.path.join(cfg, "sds-brain", "rules", "main.md")
    assert os.path.realpath(os.path.join(cfg, "sds-brain")) == os.path.realpath(bob) and md.count(imp) == 1, md
    said = open(calls).read()
    assert f"plugin marketplace add {os.path.realpath(bob)}" in said and "plugin install brain-sds@brain-sds" in said, said
    with open(os.path.join(cfg, "CLAUDE.md"), "a") as f:
        f.write("my own line\n")
    r = subprocess.run(["sh", os.path.join(bob, "join.sh"), "--no-sudo"], capture_output=True, text=True, env=env, cwd=work, timeout=180)
    assert r.returncode == 0 and open(os.path.join(cfg, "CLAUDE.md")).read().count(imp) == 1, r.stdout
    r = subprocess.run(["sh", os.path.join(bob, "join.sh"), "--leave"], capture_output=True, text=True, env=env, cwd=work, timeout=60)
    md = open(os.path.join(cfg, "CLAUDE.md")).read()
    assert r.returncode == 0 and imp not in md and "my own line" in md and not os.path.lexists(os.path.join(cfg, "sds-brain")), (r.stdout, md)
    assert os.path.isdir(os.path.join(bob, "knowledge")) and "plugin uninstall brain-sds@brain-sds" in open(calls).read()
    print("join.sh ok")

    # ---- 7. the VM: vm-setup.py makes SDS a team of the docs service; members search the library over HTTP
    vm, etc, state = (os.path.join(work, n) for n in ("opt-paas", "etc-paas", "state"))
    os.makedirs(os.path.join(vm, "teams")); os.makedirs(etc)
    with socket.socket() as so:
        so.bind(("127.0.0.1", 0)); port = so.getsockname()[1]
    token = "test-token-0123456789abcdef"
    for name, body in (("docs-token", token + "\n"), ("docs.env", f"PAAS_DOCS_PORT={port}\n"), ("plain-http", "")):
        with open(os.path.join(etc, name), "w") as f:
            f.write(body)
    general = os.path.join(work, "general")                            # the other teams' general library: not SDS's
    os.makedirs(os.path.join(general, "docs", "acme", "widget"))
    with open(os.path.join(general, "docs", "acme", "widget", "guide.md"), "w") as f:
        f.write("# Widget guide\n\nThe zzgeneralonly widget.\n")
    engine = os.path.join(bob, PLUGIN, "tools", "engine")              # the same code the VM's docs service runs
    sh(sys.executable, "-c", "import sys, docs_index; docs_index.build(sys.argv[1], sys.argv[2], log=lambda *a: None)",
       os.path.join(general, "docs"), os.path.join(general, "docs.db"), cwd=engine)
    venv = dict(ENV, PAAS_ROOT=vm, PAAS_ETC=etc, GIT_ALLOW_PROTOCOL="file")
    service = subprocess.Popen([sys.executable, os.path.join(engine, "mcp_stdio.py"), "--db", os.path.join(general, "docs.db"), "--http", f"127.0.0.1:{port}",
                                "--token-file", os.path.join(etc, "docs-token"), "--teams-dir", os.path.join(vm, "teams"),
                                "--libraries-dir", os.path.join(vm, "libraries"), "--state-dir", state], env=venv,
                               stdout=open(os.path.join(work, "service.log"), "w"), stderr=subprocess.STDOUT)
    try:
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1).read(); break
            except OSError:
                time.sleep(0.1)
        r = subprocess.run([sys.executable, os.path.join(bob, "vm-setup.py"), "--host", "127.0.0.1", "--remote", "file://" + bare],
                           capture_output=True, text=True, env=venv, timeout=300)
        assert r.returncode == 0 and "FAIL" not in r.stdout and "git add brain-sds/.mcp.json" in r.stdout, r.stdout + r.stderr
        tj = json.load(open(os.path.join(vm, "teams", "sds", "team.json")))
        assert tj["library"] == "sds" and tj["remote"] == "file://" + bare and os.path.isfile(os.path.join(vm, "libraries", "sds", "docs.db"))
        dh = json.load(open(os.path.join(bob, PLUGIN, ".mcp.json")))["mcpServers"]["docs-http"]
        assert dh == {"type": "http", "url": f"http://127.0.0.1:{port}/mcp?team=sds", "headers": {"Authorization": "Bearer " + token}}, dh
        assert subprocess.run([sys.executable, "check.py"], cwd=bob, capture_output=True, text=True, env=ENV).returncode == 0
        sh("git", "add", PLUGIN + "/.mcp.json", cwd=bob); sh("git", "commit", "-qm", "SDS brain: docs-http", cwd=bob); sh("git", "push", "-q", cwd=bob)

        def http(query, **args):
            req = urllib.request.Request(f"http://127.0.0.1:{port}/mcp?team=sds", method="POST", headers={
                "Authorization": "Bearer " + token, "Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
                data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "search_docs", "arguments": dict(query=query, limit=3, **args)}}).encode())
            return json.loads(json.load(urllib.request.urlopen(req, timeout=20))["result"]["content"][0]["text"])["results"]

        hit = http("ILM policy tag default policy", product="storagegrid-119")[0]
        assert hit["product"] == "storagegrid-119" and hit["url"].startswith("https://docs.netapp.com/us-en/storagegrid-119/ilm/"), hit
        assert http("zzgeneralonly") == [], "team sds must not search the other teams' general library"
        # with docs-http in the plugin, docs-local is the small knowledge server: no vendor documents, nothing built locally
        shutil.rmtree(os.path.join(bob, ".cache"), ignore_errors=True)
        o = mcp([PLUGIN + "/tools/docs_server.py"], [("search_docs", {"query": "PG_DEGRADED", "limit": 3}),
                                                     ("search_docs", {"query": "nearfull ratio prod-a", "limit": 3})], cwd=bob)
        assert all(h.get("vendor") == "local" for h in text(o[1])["results"]), text(o[1])       # no vendor document here
        assert "nearfull" in json.dumps(text(o[2])["results"][0]) and not os.path.exists(os.path.join(bob, ".cache", "docs.db"))
        assert "knowledge only" in o[0]["instructions"] and "docs-http" in o[0]["instructions"], o[0]["instructions"]
        rc, out, _ = hook("session-start.py", {}, cwd=bob, root=bob)
        assert "Docs: the vendor library is on docs-http" in out, out
        # a note saved by a member is pushed, the service is told at once, and teammates find it over HTTP seconds later
        # (a request that arrives while a round is running rides on that round: let the service's first one finish)
        for _ in range(150):
            if "knowledge index rebuilt" in open(os.path.join(work, "service.log")).read():
                break
            time.sleep(0.2)
        save(bob, "knowledge/notes/storagegrid.md", "# StorageGRID: grids and quirks\n- 2026-11-10 · grid zzgridalpha uses a 4 TB metadata reserve · verified · test\n")
        for _ in range(100):
            found = [h for h in http("zzgridalpha") if h.get("library") == "team knowledge"]
            if found:
                break
            time.sleep(0.2)
        assert found and "zzgridalpha" in json.dumps(found[0]), "the saved note did not reach the docs service:\n" + "".join(l for l in open(os.path.join(work, "service.log")) if "POST /mcp" not in l)[-1800:]
        # without a local index the hooks ask docs-http
        out = prompt_hook("Low metadata storage alert on the StorageGRID grid, what does it mean on 11.9?", "vmlead")
        assert out.startswith("Docs leads (docs-http;") and "storagegrid-119" in out, out
        assert "PG_DEGRADED [ceph/squid" in result_hook("Bash", {"stdout": "[WRN] PG_DEGRADED: Degraded"}, "vmhint")
        # on the VM itself, docs-local opens the service's own index of the team's knowledge when it matches this clone
        sh("git", "pull", "-q", cwd=bob)
        for _ in range(100):
            if json.load(open(os.path.join(bob, PLUGIN, ".mcp.json")))["mcpServers"].get("docs-http") and \
                    os.path.exists(os.path.join(state, "index", "sds.db.stamp")):
                break
            time.sleep(0.1)
        shutil.rmtree(os.path.join(bob, ".cache"), ignore_errors=True)
        venv_local = dict(ENV, PAAS_DOCS_INDEX=os.path.join(state, "index"))
        o = mcp([PLUGIN + "/tools/docs_server.py"], [("search_docs", {"query": "zzgridalpha", "limit": 3})], cwd=bob, env=venv_local)
        assert "zzgridalpha" in json.dumps(text(o[1])), text(o[1])
        assert not os.path.exists(os.path.join(bob, ".cache", "knowledge.db")), "docs-local built its own index on the VM"
        print("VM docs service ok (vm-setup.py, the library and the team knowledge over HTTP, docs-local knowledge only, "
              "hooks over docs-http, the shared knowledge index)")
    finally:
        service.kill()
finally:
    shutil.rmtree(work, ignore_errors=True)

# ---- 8. connections that are not configured answer instead of failing
o = mcp([PLUGIN + "/tools/connect.py", "grafana"], [("grafana_setup", {})], cwd=ROOT)
assert [t["name"] for t in o[99]["tools"]] == ["grafana_setup"] and "SDS_GRAFANA_URL" in o[1]["content"][0]["text"]
r = subprocess.run([sys.executable, "connections/objectify/launch.py", "--check"], cwd=ROOT, capture_output=True, text=True, env=ENV)
assert r.returncode == 0 and json.loads(r.stdout)["enabled"] is False, r.stdout
o = mcp([PLUGIN + "/tools/connect.py", "nothing-here"], [("nothing_here_setup", {})], cwd=ROOT)
assert "launch.py is missing" in o[1]["content"][0]["text"]
r = subprocess.run([sys.executable, "connections/okp/launch.py", "--check"], cwd=ROOT, capture_output=True, text=True, env=ENV)
assert r.returncode == 1 and "not configured" in r.stdout, r.stdout
o = mcp([PLUGIN + "/tools/connect.py", "okp"], [("okp_setup", {})], cwd=ROOT)
assert [t["name"] for t in o[99]["tools"]] == ["okp_setup"] and "SDS_OKP_URL" in o[1]["content"][0]["text"]

# okp-mcp speaks MCP over HTTP with a session id and event streams: the bridge carries both
import http.server  # noqa: E402
import threading  # noqa: E402


class FakeOkp(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        msg = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if msg.get("method") != "initialize" and self.headers.get("Mcp-Session-Id") != "s-42":
            self.send_response(400); self.end_headers(); return
        if "id" not in msg:
            self.send_response(202); self.end_headers(); return
        result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "okp", "version": "t"}} \
            if msg["method"] == "initialize" else {"tools": [{"name": "search_documentation", "inputSchema": {"type": "object"}}]} \
            if msg["method"] == "tools/list" else {"content": [{"type": "text", "text": "RHCS 8 Administration Guide"}]}
        body = ("event: message\ndata: " + json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": result}) + "\n\n").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream"); self.send_header("Mcp-Session-Id", "s-42")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)


okp = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeOkp)
threading.Thread(target=okp.serve_forever, daemon=True).start()
o = mcp([PLUGIN + "/tools/connect.py", "okp"], [("search_documentation", {"query": "rgw"})], cwd=ROOT,
        env=dict(ENV, SDS_OKP_URL=f"http://127.0.0.1:{okp.server_address[1]}/mcp"))
assert [t["name"] for t in o[99]["tools"]] == ["search_documentation"] and "RHCS 8" in o[1]["content"][0]["text"], o

# the token gateway in front of an HTTP server without authentication (okp-mcp in its OpenShift pod)
with socket.socket() as so:
    so.bind(("127.0.0.1", 0)); uport = so.getsockname()[1]
ug = subprocess.Popen([sys.executable, "connections/http/gateway.py", "--listen", f"127.0.0.1:{uport}", "--upstream",
                       f"http://127.0.0.1:{okp.server_address[1]}/mcp"], cwd=ROOT, env=dict(ENV, MCP_SERVER_TOKEN="upstream-token-0123456789"),
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(100):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{uport}/health", timeout=1).read(); break
        except OSError:
            time.sleep(0.1)

    def ucall(msg, token="upstream-token-0123456789"):
        req = urllib.request.Request(f"http://127.0.0.1:{uport}/mcp", data=json.dumps(msg).encode(), method="POST",
                                     headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            return e.code, None
    assert ucall({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, token="")[0] == 401
    code, got = ucall({"jsonrpc": "2.0", "id": 5, "method": "tools/list"})
    assert code == 200 and got["id"] == 5 and got["result"]["tools"][0]["name"] == "search_documentation", got
    code, got = ucall({"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "search_documentation", "arguments": {}}})
    assert code == 200 and "RHCS 8" in got["result"]["content"][0]["text"], got
finally:
    ug.kill()
okp.shutdown()

# a stdio connection served over HTTP by the gateway (what the Objectify container runs), and use.py's switch
with socket.socket() as so:
    so.bind(("127.0.0.1", 0)); gport = so.getsockname()[1]
gtoken = "gateway-token-0123456789"
gwdir = tempfile.mkdtemp(prefix="sds-brain-gw-")           # the image's layout: gateway.py beside Objectify's files
for f in ("connections/http/gateway.py", "connections/objectify/server.py", "connections/objectify/config.example.json",
          "connections/objectify/observed-endpoints.json"):
    shutil.copy(os.path.join(ROOT, f), gwdir)
gw = subprocess.Popen([sys.executable, os.path.join(gwdir, "gateway.py"), "--listen", f"127.0.0.1:{gport}", "--objectify"],
                      cwd=gwdir, env=dict(ENV, MCP_SERVER_TOKEN=gtoken, OBJECTIFY_CONFIG="/config/none.json"),   # not mounted: the example
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    def gcall(msg, token=gtoken):
        req = urllib.request.Request(f"http://127.0.0.1:{gport}/mcp", data=json.dumps(msg).encode(), method="POST", headers={
            "Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            return e.code, None
    for _ in range(100):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{gport}/health", timeout=1).read(); break
        except OSError:
            time.sleep(0.1)
    assert gcall({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, token="")[0] == 401
    assert gcall({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, token="wrong-token-0123456789")[0] == 401
    code, got = gcall({"jsonrpc": "2.0", "id": "a", "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}})
    assert code == 200 and got["id"] == "a" and got["result"]["serverInfo"]["name"] == "sds-objectify", got
    assert gcall({"jsonrpc": "2.0", "method": "notifications/initialized"})[0] == 202
    code, got = gcall({"jsonrpc": "2.0", "id": 42, "method": "tools/list"})
    assert code == 200 and got["id"] == 42 and [t["name"] for t in got["result"]["tools"]] == ["objectify_status"], got
    code, got = gcall({"jsonrpc": "2.0", "id": 43, "method": "tools/call", "params": {"name": "objectify_status", "arguments": {}}})
    assert code == 200 and got["id"] == 43 and '"enabled": false' in got["result"]["content"][0]["text"], got
finally:
    gw.kill()
    shutil.rmtree(gwdir, ignore_errors=True)
work2 = tempfile.mkdtemp(prefix="sds-brain-use-")
try:
    shutil.copytree(os.path.join(ROOT, PLUGIN), os.path.join(work2, PLUGIN), ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(os.path.join(ROOT, "connections", "http"), os.path.join(work2, "connections", "http"))
    with open(os.path.join(work2, "t"), "w") as f:
        f.write("use-token-0123456789abcdef\n")
    use = lambda *a: subprocess.run([sys.executable, os.path.join(work2, "connections", "http", "use.py")] + list(a), capture_output=True, text=True, env=ENV)
    r = use("grafana", "https://vm.example.internal:8444/mcp", "--token-file", os.path.join(work2, "t"))
    entry = json.load(open(os.path.join(work2, PLUGIN, ".mcp.json")))["mcpServers"]["grafana"]
    assert r.returncode == 0 and entry == {"type": "http", "url": "https://vm.example.internal:8444/mcp",
                                           "headers": {"Authorization": "Bearer use-token-0123456789abcdef"}}, (r.stdout, entry)
    assert "use-token" not in r.stdout, "the token must not be printed"
    assert use("grafana", "https://vm.example.internal:8444/mcp").returncode != 0          # never without a token
    assert use("grafana", "--stdio").returncode == 0
    assert json.load(open(os.path.join(work2, PLUGIN, ".mcp.json")))["mcpServers"]["grafana"]["args"][-1] == "grafana"
    assert use("docs-http", "https://sds-docs.apps.example/mcp", "--token-file", os.path.join(work2, "t")).returncode != 0   # ?team=
    assert use("docs-http", "https://sds-docs.apps.example/mcp?team=sds", "--token-file", os.path.join(work2, "t")).returncode == 0
    assert json.load(open(os.path.join(work2, PLUGIN, ".mcp.json")))["mcpServers"]["docs-http"]["url"].endswith("?team=sds")
    assert use("docs-http", "--stdio").returncode == 0 and "docs-http" not in json.load(open(os.path.join(work2, PLUGIN, ".mcp.json")))["mcpServers"]
finally:
    shutil.rmtree(work2, ignore_errors=True)
print("connections ok")

# ---- 9. the OpenShift manifests: restricted pods, tokens from secrets, Routes over TLS (needs PyYAML; skipped without)
try:
    import yaml
except ImportError:
    yaml = None
if yaml:
    import glob as _glob
    objs = [d for f in sorted(_glob.glob(os.path.join(ROOT, "connections", "openshift", "*.yaml"))) for d in yaml.safe_load_all(open(f)) if d]
    deps = {d["metadata"]["name"]: d for d in objs if d["kind"] == "Deployment"}
    routes = {d["metadata"]["name"]: d for d in objs if d["kind"] == "Route"}
    svcs = {d["metadata"]["name"]: d for d in objs if d["kind"] == "Service"}
    assert set(deps) == {"sds-docs", "sds-grafana", "sds-objectify", "sds-okp"} == set(routes) == set(svcs), (deps.keys(), routes.keys())
    for name, d in deps.items():
        spec = d["spec"]["template"]["spec"]
        assert spec["automountServiceAccountToken"] is False, name
        ports = set()
        for c in spec["containers"]:
            sc = c["securityContext"]
            assert sc["readOnlyRootFilesystem"] and sc["runAsNonRoot"] and sc["capabilities"]["drop"] == ["ALL"] \
                and sc["allowPrivilegeEscalation"] is False, (name, c["name"])
            assert "limits" in c["resources"], (name, c["name"])
            ports |= {p["containerPort"] for p in c.get("ports", [])}
            assert not any("TOKEN" in e["name"] for e in c.get("env", [])), (name, "a token belongs in the secret")
        assert svcs[name]["spec"]["ports"][0]["targetPort"] in ports, name
        assert routes[name]["spec"]["tls"]["termination"] == "edge", name
    env = {e["name"]: e.get("value") for e in deps["sds-grafana"]["spec"]["template"]["spec"]["containers"][0]["env"]}
    assert env["MCP_ALLOWED_HOSTS"] == routes["sds-grafana"]["spec"]["host"], "Grafana must allow the Route's host"
    okp_env = {e["name"]: e.get("value") for e in deps["sds-okp"]["spec"]["template"]["spec"]["containers"][0]["env"]}
    assert okp_env["MCP_HOST"] == "127.0.0.1", "okp-mcp must be reachable through the gateway only"
    assert any(d["kind"] == "NetworkPolicy" for d in objs)
    print("OpenShift manifests ok")
else:
    print("OpenShift manifests not checked (no PyYAML)")
print("all tests passed")
