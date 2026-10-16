# Reviews

One file per review, `NNN-<spec slug>-YYYY-MM-DD.md`, where `NNN` is the
specification reviewed. A review of a specification before it is built
uses the same name with `-spec` before the date.

Template:

```
# Review of NNN — <spec title>

- **Date:** YYYY-MM-DD
- **Reviewer:** <agent or person; not the author>
- **Reviewed:** <commit or diff range, or "the specification as drafted">
- **Re-ran:** <commands> → <counts and exit codes seen>

## Acceptance criteria against evidence
1. <criterion> — met / not met: <the evidence or the gap>

## Findings, most severe first
1. **<title>** (`path:line`) — <the defect in one sentence>.
   Failure: <concrete input or state → wrong output or crash>.

## Constitution checks
- §4 constraints: <each one touched, and whether it holds>
- §7 never-do list: <anything tripped>

## Disposition (filled in by the author, then confirmed by the reviewer)
1. <finding 1> — fixed in <commit> / not fixed because <reason>.

## Verdict
<lands / does not land yet>, in one sentence.
```
