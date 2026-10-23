# Review of 112 — Strings speak for themselves (the build)

- **Date:** 2026-10-21
- **Reviewer:** a fresh agent, started by the lane; wrote none of 112 and reviewed none of it (neither its draft nor its pre-build review)
- **Reviewed:** `git diff 1875d4cd d2234e8d` on `spec/112-strings-speak-for-themselves` (the rebased tip); the built code before the rebase, `d8fc73f..5005ccbd`
- **Run:** the builder's **39589394200** on `5005ccbd`, read back; no run of my own. The rebased tip's code is the built code's, line for line (below), so the run stands for it, and the wave's dry run checks the rebase (AGENTS.md rule 2).
- **Box:** 45 minutes (build-class by the letter); finished inside it.
- **Re-ran** (`build/lane.lock` absent; single node ids and unit files only):
  - `gh run view 39589394200 --json headSha,conclusion,jobs` → head `5005ccbd`; 43 jobs: every build, rebuild, verify, same-bytes and judge job `success` on three systems; one `failure`, "gather the shards' records"; publish and attest `skipped` (EXECUTED).
  - `gh run download 39589394200 -n release-record-1` and the same for the comparison run 39572424790 (`111d56f4`, `success`): scoreboards **781/873, 0 fail, 85 gap, 7 blocked, unit 4707/4737** against **780/872, unit 4679/4709**; the built run's only red line is `RED: G7 the newest acceptance is not on the release's set (SHA256SUMS)` (EXECUTED).
  - `tests/harness/sameness.py base built --claims <112's list>` → exit 0, `note: explained by claims: 112 2`, beside the two usual notes (3 checks run on no system; 54 Linux fuel rows not compared). Without the claims: exit 1 on exactly the new node and the suite count, 2010 → 2024 (EXECUTED).
  - My own comparison of every check of the two records (status, metrics, worst platform, need, reason): one node only in the built record (the new check); all **253 darwin fuel rows equal**, `CTYPES`' two rows among them (`5,589,462,395` each); 28 metric differences, every one a Linux fuel row of `test_v1_3_upstream_suites.py` (Note 4) (EXECUTED).
  - The two runs' `rebuild-ubuntu-24.04` `SHA256SUMS` → one line differs, `MANIFEST`'s; `python.wasm` `11d7799d…`, the snapshot `e65dfa2d…`, the zip `02d3a3b7…` in both (EXECUTED). `git diff --stat 111d56f4 d8fc73f -- recipes scripts downloads/SHA256SUMS .github` is empty (EXECUTED), so the comparison run is a fair base.
  - The rebase: the `+`/`-` lines of `git diff d8fc73f 5005ccbd -- . ':!context'` and of `git diff 1875d4cd 81decaca -- . ':!context'` are identical (`diff` empty), and `81decaca..d2234e8d` touches only the specification (EXECUTED).
  - On `d2234e8d`: `uv run pytest` of `test_no_string_names_a_context_document`, 109's and 107's checks, `tests/unit/test_scan.py`, `test_gather.py`, `test_sameness.py`, `test_pins.py`, `test_patches.py` → **450 passed, 1 skipped**; the twelve rows of `test_each_refused_option_exits_before_anything_runs`, `test_a_step_that_runs_an_unpinned_python_fails` and `tests/unit/test_landing_lane.py` → **55 passed**; `ruff check src tests` and `ruff format --check src tests` clean (EXECUTED).
  - Three probes of my own (scratchpad, not committed): every tracked file the rule does not read, scanned with `STRING_CITATION_RULES` (Note 3); every string the `re` and `_ALLOWED` skips hide in the read files, and every parenthesized docstring (none hidden today); and seventeen two-line fixtures through `string_citation_hits` (findings 1 and 2) (EXECUTED).

## Acceptance criteria against evidence

