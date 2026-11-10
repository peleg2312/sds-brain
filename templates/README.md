# Templates

Copy one, fill it in, save it under `knowledge/` (Claude does the same through the `brain-learn` skill). People change
these files with a commit; Claude reads them and never edits them. No passwords, keys or tokens in anything copied
from here: `<REDACTED>`.

| Template | Becomes | When |
|---|---|---|
| `topic.md` | `knowledge/notes/<topic>.md` | The first fact of a new topic (ceph, rgw, s3, storagegrid, linux, hardware, observability, objectify, tools, general) |
| `capture.md` | `knowledge/captures/<yyyy-mm-dd>-<slug>.md` | A solved problem or finding that is not certain yet, or whose topic is unclear: curated later |
| `page.md` | `knowledge/notes/<topic>-<slug>.md` | A settled finding that needs sections (a fact line is too short) |
| `runbook.md` | `knowledge/runbooks/<topic>-<task>.md` | A change procedure a person ran and that worked. `check.py` requires its four sections |
| `incident.md` | `knowledge/incidents/<yyyy>/<yyyy-mm-dd>-<slug>.md` | A postmortem, blameless, times in UTC |
| `metric.md` | a section of `knowledge/notes/observability.md` | An exporter metric the team has understood |

A fact line, everywhere: `- <yyyy-mm-dd> · <fact> · <confidence> · <source>`, with confidence one of `verified`
(tested here, more than once or with recorded evidence), `observed` (seen once here), `documented` (read in a cited
document), `user-reported` (someone said so) or `hypothesis`.
