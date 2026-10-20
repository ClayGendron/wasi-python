# Reviews

One file per review, `NNN-<spec slug>-YYYY-MM-DD.md`, where `NNN` is the
specification reviewed. A review of a specification before it is built
uses the same name with `-spec` before the date.

## The builder's self-check

The builder writes this list at the top of its review request (AGENTS.md rule 8; the owner,
2026-10-19). The reviewer names any item found unchecked and ranks it Low.

```
Before you ask for a review:
- rebased onto main's tip (or the named stacked base) today; the base commit in the Status line;
- CI run dispatched on this exact commit and read: run id, red lines (GREW and G7 only), the
  Windows legs green or the Windows criterion named;
- every number from a measured run on this base, labelled EXECUTED; the growth list is this
  build's, not the draft's;
- "For the lane": the claim list (rows changed, grown with reasons, retired, passes moved), the
  exact flags, each reason beginning with the spec number, the wave kind (parallel-safe,
  build-class, package, toolchain), dry-run needs;
- every new check seen failing first; a Windows and a Linux branch named or excluded with a reason;
- every gap names its closer; every reserved follow-up has a roadmap line;
- packages.toml has its reason line; README rows the spec changes listed;
- CHANGELOG under the one unreleased section; questions numbered from the next free number;
- ruff check, ruff format --check, the fast tier: green, output in build/<spec>/.
```

## The reviewer's checklist

Time box: 25 minutes for a parallel-safe specification, 45 for a build-class one or a package.
The review states its box.

1. Dispatch your own run of the release workflow on the reviewed commit first, so it finishes
   while you read. Its run id is the review's **Run** line; it is your re-run of the counted
   tests (constitution §5.6). Locally, run the fast tier or single node ids only (AGENTS.md
   rule 3a).
2. Read the self-check; any unchecked item is a Low finding, written as the fix text.
3. Criteria against evidence, one line each, labelled EXECUTED, READ or INFERRED.
4. The diff against §4 and §7; the claim list against the diff (a row changed and not claimed is
   Medium).
5. One to three probes by node id, locally.
6. Rank: High (a wrong answer or an unsafe default), Medium (a guarantee not evidenced), Low (a
   write-in). A Low with its fix text needs no round. One Medium per review is normal; state what
   evidence would close it.
7. A Low that touches only `context/` you may write in yourself, as a commit of the exact text on
   the specification's branch once the builder has handed it over; a code fix stays the
   builder's (constitution §5.6).
8. Verdict in one sentence: "lands", "lands once <Mediums>", or "does not land yet: <High>".

A wave's integration review is written by a fresh agent that reviewed none of its entries: each
entry's `git range-diff` against its reviewed tip, the conflicts each builder named, the fast
tier's output, and the claim lists against the wave's GREW lines. Its verdict is "lands as merged
at <tip>", or names the entry to eject.

## Template

```
# Review of NNN — <spec title>

- **Date:** YYYY-MM-DD
- **Reviewer:** <agent or person; not the author>
- **Reviewed:** <commit or diff range, or "the specification as drafted">
- **Run:** <the reviewer's own release-workflow run id>
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
