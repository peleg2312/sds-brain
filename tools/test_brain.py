#!/usr/bin/env python3
"""Tests of the brain's hooks, docs server and checks, in a temporary copy (nothing here is changed). Standard library.
    python3 tools/test_brain.py          exits 1 on the first failure"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(ROOT, ".claude", "hooks")
ENV = {k: v for k, v in os.environ.items() if not k.startswith(("SDS_", "GIT_"))}


def hook(script, payload, cwd=ROOT, env=None, root=ROOT):
    r = subprocess.run([sys.executable, os.path.join(root, ".claude", "hooks", script)], input=json.dumps(payload),
                       capture_output=True, text=True, cwd=cwd, env=env or ENV, timeout=60)
    return r.returncode, r.stdout, r.stderr


def guard(tool, **inp):
    rc, out, err = hook("guard.py", {"tool_name": tool, "tool_input": inp, "cwd": ROOT})
    return "block" if rc == 2 else "ask" if '"ask"' in out else "allow"


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
python3 tools/search.py "PG_DEGRADED"
cat CLAUDE.md
cp CLAUDE.md /tmp/claude-copy.md
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
echo x >> CLAUDE.md
sed -i 's/Read-only/Read-write/' CLAUDE.md
rm .claude/hooks/guard.py
cp /tmp/evil.py tools/brainlib.py
echo 'ceph *' > .claude/hooks/guard-allow.txt
git checkout -- .claude/settings.json""".splitlines()
ASK = """curl -X POST https://grid.example/api/v3/authorize -d '{"username":"x"}'
curl -X DELETE https://objectify.example/account/obj_acc
ssh node1 'some-unknown-tool --flag'
systemctl restart ceph.target
sudo reboot""".splitlines()
for want, cmds in (("allow", ALLOW), ("block", BLOCK), ("ask", ASK)):
    for c in cmds:
        got = guard("Bash", command=c)
        assert got == want, f"guard: expected {want}, got {got}: {c}"
for path, want in (("CLAUDE.md", "block"), (".claude/hooks/guard.py", "block"), (".claude/settings.json", "block"),
                   ("tools/docs_server.py", "block"), ("connections/grafana/launch.py", "block"), (".mcp.json", "block"),
                   ("knowledge/notes/ceph.md", "allow"), ("knowledge/captures/2026-11-10-x.md", "allow"),
                   ("docs/redhat/rhcs-8.1/notes.md", "allow"), (".claude/skills/ceph-health/SKILL.md", "allow"),
                   ("/tmp/elsewhere/CLAUDE.md", "allow")):
    got = guard("Write", file_path=path if path.startswith("/") else os.path.join(ROOT, path), content="x")
    assert got == want, f"guard: Write {path}: expected {want}, got {got}"
for tool, want in (("mcp__sds-docs__search_docs", "allow"), ("mcp__grafana__query_prometheus", "allow"),
                   ("mcp__grafana__list_datasources", "allow"), ("mcp__grafana__update_dashboard", "block"),
                   ("mcp__grafana__create_incident", "block"), ("mcp__objectify__objectify_status", "allow"),
                   ("mcp__objectify__objectify_get_account", "allow"), ("mcp__objectify__resize_account", "block"),
                   ("mcp__sds-okp__search_documentation", "allow")):
    assert guard(tool) == want, f"guard: {tool}: expected {want}"
print(f"guard ok ({len(ALLOW)} allowed, {len(BLOCK)} blocked, {len(ASK)} asked)")


# ---- 2. two people, one team repository: notes are saved, shared, merged; secrets stay out
def sh(*cmd, cwd=None, check=True):
    r = subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True, env=ENV, timeout=120)
    assert not check or r.returncode == 0, (cmd, r.stdout, r.stderr)
    return r.stdout.strip()


