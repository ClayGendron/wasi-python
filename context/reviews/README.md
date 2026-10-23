# Reviews

One file per review, `NNN-<spec slug>-YYYY-MM-DD.md`, where `NNN` is the specification reviewed. A review of a specification before it is built uses the same name with `-spec` before the date.

## The builder's self-check

The builder writes this list at the top of its review request (AGENTS.md rule 8; the owner, 2026-10-19). The reviewer names any item found unchecked and ranks it Low.

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

Time box: 25 minutes for a parallel-safe specification, 45 for a build-class one or a package. The review states its box.

1. Dispatch your own run of the release workflow on the reviewed commit first, so it finishes while you read. Its run id is the review's **Run** line; it is your re-run of the counted tests (constitution §5.6). Locally, run the fast tier or single node ids only (AGENTS.md rule 3a).
2. Read the self-check; any unchecked item is a Low finding, written as the fix text.
3. Criteria against evidence, one line each, labelled EXECUTED, READ or INFERRED.
4. The diff against §4 and §7; the claim list against the diff (a row changed and not claimed is Medium). 4a. Structure, one line (AGENTS.md, "Structure is reviewed"): does the diff add a concern, a lifecycle flag, a module-level mutable, a test seam, a platform branch, a private-API use or a function past 80 lines that the rubric below would score down, whether or not a rules check catches it? Name the row. If it does and the Kind line does not carry **structural**, that is Medium: the specification is structural and was not reviewed as one.
5. One to three probes by node id, locally.
6. Rank: High (a wrong answer or an unsafe default), Medium (a guarantee not evidenced), Low (a write-in). A Low with its fix text needs no round. One Medium per review is normal; state what evidence would close it.
7. A Low that touches only `context/` you may write in yourself, as a commit of the exact text on the specification's branch once the builder has handed it over; a code fix stays the builder's (constitution §5.6).
8. Verdict in one sentence: "lands", "lands once <Mediums>", or "does not land yet: <High>".

A wave's integration review is written by a fresh agent that reviewed none of its entries: each entry's `git range-diff` against its reviewed tip, the conflicts each builder named, the fast tier's output, and the claim lists against the wave's GREW lines. Its verdict is "lands as merged at <tip>", or names the entry to eject.

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

## Structural review

A review of `src/` against the eight-row rubric of `../research/2026-10-20-a-design-review-of-the-runner.md` (section 1), which is structural review zero: its scorecard (section 2, at `30e9b41`) is what the first release review compares with, and each later review compares with the last. It is written twice (AGENTS.md, "Structure is reviewed"; spec 108):

- **Before every release**, by a fresh agent that wrote none of the code since the last structural review, on the commit before the version bump, whose `src/` is the one tagged; the review is committed with the bump, the release's dry run runs on that commit, and the tag follows the CHANGELOG-only release commit (AGENTS.md rule 6b), beside the security review. File: `<version>-structural-review-YYYY-MM-DD.md`, the twin of `<version>-security-review-YYYY-MM-DD.md`. The release waits on its High findings; the judge refuses a released version with no such file (`test_a_release_has_its_structural_review`).
- **For a structural specification** (its Kind line carries **structural**), as a "Structure" section of its pre-build review (`NNN-<slug>-spec-YYYY-MM-DD.md`): the eight rows, one line each, saying which row the change moves and which way, and the measurements it claims to change, before and after, by the commands below. The judge holds that a built structural specification cites that review (`test_built_structural_specifications_cite_their_pre_build_review`).

Time box: 45 minutes for a release review: the measurements first (one command each), then the diff of `src/` since the last structural review and the modules whose measurements moved; the whole of `src/` only when no structural review precedes it (the first compares with the memo, which read it whole). The "Structure" section fits inside its review's box. The review states its box.

### The eight rows

Score each Strong, Adequate or Weak, with a one-line reason, as the memo did.

- **R1 Contract.** Are the public names still few and snapshotted (`tests/public_api.txt`)? Is every invariant a sentence a test checks? Are failures promised by type, never by message?
- **R2 Safety.** Are the defaults safe and read once? Is every channel to the host bounded? Are arguments validated before any side effect? Are check-and-use races closed by identity?
- **R3 Layering.** Does exactly one module touch the engine's private API? Is policy apart from mechanism? Is the import graph acyclic?
- **R4 Process state.** Is module-level mutable state owned by one object and reset in one place? Is each lifecycle an enum and a table, not flags? Is the lock order written down?
- **R5 Portability.** Does OS-specific behaviour live in one module behind one interface, chosen once?
- **R6 Testability.** Are seams constructor parameters or protocol objects? Do tests drive public behaviour? Does production code carry a branch only the judge takes?
- **R7 Evolvability.** Can one person hold each module, and each function, in their head? Does the code say why without the archive open? Does the type checker pass? Is the engine upgrade's cost written?
- **R8 Operability.** Do `stats()`, the records and the trap strings still say what the guest did? Can a warning deadlock an embedder?

