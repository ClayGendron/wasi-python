# Review of 102 — the release tier: slow tests run before a publication, never left out (pre-build)

- **Date:** 2026-10-20
- **Reviewer:** a fresh agent (Claude Opus 5.5). It wrote none of spec 102 and reviewed none of it.
- **Reviewed:** the specification as drafted and revised, `spec/102-the-release-tier` at `9460d14`
  (base main `4161ef9`). Read against `AGENTS.md`, the constitution (§5.5, §5.6, §5.7, §7),
  `context/reviews/README.md`, `decisions.md` ("Two tiers of tests" and "Spec 102's four
  questions", 2026-10-20), and the code the design changes, on main: `scoreboard.py`, `gather.py`,
  `history.py`, `release.yml`, `release_shards.toml`, `contourpy.toml`, `python.toml` and the
  CPython plan files. The stacked chain 103 to 109 was read at `dbecd2d` with `git show`.
- **Time box:** 45 minutes (build-class: it edits the release workflow).
- **Run:** none. This is a pre-build review of a specification. No line of the judge has changed
  yet, so a run on `9460d14` would only repeat main's judge. The lane holds the judge slot.
- **Re-ran:**
  - One probe of `scoreboard.accept`, EXECUTED in the worktree with `uv run python` (a scratch
    script, no guest run). An accepted pass that a later run deselects keeps its row in
    `accepted.json` (`pass`). But it appears in the new history line's `passed_removed`. And today
    `compare` puts it in `upstream_unrun`, so `accept` refuses without `--partial`. Finding 2 rests
    on this probe.
  - The pinned `Python-3.15.0.tar.xz`, read as data with `tar -xO` (after `downloads/SHA256SUMS`
    was checked by the drafter; nothing unpacked): `Lib/test/test_io/test_largefile.py:274` and
    `Lib/test/test_mmap.py:1281`. Finding 4 rests on these lines.
  - `git show dbecd2d:<path>` for the chain's `release.yml`, `AGENTS.md`, `tests/checks/test_rules.py`,
    `tests/harness/scan.py` and the eleven harness files 102 edits.

## Acceptance criteria against evidence

The question here is whether each criterion can be checked, not whether it is met.

1. **The checks, seen failing first** — checkable. The landing notes name each failure. READ.
2. **The survey first** — checkable. The memo exists or does not, and the commit order shows it came
   first. READ.
3. **The baseline** (each release group by node id, twice, restaged) — checkable on darwin with
   single node ids, which AGENTS.md rule 3a allows. READ.
4. **Nothing normal moves but what is named** — checkable from the builder's node-id runs and the
   branch run. READ. Finding 1 changes its CPython clause.
5. **A normal branch run** — checkable from the run. READ.
6. **A release branch run** — checkable, but it contradicts criterion 5. Criterion 5 allows a red
   G5 `fewer` line for the four inline tests, and a red G7. Criterion 6 says "the gather passes".
   The same four tests leave the normal groups on that run too, so the same `fewer` line appears.
   Finding 7.
7. **The gather's conditions** — half checkable. The skipped case is shown by run 5. The failed
   case is left to "the first red release leg on any later run". That rests on GitHub's documented
   meaning of `failure()`, INFERRED. Check 9's mutants hold the text. Note 1.
8. **The judge** — checkable. READ.

## Findings, most severe first

1. **Medium: the four inline-cpu tests stop running on Windows and macOS** (Decision 9; criterion 4;
   the flags). `test_posixpath` is planned in `cpython-fs` (`tests/upstream/python/cpython-fs.txt:32`).
   That group runs on all three systems: `upstream-numpy-a` on Linux, `upstream-macos` and
   `upstream-windows` (`tests/release_shards.toml`). Its inline test reads
   `is_resource_enabled('cpu')` (`Lib/test/test_posixpath.py:367`, `maxusers` 1000 or 100). Decision
   9 puts it in the normal group's `-i` list, so it runs only in the release tier. Decision 10 runs
   the release tier on Linux alone. So a test that passes on Windows today never runs on Windows
   again, in any tier. It runs only on Linux CI and in the lane's darwin acceptance. That breaks
   "every test runs in one tier" for Windows. It also means fewer checks on three systems, against
   AGENTS.md rule 4. The other three inline tests (`test_tokenize` and `test_unparse` in
   `cpython-b`, `test_unicodedata` in `cpython-c`) are Linux-only today, so for them nothing
   is lost.
   Failure: a change that breaks `posixpath` on Windows (its path rules differ there) passes every
   run. Before 102 that test would have failed in `upstream-windows`.
   **Fix text (Decision 9, criterion 4, the claim list, the flags):** "An `inline` entry is **not**
   ignored in its normal group. It runs in both tiers: in its normal group on every system that
   group runs on, doing the reduced work `cpu` off allows, and in its release group on Linux and
   in the release acceptance, with `cpu` on, doing the full work. This is the one case where a test
   id runs in both tiers. It is not a duplicate, because the work differs, and nothing leaves a
   system. The partition proof still holds: every `inline` entry is in its normal group's
   selection and in its release group's `match`. `passes` does not fall, so the
   `--accept-fewer-passes` flag and criterion 4's 'down by exactly the four' clause go away.
   Criterion 4 becomes: CPython's normal groups' JSON byte for byte as the base's, `passes`
   unchanged." Check 2 changes to match: no `-i` entries. Check 4 gains one fixed stream in which
   an `inline` id is missing from its normal group's stream; that stream is a finding.

2. **Medium: a normal acceptance writes every release-tier pass into the history as removed**
   (Decision 5; check 5; `tests/harness/scoreboard.py:288-292`). `accept` builds the passed set from
   the run's own checks. So a check the run did not run is not in the set. The probe showed this,
   EXECUTED: an accepted pass, deselected in the next run, stays `pass` in `accepted.json` but is
   listed in that history line's `passed_removed`. Decision 5 says "a normal acceptance never
   changes a release-tier row". That holds for `accepted.json` but not for the history.
   Failure: at 102's own landing, the seventeen contourpy groups' suite and class checks were
   passing and accepted. The landing is in the normal tier. Its history line says those passes
   were removed. Each later normal acceptance carries the gap, and the next release acceptance
   adds them back. So the append-only record (AGENTS.md rule 6) says passes were lost and found
   when none were. Its per-area `counts` fall by the release tier's size. Any reader of
   `passed_sets` (the history check, a future "since the last release" diff) sees the same false
   change.
   **Fix text (Decision 5 and check 5):** "On a normal-tier run, `accept` takes the passed set as
   the run's passes **plus** every release-tier check that is in the newest line's passed set and
   in this run's `tier_deselected`. So a normal acceptance's `passed_added` and `passed_removed`
   name only normal-tier changes. A release acceptance's name every change. Its `counts` count a
   release-tier row by its accepted status." Check 5 adds: "after a release acceptance in which
   release-tier check X passed, a normal acceptance's history line has X in neither
   `passed_removed` nor `passed_added`, and its `passed_digest` covers X."

3. **Medium: a check can move from the normal tier to the release tier with no flag of its own**
   (Decisions 2, 3 and 5). On a normal run the ratchet puts an accepted check that is now
   release-tier into `release_tier`. That list is never red. The only flag the move needs is
   `--accept-judge`, which every TOML edit needs anyway. Two things are missing. Nothing refuses a
   release group that is none of the three kinds: Decision 3's path rules cover marker and keyword
   groups, but a plain group with `tier = "release"` in a family with no `release_marker` (lxml,
   say) is not forbidden. And nothing marks the move in the ratchet.
   Failure: a pin bump breaks a test in `numpy-core`. The builder adds a `[[release_select]]` entry
   for it, with a reason, or marks a whole small group `tier = "release"`. The lane's landing
   ratchet prints `release tier not run +1`, not `LOST`. The landing goes green. The loss shows
   only at the release acceptance, weeks later, against AGENTS.md rule 5 ("no pass is lost
   quietly"). The judge-hash line and the review are the only defences.
   **Fix text (Decisions 3 and 5, checks 1 and 5, the flags):** "Each entry in `accepted.json`
   records the `tier` it was accepted in (absent reads as normal). On any run, an accepted check
   whose entry says `normal` and which is release-tier now is listed `moved`. `moved` is red, and
   `--accept` refuses it without `--accept-tier-move "<reason>"`. The reason begins with the spec
   number and goes in the history line. A release group must be a marker, keyword or regrtest-list
   group (or 067's node-id form, when 067 adds it). A group with `tier = "release"` and none of
   these is refused." 102's own landing then carries `--accept-tier-move "102: contourpy's slow and
   random_big cases move to the release tier (the owner, 2026-10-20)"` for its seventeen groups.
   Check 1 adds the plain-release-group mutant. Check 5 adds: a normal-accepted pass that becomes
   release-tier is `moved` and red, and the flag accepts it.

4. **Low: the `largefile` half of Decision 9 is wrong under WASI.** Both `largefile` gates sit
   inside a platform branch. `test_io/test_largefile.py:274` gates only when `sys.platform[:3] ==
   'win' or sys.platform == 'darwin'`. `test_mmap.py:1281` gates only on Windows and Apple. The
   guest's `sys.platform` is `wasi`, so neither gate runs there. Both modules take the other branch:
   they probe the filesystem with a seek past 2 GiB and skip with "filesystem does not have
   largefile support" if it fails. Both are already planned in the normal tier
   (`cpython-fs.txt:18` and `:26`). If the builder lists them as `gated`, the partition proof
   reports "listed, not gated" and the build goes red. Adding `largefile` to the release resources
   changes nothing in the guest.
   **Fix text (Decision 9):** "Under WASI, neither `largefile` gate runs: both are inside
   `win`/`darwin` branches (`test_largefile.py:274`, `test_mmap.py:1281`). Both modules stay in
   their normal group, where the filesystem probe decides whether they run or skip. The survey
   records which. `release_resources` keeps `largefile` so the release tier says what the owner
   asked for, but no `gated` entry names a `largefile` gate unless the survey's normal streams show
   one. The `cpu`-decorated tests inside `test_largefile` (lines 192 and 242) are `gated` entries
   like any other." The owner's answer 4 is still met: the `largefile` tests run today, in the
   normal tier.

5. **Low: `excluded_marker` lets a family leave tests out of both tiers** (Decision 2a). The truth
   table only asks that `marker or release_marker` equal `not excluded_marker`. So
   `excluded_marker = "slow"`, with no `release_marker`, passes the table. That is exactly the
   exclusion the owner ruled out ("do not exclude anything from the full suite").
   **Fix text (Decision 2a, check 1):** "`excluded_marker` may name only markers in a closed list
   in `upstream.py`: today `network` and `db`. Each is a guest capability `README.md` says is
   absent. Any other name, or a name the family's `release_marker` uses, is refused." Check 1 adds
   a family with `excluded_marker = "slow"`, which is refused.

6. **Low: the baseline for the release comparison lives only in `build/`** (Decision 6). The lane
   has cleared `build/` before to free disk (the lane's disk-space notes). If
   `build/releases/<previous>/record.json` is gone, Decision 6 does not say what happens.
   **Fix text (Decision 6):** "No normal acceptance writes a release-tier row (Decision 5). So
   `accepted.json`'s release-tier rows are the previous release acceptance's. The ratchet at the
   release acceptance already compares every release-tier row with them, for `LOST`, `FEWER` and
   `GREW`. The `build/releases/<previous>/record.json` comparison adds outcomes by id. The lane
   keeps that file and records its SHA-256 in the release acceptance's reason. If it is missing,
   the lane says so in the reason and relies on the ratchet alone."

7. **Low: criteria 5 and 6 disagree about which red lines are allowed.** Run 6 runs the normal tier
   too. So it shows the same G5 `fewer` lines for the inline tests, and the same G7 lines on a set
   that is not main's.
   **Fix text (criterion 6):** "the gather's only red lines are the ones criterion 5 allows."
   Finding 1's fix removes the `fewer` lines from both criteria.

8. **Low: the §5.5 amendment would split a sentence.** "After 're-pin, re-run, re-verify,
   publish'" lands inside "A new pinned set means: re-pin, re-run, re-verify, publish, and write
   the memo that says what changed."
   **Fix text (For the lane):** "§5.5, a new last sentence of the paragraph: '**The release rule**
   (owner, 2026-10-20): …'".

9. **Low: if a re-pin adds a new inline-`cpu` test, nothing notices** (Decision 9). The four inline
   tests were found by a reader run once, at drafting time. A re-pin of CPython that adds a fifth
   test reading `is_resource_enabled('cpu')` would run only its reduced form, in the normal tier.
   The test is still run, but it never does its full work.
   **Fix text (Decision 9, check 4):** "A rules check reads the staged `Lib/test` files of every
   planned module. The set of tests that read `is_resource_enabled('cpu')` must equal the plan's
   `inline` entries." Check 4 adds a mutant with one unlisted test.

10. **Low: the chain 103 to 109 changes what 102's code may say, and 102's Design table does not
    list `tests/checks/test_rules.py`.** Checked at `dbecd2d`:
    - **The behaviour of 102's design is unchanged.** In the eleven harness files 102 edits, the
      chain changes only comments and docstrings. Its `release.yml` hunks are comments too. It
      leaves AGENTS.md rules 3a and 6b, the sentences 102 rewrites, alone. Its two new AGENTS.md
      bullets and its rule-8 sentence do not touch 102's text.
    - **Every file in 102's Design table except the context documents conflicts by text.** That
      includes `scan.py` (+785 lines) and `release.yml`. Each conflict is mechanical.
    - **After the chain, `test_code_outside_src_names_no_context_document` holds every comment and
      docstring under `tests/` and `.github/workflows/`.** None may cite a specification number, a
      § section, a `context/` path or a finding id. 102's new code, its `judge-release` job's
      comments and its TOML comments must give reasons in words. The `context/release-tier-claims.toml`
      path may appear in code, but not in a docstring.
    - **`CONTEXT_CITATION_ALLOWED` admits citations in exactly the four TOMLs 102 edits:**
      `numpy.toml` (5 entries), `pandas.toml` (6), `contourpy.toml` (3) and `python.toml` (5).
      Their stated reason (`JUDGE_FILE`) is that such a file "changes only by a judge change of its
      own, which clears these comments then". An entry that admits nothing fails.
    **Fix text (Design, For the lane):** "If 103 to 109 land first, 102 rebases onto them. Its
    edits to `numpy.toml`, `pandas.toml`, `contourpy.toml` and `python.toml` clear those files'
    cited comments. The same change removes each matching `CONTEXT_CITATION_ALLOWED` entry in
    `tests/checks/test_rules.py`, which joins the Design table. No new comment or docstring cites a
    document." If 102 lands first, the chain's rebase takes 102's new comments into its sweep.

11. **Note: GitHub's skip rule reaches past the gather.** When a needed job is skipped, every job
    after it is skipped too, unless that job's `if:` uses a status function. `attest`, `publish` and
    `pypi` need `gather` and run only on tags, where `judge-release` always runs, so they are
    unaffected. A later job that needs `gather` on a branch run must carry `!cancelled() &&
    !failure()` too. Worth one sentence in Decision 13, and a rules row if check 9 can hold it
    cheaply. INFERRED from GitHub's documented `needs` semantics.

12. **Note: the price on darwin is not stated.** For Linux, the release legs add six to ten jobs
    queued behind the 40-job Pro limit on a tag. That is a few minutes, INFERRED. And every branch
    run, wave dry run and lane acceptance sheds about 3.97 T of contourpy fuel, about six plot
    shards' worth. Both claims are sound. The release acceptance's darwin cost is missing. At 0.154
    to 0.170 s per G (the parallel-shards research), the release tier as specified is about 4.4 to
    9 T. That is roughly 12 to 25 minutes of guest time on top of the normal tier at `-n 3`. After
    067, sympy's 2.6 T group is the longest single leg, about 7 minutes. All of this is INFERRED.
    The survey should state the measured figure so the lane can book the slot.

13. **Note: the acceptance's counts will read lower.** In a normal-tier scoreboard, the release
    tier's checks show as deselected, so the area counts in the lane's acceptance commit messages
    (`763/850 pass`) fall by the release tier's size. The ratchet line's `release tier not run <n>`
    explains the gap. The lane's message should quote it.

## Constitution checks

- §4.9 (tests count): every criterion is counted. Times appear only as INFERRED benchmark notes.
  Holds.
- §4.10 (claims carry evidence): the drafter's counts are labelled EXECUTED, with their readers
  named. One count is wrong under WASI (finding 4). Holds otherwise.
- §5.5 (a release is a re-run): the release rule is added, but at the wrong place (finding 8).
- §5.6 (review before build): this review meets it for the workflow change. The build review must
  read both branch runs (criteria 5 and 6).
- §5.7 (the lane): the amendment's text matches §5.7's current sentences ("runs the full judge on
  that exact commit in the main tree", "judges the tip once"). Holds.
- AGENTS.md rule 4 (never weaken the judge): nothing leaves both tiers, with two exceptions. The
  Windows loss is finding 1, and the `excluded_marker` door is finding 5. A move between tiers
  that is not marked is finding 3.
- AGENTS.md rule 5 (no pass lost quietly): findings 2 and 3.
- §7 never-do list: nothing tripped. No artifact byte, no guest import or export, no download
  changes.

## Disposition (filled in by the author, then confirmed by the reviewer)

The builder's answers (2026-10-20, late night), on `spec/102-the-release-tier` rebased onto
`dbecd2d` (the chain 103 to 109; no conflict hunk, since the branch touches only the
specification and this review). Every finding is written into the specification in the same
commit as this section.

1. M1 (the inline-cpu tests leave Windows and macOS) — **fixed, the review's text taken.** An
   `inline` entry is no longer ignored in its normal group: it runs reduced there, on every system
   the group runs on, and in full in its release group (Decision 9). The Principle names it as the
   one exception to "one tier", and Decision 2(c) says the same. CPython's normal groups' JSON is
   byte for byte the base's (Decision 3, the table in Decision 2, check 2). The proof: each inline
   id ran in its normal group's stream and is in its release group's `match`; check 4 gains the
   stream missing an inline id. `passes` does not fall, so `--accept-fewer-passes` leaves the
   Kind line, Decision 9, criterion 4 (now "JSON byte for byte, `passes` unchanged"), the claim
   list (**passes**: none) and the flags.
2. M2 (a normal acceptance writes release-tier passes as removed) — **fixed, the review's text
   taken.** Decision 5, *The acceptance*: on a normal run the passed set is the run's passes plus
   every check in the run's `release_checks` that is in the newest line's passed set, so
   `passed_added` and `passed_removed` name normal-tier changes only and `passed_digest` covers the
   carried rows; the line's `counts` take each unrun release-tier check at its accepted status.
   Check 5 adds the review's row (after a release acceptance in which X passed, a normal
   acceptance has X in neither list, its digest covers X, its counts count X). The Principle says
   a row not run keeps its place in the history's passed set too.
3. M3 (a move between tiers has no flag) — **fixed, the review's text taken, in both directions.**
   The record gains `release_checks` on every run (it replaces the draft's `tier_deselected`, so
   a release run says which checks are release-tier too). Each `accepted.json` entry records its
   check's tier (`"release"`, or absent for normal, so today's entries keep their bytes). The
   ratchet's new `moved` list is red on any run, normal to release or back; `--accept` refuses it
   without `--accept-tier-move "<reason>"`, which rewrites only the moved entries' `tier` and goes
   in the history line as `tier_move_reason`. A release-tier check that is gone is `absent`, not
   `moved`. The gather's G5 shows a move on a branch run, so the claim list names it (Decision 13;
   criterion 5 allows that line). Decision 3: a release group is a marker, keyword or regrtest list
   group (067's node-id form later), or refused. Decision 2 states both ways a test can move: a
   whole check is `moved`; a test leaving a normal group lowers its `passes`, `fewer`. Decision 7
   and *For the lane*: 102's landing carries `--accept-tier-move` for contourpy's seventeen groups.
   Checks 1 and 5 carry the mutants.
4. L4 (the `largefile` gates do not run under WASI) — **fixed, the review's text taken.**
   Decision 9 says both gates sit in `win`/`darwin` branches, both modules stay in `cpython-fs`
   where the filesystem probe decides, the survey records which, `release_resources` keeps
   `largefile`, and no `gated` entry names a `largefile` gate unless the survey's streams show one;
   `test_largefile`'s two `cpu`-decorated tests are `gated` entries. The Problem, Decision 9's
   title, its INFERRED paragraph and *The owner's answers* (4) follow.
5. L5 (`excluded_marker` can leave tests out of both tiers) — **fixed.** Decision 2(a): a closed
   list, `upstream.EXCLUDABLE` (`network`, `db`); any other name, or one of them in
   `release_marker`, is refused; a name joins the list only by a judge change. Check 1 adds
   `excluded_marker = "slow"` and a `release_marker` using `network`.
6. L6 (the previous release record lives only in `build/`) — **fixed, the review's text taken**
   (Decision 6, *If that record is gone*): the ratchet against `accepted.json` is the comparison
   that needs no file; the lane keeps the record, names its SHA-256 in the release acceptance's
   reason, or says it is missing there.
7. L7 (criteria 5 and 6 disagree) — **fixed.** Criterion 6: "the gather's only red lines are the
   ones criterion 5 allows". Criterion 5's allowed lines are now a growth line, the G5 move line
   for the seventeen contourpy groups, or G7; the `fewer` line is gone with M1.
8. L8 (the §5.5 amendment splits a sentence) — **fixed.** *For the lane*: a new last sentence of
   §5.5's paragraph, after "…prepares one and asks (owner, 2026-10-17)."
9. L9 (a re-pin can add an unlisted inline test) — **fixed.** Decision 9: a rules check over the
   pinned tarball's `Lib/test` members, read as data as `regrtest.py` already reads them for its
   id checks: the test functions in planned modules that read `is_resource_enabled('cpu')` equal
   the plans' `inline` entries. Check 4 adds the two mutants (a plan missing one; a fifth such
   test). The Design table names the reader in `regrtest.py` and the row in `test_rules.py`.
10. L10 (the chain changes what 102's code may say) — **fixed.** The branch is rebased onto the
    chain. The Design table gains `tests/checks/test_rules.py` (the four TOMLs'
    `CONTEXT_CITATION_ALLOWED` entries removed as 102's edits clear their cited comments, and the
    new rules rows), and a paragraph under it says no new comment or docstring cites a document,
    the ledger's path appearing only as code. Decision 15 names the chain as the base.
11. N11 (the skip reaches past the gather) — **taken.** Decision 13 gains the sentence; check 9
    gains a rules row (every job that needs `gather` and is not limited to tags carries a status
    function) and its mutant.
12. N12 (the darwin price) — **taken.** Decision 11: the survey states the release tier's measured
    darwin fuel and its longest group, with the review's INFERRED range beside it until measured.
13. N13 (the acceptance's counts read lower) — **taken.** *For the lane*: the lane's message
    quotes the ratchet line's `release tier not run <n>` beside the printed counts; the history's `counts`
    do not fall (M2).

## Verdict

Fit to build once the three Mediums are written in: the inline-cpu tests keep Windows and macOS,
a normal acceptance keeps release-tier passes in the history, and a move between tiers is red
without its own flag. The Lows and Notes need no further round once their text is in.

In one line: the tiers are sound and nothing is dropped, but three ways a pass could leave a
system or the record quietly must be closed first.
