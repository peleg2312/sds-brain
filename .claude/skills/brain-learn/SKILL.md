---
name: brain-learn
description: Capture durable knowledge into the team's notes or captures, curate captures into notes, save a tested procedure as a runbook, write an incident postmortem. Use for "remember this", "write it down", "curate the captures", "save this as a runbook", "postmortem", "incident report", "what did we learn".
when_to_use: A problem was solved, a change procedure the user ran worked, the user asks to keep something, to curate captures, or to write up an incident.
---
# Brain learn

Facts come from tool results, pasted output and the user only (rule 2). Never keys, tokens or passwords: write
`<REDACTED>` (rule 4). Everything is under `knowledge/` in this repository; the save hook checks each file for secrets,
commits it and pushes it to the team, and the search index follows by itself.

## a) Capture
1. Worth it? Only if a teammate in three months saves real time. Not generic vendor facts the library already has.
2. `grep -ri <keyword> knowledge/notes knowledge/captures knowledge/runbooks` first: update an existing line instead of
   adding one.
3. Destination: confident and the topic is clear -> a dated line in `knowledge/notes/<topic>.md`
   (`- <date> · <fact> · <verified|observed|hypothesis> · <source>`; a new topic file starts with `# Topic: what is in it`).
   Otherwise a capture `knowledge/captures/<date>-<slug>.md`:
   ```
   # <title>
   ## Symptom        exact error text, so a search finds it
   ## Cause
   ## Fix / workaround   commands in a code block, placeholders instead of real names
   ## Scope          cluster / grid, releases, hardware where it applies; where it is known not to
   ## How we know    what was observed, when, confidence: verified | observed | hypothesis
   ## History        <date>: created
   ```
   A fact that needs sections but is settled is a page `knowledge/notes/<topic>-<slug>.md` (line 1 `# <title>`).
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
shows each value. Sections (`tools/check.py` requires the four marked *):
```
# <Verb phrase: Replace a failed OSD drive on an Apollo 4200>
When to use: ...   Impact while running: ...   Prerequisites: ...
## Pre-checks *      read-only commands and what each must show before going on
## Procedure *       numbered steps, one command block each, with why
## Verification *    commands that prove it worked
## Rollback *        how to undo each step, or "not reversible after step N"
## Scope             clusters / grids, releases, hardware it was run on
## History           <date>: created, run on <cluster, release> by <who> · verified
```
Show it to the user and wait for the go-ahead before saving. When asked for change steps later, a matching runbook
is the answer: follow it, say which one, add a History line when the user reports it worked again.

## d) Incident report
Blameless postmortem in `knowledge/incidents/<yyyy>/<date>-<slug>.md`. Search the library and `knowledge/` for
related history first. Sections, in order: **Header** (title, date, severity sev1-sev4, status, clusters / grids
affected, started / detected / mitigated / resolved with time zone), **Impact**, **Timeline** (one line per event),
**Root cause** (with a confidence word), **Contributing factors**, **What fixed it**, **What was tried and did not
work**, **Evidence** (redacted log lines, health checks, alerts, document references), **Action items** (owner, due).
Then one dated line in `notes/<topic>.md` pointing to the report.