1. Seen failing first — met: 77 findings on `b976dcdf`, every row used; the two over the draft's 75 are explained (Difference 1) (READ, the landing notes).
2. Measured on the base — met; on the rebased tip the check passes with the same fifteen rows, so wave 10 added no citing string (EXECUTED).
3. Passes, fifteen rows, 109's and 107's green — met (EXECUTED).
4. Fourteen unit rows — met: ten forms, carriers, negative, files, lines; the file passes whole (EXECUTED, counted in the diff).
5. Strings only — met as amended by Difference 2 (the refusal test's code, the review's L6). I read every hunk of the 27 other files: each changes a string or a comment inside a held program, and `ruff format`'s re-wraps (READ).
6. No protected file changes — met: the diff touches none of them (READ, `--stat`).
7. Every kind B test matches its message — met: each copy follows its message exactly; each passes by node id (EXECUTED).
8. Rule (b) traced — met: nine strings, each with its source (READ).
9. The artifact set — met (EXECUTED above).
10. The fast tier — met as the builder ran it, with the set's five failures named (READ); the rebased tip's fast tier is the lane's (Note 5).
11. Ruff — met (EXECUTED).

**What each reworded string says.** Every user-read message keeps its meaning: the refusals still name what is refused and what to do (`refuse-python`, the dirty tree, the worktree, the shard with `-n`, the xdist rows, `paths.py`'s TMPDIR advice); the rule-(b) texts give the reason the number stood for. The new `sameness.py` wording ("older than the merged release record") uses the term `gather.py`'s docstring defines (READ). The eight workflow step names: nothing reads them but `test_scan.py`'s `SET_SUMS_STEP`, which follows (EXECUTED, `grep` of the five distinct new names under `tests/`, `scripts/`, `release/`, `src/`); `needs:` and `if:` use ids. The rebase's one conflict (`release.yml:79`) kept this name and main's comment; a step name and a comment are not code, so no run of its own is needed: the wave's dry run on three systems checks it, as AGENTS.md rule 2 says for a rebase only.

**Fuel.** `CTYPES`' `review 033` is kept by the `GUEST_FUEL` row, and the file's diff touches only `:229` to `:237`, outside it; its fuel is equal in both records (EXECUTED). `PLANT`'s comment moved; its four checks record no metric (EXECUTED, the base record: `{}`). The other held programs are host programs run in a child Python.

**The judge not weakened (rule 4).** The renamed unit id (`test_gather.py`'s `FORGERIES` row) changes only its label; its mutation (`c.newest.pop("set_sums")`) and its expected `G7` line are the same (READ). The refusal test matches `REFUSAL`'s whole shape (`refused: .+ \(.+\)`) where it matched `spec 052`, and the line must still name the option: looser than a citation, tighter than the `refused:` prefix (READ). The allowance: fifteen rows, four named reasons, each read by the rule; a stale row fails.

## Findings, most severe first

1. **Low — a `re.escape` inside a pattern argument is not read** (`tests/harness/scan.py`, `_not_read`, `nodes.update(id(sub) for arg in given for sub in ast.walk(arg))`). The skip walks the whole pattern argument, so a `re.escape(...)` call nested in it is skipped too. Decision 3 says "`re.escape`'s argument is text and is read". Failure: `re.search(re.escape("… (spec 052)"), err)` or `re.compile(re.escape(MSG_TEXT))` with a literal gives no hit (EXECUTED: the fixture `re.compile(re.escape("spec 052"))` → `[]`). This is the common way a test matches a message. No string is hidden today (EXECUTED: the only citing strings under a pattern argument are `scan.py`'s own rule patterns, `:3253` and `:3371`). Fix text: in `_not_read`, walk the pattern argument but do not descend into an `ast.Call` (a call's arguments are text, not the pattern); the carriers row gains `F = re.search(re.escape("<cite>"), s)` as a hit.

2. **Low — a parenthesized docstring is read by neither rule** (`tests/harness/scan.py`, `_not_read`'s `docs.add((first.value.lineno, first.value.col_offset))`). 109's `_python_prose` keys a docstring by the statement's position, `(first.lineno, first.col_offset)`; this rule by the constant's. For `("…")` the two differ by the parenthesis, so 109 reads nothing and this rule skips the token. Failure: `def f():\n    ("see spec 052 here")` → `context_citation_hits` `[]` and `string_citation_hits` `[]` (EXECUTED). Decision 3 promises "the docstrings 109 reads, and no more". None exists in the read files today (EXECUTED: 0). Fix text: key `docs` by `(first.lineno, first.col_offset)`, as 109 does, so the set skipped is exactly the set 109 reads; the carriers row gains a parenthesized first statement as a hit.

3. **Note — two comment-holding files under `tests/` are read by neither rule** (`tests/cpython_configure.txt:2-3`, `(spec 086, …)` and `constitution §4.5`; `tests/upstream/numpy.ini:1`, `pandas.ini:1`, `pillow.ini:2`). 109 reads only `.py`, `.sh`, `.toml`, `.yml` and `.yaml` under `tests/`. Every hit is a `#` comment, not a string, so it is 109's ground, not 112's; and the `.ini` files sit beside the allowance files. The closer's roadmap line could name them. Nothing else outside the read files holds a citing string but the judge's allowance files, `context/`, `recipes/` and the root's Markdown and dotfiles (EXECUTED).

4. **Note — Linux upstream fuel drifts between the two runs; it is not 112's.** 28 of the 54 `linux-x86_64` fuel rows differ (the largest `cpython-b`, −3.1 %), every one in `test_v1_3_upstream_suites.py`. Their inputs, the upstream suites and the set's bytes, did not move, and the judge does not compare them ("release fuel not from darwin, not compared: 54"). All 253 darwin rows are equal (EXECUTED).

5. **Note — the rebased tip's fast tier is not recorded.** The builder ran the rules check and the scanner's unit file on `d2234e8d` (334 passed), and I ran the unit files above; the whole fast tier on the rebased tip is the lane's integration run. The risk it would see is a citing string wave 10 added, and the check on `d2234e8d` passes (EXECUTED).

6. **Note — a field's format spec is not read** (`_literal_pieces`, depth above zero). `f"{x:spec 052}"` gives no hit (EXECUTED). A format spec is the format mini-language, so no message can carry a citation there; no change asked.

## Constitution checks

- §4.1 (few, recorded patches): no patch and no recipe file changes; two `scripts/` files change one string each, recorded by `MANIFEST`'s two recipe lines (READ; EXECUTED, the set's `SHA256SUMS` differs only in `MANIFEST`).
- §4 pins: no input changes (READ).
- §5.6: the build recipe's `scripts/` change was reviewed before the build (the pre-build review, its Disposition confirmed against the built text: M1's marker line, M2's `GUEST_FUEL` row, L3's id, L6's pattern are each in the diff) and is reviewed here; the builder's run is on the exact code reviewed.
- AGENTS.md rule 4: no check is weakened, no golden, expected, allowance or progress file changes; the judge-hash line names the changed files, and `--accept-judge` is in the flags.
- §7 never-do list: nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. L1 — fixed as the fix text: `_not_read` walks a pattern argument through `_pattern_nodes`, which stops at a call, so `re.escape`'s text inside a pattern argument is read. The carriers row gains `F = re.search(re.escape("<cite>"), "x")` as a hit, seen failing first (the row failed on the old scanner, passes on the new).
2. L2 — fixed as the fix text: `docs` is keyed by the statement's position, `(first.lineno, first.col_offset)`, as 109's `_python_prose` keys it, so a parenthesized first statement is read by this rule; the carriers row gains `def g():\n    ("<cite>")` as a hit, seen failing first with L1's case. On the fixed scanner (EXECUTED): `tests/unit/test_scan.py` and `tests/checks/test_rules.py` 334 passed, 1 skipped; the string rule over the tree 0 findings, every row used; `ruff check` and `ruff format --check` clean.
3. Notes 3 to 6 — no answer needed.

## Verdict

Lands: the strings read in words, the check holds them with fifteen reasoned rows, and the set's binary bytes and every compared fuel row are the base's. Findings 1 and 2 are latent gaps in the skips (nothing hidden today), fixed by the builder or answered in writing, with no further review round.