### The measurements

One command each, run from the repository's root on the reviewed commit; the review records the output beside the score it informs, labelled EXECUTED. Where a rules check of specs 103 to 108 reports the same number, quote its pass line too (`uv run pytest tests/checks/test_rules.py -q`). The numbers are those of `a9064a2` (EXECUTED 2026-10-20, spec 108), before the chain; the memo's differ where its method was reading, not a command.

| what (row) | command | at `a9064a2` |
|---|---|---|
| module sizes (R7) | `wc -l src/wasi_python/*.py \| sort -n` | `runner.py` 6,241; `tools.py` 2,450; `mounts.py` 2,235; 11,423 in all |
| functions over 80 lines (R7; spec 108's check and its allowance list) | `uv run python -I -c "import ast,pathlib;[print(p.name,sum(1 for n in ast.walk(ast.parse(p.read_text())) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.end_lineno-n.lineno+1>80)) for p in sorted(pathlib.Path('src/wasi_python').rglob('*.py'))]"` | `runner.py` 6, `tools.py` 2 |
| module-level mutables and locks (R4) | `grep -rnE '^_?[a-z]\w*\s*(:[^=]+)?=\s*(threading\.(R?Lock\|Condition\|Event\|Semaphore)\(\|\{\|\[\|dict\(\|list\(\|set\(\|collections\.)' src/wasi_python --include=*.py` | 47 lines: `runner.py` 46, `__init__.py` 1 |
| private-API uses (R3) | `grep -rnE 'wasmtime\._\|\b_ffi\.\|\b_bindings\.\|\._func\b\|_from_ptr\|\._context\(\)\|\.ptr\(\)' src/wasi_python --include=*.py` | 27 lines: `mounts.py` 15, `runner.py` 11, `tools.py` 1 |
| platform branches (R5) | `grep -rnE 'sys\.platform\|os\.name\b\|platform\.system' src/wasi_python --include=*.py` | 22 lines, all in `runner.py` |
| private names the judge patches (R6; spec 108's seam check holds the runner's) | `grep -rhoE 'monkeypatch\.setattr\(\s*\w+(\.\w+)*,\s*"_\w+"' tests --include=*.py \| sort \| uniq -c \| sort -rn` | 59 distinct; `runner._ctrl_c_watched` 8 times, `_remove_tree` 5 |
| `Any` and `type: ignore` (R7) | `grep -rc '\bAny\b' src/wasi_python --include=*.py; grep -rc 'type: ignore' src/wasi_python --include=*.py` | 349 `Any`; 12 ignores |
| the type checker (R7) | spec 106's check by its node id in `tests/checks/test_rules.py`, and the length of its allowlist | none before 106 |
| citations of the archive (R7) | `grep -roE 'spec [0-9]{3}' src/wasi_python --include=*.py \| wc -l; grep -roE "review'?s? [A-Z][0-9]+" src/wasi_python --include=*.py \| wc -l` | 315 specification references; 37 finding IDs |

### Ranking

- **High:** a structural rule bypassed, or a finding the next change would build on: a concern added to a module at its ceiling, a flag added to a lifecycle that has an enum, an import cycle, a seam off the process object. A release waits on it; a structural specification does not build yet.
- **Medium:** a row that moved toward Weak since the last structural review, or a measurement that moved the wrong way with no specification named to move it back. It becomes a reserved specification with a roadmap line before the next release; the release may go.
- **Low:** a write-in, as in every review.

Verdict in one sentence: "the structure holds", "holds once <the Mediums are reserved>", or "does not hold: <the High>".

### Template

```
# <version>: structural review against the rubric, YYYY-MM-DD

- **Date:** YYYY-MM-DD
- **Reviewer:** <agent or person; wrote none of src/ since the last structural review>
- **Reviewed:** main at <commit>, the commit before the bump to <version>; its src/ is what ships
- **Compared with:** <the last structural review's file, or the memo's scorecard at 30e9b41>
- **Box:** 45 minutes; <where it stood at the box>

## Measurements (EXECUTED)
| what | then | now | command |
|---|---|---|---|

## The eight rows
| row | then | now | reason |
|---|---|---|---|
| R1 Contract | | | |
| R2 Safety | | | |
| R3 Layering | | | |
| R4 Process state | | | |
| R5 Portability | | | |
| R6 Testability | | | |
| R7 Evolvability | | | |
| R8 Operability | | | |

## Findings, most severe first
1. **<title>** (`path:line`, row Rn) — <the defect in one sentence>.
   Next change it would shape: <what the next specification would build on it>.

## Verdict
<the structure holds / holds once … / does not hold: …>, in one sentence.
```