work = tempfile.mkdtemp(prefix="sds-brain-test-")
try:
    bare, alice, bob = (os.path.join(work, n) for n in ("remote.git", "alice", "bob"))
    shutil.copytree(ROOT, alice, ignore=shutil.ignore_patterns(".git", ".cache", "__pycache__"))
    sh("git", "init", "-q", "--bare", "-b", "main", bare)
    sh("git", "init", "-q", "-b", "main", alice)
    for k, v in (("user.name", "alice"), ("user.email", "alice@example.test")):
        sh("git", "config", k, v, cwd=alice)
    sh("git", "add", "-A", cwd=alice); sh("git", "commit", "-qm", "the brain", cwd=alice)
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
    assert rc == 0 and out.startswith("SDS brain: Team repository: in sync"), out
    assert "notes/ceph.md (1 facts): Ceph: clusters and quirks" in out and "notes/ceph-versions.md" in out, out
    assert "Team changes in the last 14 days: notes/ceph.md (alice)" in out, out
    assert "only the reported fleet summary" in out and "grafana not configured" in out, out

    # both add a fact to the same file at the same time: both lines reach the remote (merge=union), no conflict
    save(alice, "knowledge/notes/ceph.md", "- 2026-11-10 · alice's fact · observed · test\n", "a")
    save(bob, "knowledge/notes/ceph.md", "- 2026-11-10 · bob's fact · observed · test\n", "a")
    merged = sh("git", "show", "main:knowledge/notes/ceph.md", cwd=bare)
    assert "alice's fact" in merged and "bob's fact" in merged and "nearfull" in merged, merged
    rc, out, _ = hook("session-start.py", {}, cwd=alice, root=alice)
    assert "in sync" in out and "bob's fact" in open(os.path.join(alice, "knowledge/notes/ceph.md")).read(), out

    # a runbook and a capture are listed; the checks catch a runbook without its sections and a secret
    save(bob, "knowledge/runbooks/ceph-replace-osd-drive.md", "# Replace a failed OSD drive\n## Pre-checks\n## Procedure\n## Verification\n## Rollback\n")
    save(bob, "knowledge/captures/2026-11-10-slow-list.md", "# Bucket listing slow on prod-a\n## Symptom\nlisting takes 40 s\n")
    rc, out, _ = hook("session-start.py", {}, cwd=bob, root=bob)
    assert "runbooks: 1 tested procedures" in out and "ceph-replace-osd-drive" in out and "captures: 1 waiting" in out, out
    assert subprocess.run([sys.executable, "tools/check.py"], cwd=bob, capture_output=True, text=True, env=ENV).returncode == 0
    with open(os.path.join(bob, "knowledge/runbooks/bad.md"), "w") as f:
        f.write("# Bad\n## Procedure\n")
    with open(os.path.join(bob, "knowledge/notes/leak.md"), "w") as f:
        f.write("# Leak\n- 2026-11-10 · password=Hunter2!x · observed · test\n")
    r = subprocess.run([sys.executable, "tools/check.py"], cwd=bob, capture_output=True, text=True, env=ENV)
    assert r.returncode == 1 and "FAIL runbook knowledge/runbooks/bad.md" in r.stdout and "FAIL no secret in knowledge/notes/leak.md" in r.stdout, r.stdout
    os.remove(os.path.join(bob, "knowledge/runbooks/bad.md")); os.remove(os.path.join(bob, "knowledge/notes/leak.md"))
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
    o = mcp(["tools/docs_server.py"], [("search_docs", {"query": "PG_DEGRADED", "limit": 3}),
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
    r = subprocess.run([sys.executable, "tools/search.py", "SignatureDoesNotMatch", "--limit", "2"], cwd=bob, capture_output=True, text=True, env=ENV)
    assert r.returncode == 0 and "aws/s3" in r.stdout, r.stdout[:300]
    print("docs server ok")
finally:
    shutil.rmtree(work, ignore_errors=True)

# ---- 5. connections that are not configured answer instead of failing
o = mcp(["connections/grafana/launch.py"], [("grafana_setup", {})], cwd=ROOT)
assert [t["name"] for t in o[99]["tools"]] == ["grafana_setup"] and "SDS_GRAFANA_URL" in o[1]["content"][0]["text"]
r = subprocess.run([sys.executable, "connections/objectify/launch.py", "--check"], cwd=ROOT, capture_output=True, text=True, env=ENV)
assert r.returncode == 0 and json.loads(r.stdout)["enabled"] is False, r.stdout
print("connections ok")
print("all tests passed")
