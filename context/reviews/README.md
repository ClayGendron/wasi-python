# Reviews

One file per review, `NNN-<spec slug>-YYYY-MM-DD.md`, where `NNN` is the specification reviewed. A review of a specification before it is built uses the same name with `-spec` before the date. A pull request's review uses `-pr` before the date, `NNN-<slug>-pr-YYYY-MM-DD.md`, where `NNN-<slug>` is the name of one of the pull request's news files (`../changes/NNN-<slug>.md`).

## One review per pull request

Every pull request into `dev` that is not documentation only gets one review, by a fresh agent or a person who did not write the change, written as `NNN-<slug>-pr-YYYY-MM-DD.md` in the template below: criteria against evidence, findings ranked, constitution checks, verdict (`../specifications/138-pull-requests-into-dev-and-the-judge-runs-where-it-is-needed.md`, Decision 9).

- **No confirmation round.** The author answers in the pull request. A code fix is a new commit on the same pull request, and the reviewer reads it and signs again.
- **The reviewer reads the pull request's run** (`ci-status`, the gather's summary) and never dispatches one. A Low that touches only `context/` the reviewer may commit to the pull request's branch.
- **The review file is committed last**, as the branch's last context-only commit, after the final code commit. `ci-status` runs `quick` on it and re-uses the green run of the head it follows.
- **`ci-status` holds the review.** It fails the pull request when no such file is among its changed paths; when the newest commit that changed it is followed by a commit touching a path that is not documentation only; when its `Reviewer:` line is empty or names the author (the self-check's author, or any `Claude-Session:` trailer on the pull request's code commits); or when the first line of its `## Verdict` section does not begin with "Lands". The `Reviewer:` line names the reviewer's session (`https://claude.ai/code/session_…`) or a person. This is a process guard, not an identity guard: an agent that writes a false `Reviewer:` line defeats it. The check arrives with step 3 of specification 138 (written 2026-10-25); until then the owner's agent reads the review file before it merges.
- **The pre-build review stays** for the classes constitution §5.6 names (the guest's imports or exports, the artifact set, the build recipe) and for a structural specification, as a review of the specification before the branch has code (`-spec`). A parallel-safe runner change needs none unless its Kind line says **structural**: its pull request's review reads the code with the specification.
- **Per release**, the security review and the structural review (below) are the release pull request's review.

## The author's self-check

The self-check is the pull request's description, from the pull request template, `.github/PULL_REQUEST_TEMPLATE.md`, which step 6 of specification 138 adds. It names the author (session or name), every new check seen failing first, the Windows legs read, every gap naming its closer, and the news file. Until the template exists, the author writes those five lines at the top of the pull request's description. The reviewer names any item found unchecked and ranks it Low.

## The reviewer's checklist

Time box: 25 minutes for a parallel-safe specification, 45 for a build-class one or a package. The review states its box.

1. Read the pull request's run first: `ci-status` and the gather's summary in the job summary (`gh pr checks <n>`, `gh run view <id>`). Its run id is the review's **Run** line; it is your reading of the counted tests (constitution §5.6). Dispatch no run. Locally, run what you need by node id.
2. Read the self-check; any unchecked item is a Low finding, written as the fix text.
3. Criteria against evidence, one line each, labelled EXECUTED, READ or INFERRED.
4. The diff against §4 and §7; the news file's claim block against the diff and the gather's `GROWTH` rows (a row changed and not claimed is Medium). 4a. Structure, one line (AGENTS.md, "Structure is reviewed"): does the diff add a concern, a lifecycle flag, a module-level mutable, a test seam, a platform branch, a private-API use or a function past 80 lines that the rubric below would score down, whether or not a rules check catches it? Name the row. If it does and the Kind line does not carry **structural**, that is Medium: the specification is structural and was not reviewed as one.
5. One to three probes by node id, locally.
6. Rank: High (a wrong answer or an unsafe default), Medium (a guarantee not evidenced), Low (a write-in). A Low with its fix text needs no round. One Medium per review is normal; state what evidence would close it.
7. A Low that touches only `context/` you may write in yourself, as a commit of the exact text on the pull request's branch; a code fix stays the author's (constitution §5.6).
8. Verdict in one sentence. It begins "Lands" when nothing stands, or "Does not land yet: <the High or the Mediums>". After the author's fix commit, read it and write the verdict again: a verdict that begins "Lands" is your signature on the head.

## Template

```
# Review of NNN — <spec title>

- **Date:** YYYY-MM-DD
- **Reviewer:** <the reviewer's session URL or a person; not the author>
- **Reviewed:** <commit or diff range, or "the specification as drafted">
- **Run:** <the pull request's run id (`ci-status`)>
- **Re-ran:** <what the reviewer ran by node id> → <counts and exit codes seen>

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
<Lands / Does not land yet: …>, in one sentence.
```

## Structural review

A review of `src/` against the eight-row rubric of `../research/2026-10-20-a-design-review-of-the-runner.md` (section 1), which is structural review zero: its scorecard (section 2, at `30e9b41`) is what the first release review compares with, and each later review compares with the last. It is written twice (AGENTS.md, "Structure is reviewed"; spec 108):

- **Before every release**, by a fresh agent that wrote none of the code since the last structural review, on the commit before the version bump, whose `src/` is the one tagged; the review is committed with the bump, the release pull request's run judges that commit, and the tag follows the merge (constitution §5.5), beside the security review. File: `<version>-structural-review-YYYY-MM-DD.md`, the twin of `<version>-security-review-YYYY-MM-DD.md`. The release waits on its High findings; the judge refuses a released version with no such file (`test_a_release_has_its_structural_review`).
- **For a structural specification** (its Kind line carries **structural**), as a "Structure" section of its pre-build review (`NNN-<slug>-spec-YYYY-MM-DD.md`): the eight rows, one line each, saying which row the change moves and which way, and the measurements it claims to change, before and after, by the commands below. The judge holds that a built structural specification cites that review (`test_built_structural_specifications_cite_their_pre_build_review`).

Time box: 45 minutes for a release review: the measurements first (one command each), then the diff of `src/` since the last structural review and the modules whose measurements moved; the whole of `src/` only when no structural review precedes it (the first compares with the memo, which read it whole). The "Structure" section fits inside its review's box. The review states its box.

### The eight rows

Score each Strong, Adequate or Weak, with a one-line reason, as the memo did.

- **R1 Contract.** Are the public names still few and snapshotted (`tests/public_api.txt`)? Is every invariant a sentence a test checks? Are failures promised by type, never by message?
- **R2 Safety.** Are the defaults safe and read once? Is every channel to the host bounded? Are arguments validated before any side effect? Are check-and-use races closed by identity?
- **R3 Layering.** Does exactly one module touch the engine's private API? Is policy apart from mechanism? Is the import graph acyclic?
- **R4 Process state.** Is module-level mutable state owned by one object and reset in one place? Is each lifecycle an enum and a table, not flags? Is the lock order written down?
- **R5 Portability.** Does OS-specific behaviour live in the platform modules (`_platform.py` and the two below it, no other) behind one interface, chosen once?
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
