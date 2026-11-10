---
name: brain-learn
description: Capture durable knowledge into the team's notes or captures, curate captures into notes, save a tested procedure as a runbook, write an incident postmortem. Use for "remember this", "write it down", "curate the captures", "save this as a runbook", "postmortem", "incident report", "what did we learn".
when_to_use: A problem was solved, a change procedure the user ran worked, the user asks to keep something, to curate captures, or to write up an incident.
---
# Brain learn

Facts come from tool results, pasted output and the user only (rule 2). Never keys, tokens or passwords: write
`<REDACTED>` (rule 4). Everything is under `~/.claude/sds-brain/knowledge/`, the team repository: the `knowledge/...`
paths below are in it, never in the folder you were started in. The save hook checks each file for secrets, commits
it and pushes it to the team, and the search index follows by itself.

## a) Capture
1. Worth it? Only if a teammate in three months saves real time. Not generic vendor facts the library already has.
2. `grep -ri <keyword> ~/.claude/sds-brain/knowledge/{notes,captures,runbooks}` first: update an existing line instead of
   adding one.
3. Destination, each from its template in `~/.claude/sds-brain/templates/` (read it, fill it, never change it):
   confident and the topic is clear -> a dated line in `knowledge/notes/<topic>.md`
   (`- <date> · <fact> · <verified|observed|documented|user-reported|hypothesis> · <source>`; a new topic file starts
   from `topic.md`). Otherwise a capture `knowledge/captures/<date>-<slug>.md` from `capture.md`. A settled finding
   that needs sections: a page `knowledge/notes/<topic>-<slug>.md` from `page.md`. An exporter metric the team has
   understood: a block from `metric.md` in `notes/observability.md`.
   Pages, runbooks and incidents start with the template's header: `applies_to` names the exact releases (rule 3),
   `confidence` one of the five words, `last_verified` the date it was last checked here (change it, and the
   confidence, only on new evidence), `sources` what it rests on.
4. Tell the user the file and a two-line summary.

## b) Curate ("curate the captures")
List `knowledge/captures/*.md`. For each choose: **promote** (dated lines in `notes/<topic>.md`, a page, or a runbook (c)
when it is a procedure the user has since run and confirmed), **merge** (into an existing note, bump its date),
**keep**, **discard**. Show the table (file | decision | reason) and wait for the user's go-ahead before writing.
Never raise confidence while curating. Facts older than 180 days are listed at session start: ask the user to
re-verify the ones that matter; never delete them on your own.

## c) Runbook
A change procedure the **user ran and that worked** (add an RGW zone, replace an OSD drive, expand a grid, rotate a
certificate) becomes `knowledge/runbooks/<topic>-<task>.md`. Not run yet, or fixed on the way and not re-checked: a
capture instead. Search first (`ls knowledge/runbooks`): an existing runbook is updated, never duplicated. Every
command is for the user to run; placeholders (`<fsid>`, `<osd-id>`, `<tenant-id>`) plus the read-only command that
shows each value. Start from `templates/runbook.md`: its header, then Pre-checks, Procedure, Verification and
Rollback, which `check.py` requires, then Scope and History.
Show it to the user and wait for the go-ahead before saving. When asked for change steps later, a matching runbook
is the answer: follow it, say which one, add a History line when the user reports it worked again.

## d) Incident report
Blameless postmortem in `knowledge/incidents/<yyyy>/<date>-<slug>.md`, from `templates/incident.md` (header,
impact, UTC timeline, root cause with its confidence and the alternatives weighed, contributing factors, what fixed
it, what did not, evidence, learning, action items). Search the library and `knowledge/` for related history first.
Mark suggested commands apart from executed ones; a correlated timing is a lead, not the root cause.
Then one dated line in `notes/<topic>.md` pointing to the report.

## e) A new investigation procedure
When the team keeps running the same investigation and no skill covers it, draft one from `templates/skill.md`
(scope, bounded read-only evidence, decision points, escalation and exit, sources) and give it to the user as text:
skills live in `brain-sds/skills/` and only people add them, with a commit.
