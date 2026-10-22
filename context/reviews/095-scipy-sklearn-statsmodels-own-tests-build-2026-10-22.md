# Review of 095 — scipy's, scikit-learn's and statsmodels' own tests in the release (build)

- **Date:** 2026-10-22
- **Reviewer:** a fresh agent (Claude Opus 5.5). I wrote none of 095 and reviewed none of it
  before. I read `AGENTS.md`, the constitution, `context/reviews/README.md`, `decisions.md`'s
  newest entries ("The path to 0.1.0 is compressed", "Upstream hosts are not probed", "Fast tests
  and slow tests"), the specification (Kind, Design, Acceptance criteria, For the lane, and the
  Landing notes: *The build, completed*, *For the lane, as built*, *The builder's self-check*),
  its pre-build and delta review (`095-…-spec-2026-10-20.md`), and 102's ledger rules
  (`context/progress/README.md`, "The release tier").
- **Reviewed:** `git diff 2a8091d7 ab5cde5b` (main to the builder's tip). I began on `b86f847c`.
  The lane then told me the builder had pushed `ab5cde5b`, the fix for this review's first
  finding (H1). `git diff b86f847c ab5cde5b` is one unit row and one fixture line, read in full.
- **Run:** none of my own. The builder's runs are on the exact commits (AGENTS.md rule 3a; the
  compressed plan). I read both back:
  - `39705963592` on `b86f847c`: 42 success, 2 failure, 6 skipped. It is the run H1 is from.
  - `39708064741` on `ab5cde5b`: see *The run* below.
- **Box:** 45 minutes (build-class, a package family). I went past it, by about 40 minutes, on
  four guest probes that decide M1 and L2, and on reading the second run.
- **Re-ran** (EXECUTED, darwin-arm64; main's frozen set `SHA256SUMS 1556bbd5` and the pinned
  downloads cloned into my worktree with `cp -c`, every SHA-256 checked; no `build/lane.lock`):
  - The fast tier at `b86f847c`, holding the fast slot: `uv run pytest -m "not slow" -n 3`.
    Result: 2,959 passed, **1 failed**, 48 skipped, exit 1 (`build/095-review/fast.log`). The
    one failure is `test_packages.py::test_every_other_family_stages_what_it_staged_before`
    (H1). The ratchet line: lost 0, gained 1, grew 0. 41 blocked: trees this worktree lacks.
  - At `ab5cde5b`: `tests/unit/test_packages.py`, 71 passed. `ruff check` and `ruff format
    --check` on `src` and `tests`: clean.
  - By node id, at `b86f847c`, with the artifact set: `test_every_compiled_family_has_its_smoke_cover`,
    `test_upstream_files_are_well_formed` and `tests/checks/test_rules.py`. Result: 72 passed,
    1 skipped (prior-art clones).
  - Unit collection: 2,290 at the tip and 2,244 at `2a8091d7` (a `git archive` copy in my
    scratchpad). That is +46, as the claim block's `units = 46` says.
  - lxml's tree-free group JSON digest, computed with **main's** harness and TOMLs (the
    `git archive` copy): `f01719f332a7…406438d`. It equals the new fixture line and CI's value.
  - Four guest probes, one at a time, through `harness.guest.run`. Each used the snapshot,
    `SCIPY_XSLOW=1` and the kit's wheels as guest files. Scripts are in my scratchpad; outputs
    are `build/095-review/probe-*.txt`:
    - `test_betainc`'s body at `clock_step_ns = 100_000`: it ends in 54.2 G and passes.
    - The same at the default 1 µs: out of fuel at 300 G.
    - `test_betaincc`'s body at 100 µs: it passes.
    - `test_support_alternative_backends_hypothesis` for `yn` and for `hyp1f1`, with no shrink
      phase and verbose examples, at the default clock: each ran out of fuel at 60 G.

## The first run's red jobs (found here, fixed in `ab5cde5b`)

Run `39705963592` (on `b86f847c`) had two red jobs: `judge (ubuntu-24.04, own-rest)` (job
119586635992) and `judge (macos-15, own-rest)` (119586635868). Each was "1 failed, 1612 passed".
The failure was `test_every_other_family_stages_what_it_staged_before`, with "lxml's group JSON
changed" (`b439e137…` wanted, `f01719f3…` got). That is not a growth line or G7. My fast tier
failed on the same row. The gather and the release half were skipped, so that run has no
`release-record-1`. Everything else was green, including:

- every Windows leg;
- `upstream-sci-smoke-a`: 2 passed, 4 xfailed, job 201 s;
- `upstream-sci-smoke-b`: 2 passed, 8 xfailed, job 178 s.

Both smoke jobs are within the 360 s bound. Their ratchet line: lost 0, gained 2, grew 0.

## Acceptance criteria against evidence

1. **The rules** — met. Each variant is a parametrized row of
   `test_a_malformed_key_fails_with_its_own_line`, plus the clock, cover and must-cover rows
   (READ). The rules row passes on the three real TOMLs with the product's packages passed in
   (EXECUTED).
2. **The derived run on a synthetic tarball** — met. The valid output is staged with its facts
   on `derived_row` alone. Exit 1, nothing, an empty archive, a link, past the bound and past the
   cap each fail with their own line. The output is read with `lstat` and opened as a zip on the
   host, never through a link (READ). The rows pass in the fast tier (EXECUTED).
3. **The survey, then the baseline** — met (READ). The memo and its delta were reviewed before
   the build.
4. **The lists and gaps complete** — met for the normal tier: the smoke groups' xfails match
   their gaps on CI (EXECUTED, run 1). For the release tier, met by the builder's local passes 1
   to 4 (READ). The first CI run of the release tier is the dry run on main.
5. **Fuel repeats** — met as written (READ): the four smoke groups were run twice, equal to the
   instruction, and `sameness.py` exited 0. Every release group was measured once.
6. **Nothing else moves** — met at `ab5cde5b`. It was not met at `b86f847c` (H1). The fast
   tier's ratchet shows lost 0 and grew 0 (EXECUTED).
7. **The shards and the partition** — met, by my own count (EXECUTED, `tomllib`):
   - All 265 groups are in exactly one shard. The four smoke groups are in two Linux shards; the
     261 release groups are in 104 `release` shards.
   - No shard of more than one group is past 725 G with the derived run counted. 13 shards each
     hold one group past it; the largest is 3,023 G.
   - Smoke fuel: scipy 461.9 G (within the 500 G budget), scikit-learn 257.3 G and statsmodels
     135.8 G. All four together are 855.0 G.
   - The partition row by pytest's own collection passes (EXECUTED).
8. **The fetch** — met. The three fetch rows pass (EXECUTED).
9. **The tie and the stage** — met. The pin row and the staged-`__init__` row pass (EXECUTED).
   The base record shows the pin row failing first (READ).
10. **`packages.toml`** — met. All three are `suite`, and no entry names 095. Three citation
    allowances were retired, which tightens the rules (READ; the rules pass, EXECUTED).
11. **The fast tier and the lint** — met at `ab5cde5b` (lint EXECUTED; the fast tier at
    `b86f847c` was red only on H1's row, which passes at the tip). Not met at `b86f847c`.
12. **The branch's run** — for run `39708064741`, see *The run*. No `release-tier: true` dispatch
    was made (READ). The release groups were measured locally by node id (READ).
13. **The lane's dry run after landing** — not yet; it is the pre-tag dry run on main.

## Rule 4: never weaken the judge

- **The six deleted class lists are 095's own.** None of the three families has a file under
  `tests/upstream/expected/` at `2a8091d7` (EXECUTED: `git ls-tree` gives 0). In `0712a876`,
  git shows each as a rename to a regrouped group's list, and the members are kept:
  - `scipy-optimize-1`'s nine members are exactly `-1-1`'s and `-1-2`'s together;
  - `scipy-special-mpmath-8`'s `test_ci_complex` and `test_spherical_in` are now in `-10` and
    `-37`;
  - the other four are 100 % renames.
- **No allowance on main is loosened.** Against main, `tests/known_gaps.toml` has 507 lines
  added and 0 deleted. No `expected/` file of another family changes. `packages.toml` changes
  only the three `later` entries. `test_rules.py` only removes allowances.
- **The judge-hash line** reads "judge changed: tests/checks/test_rules.py,
  tests/checks/test_v1_3_upstream_suites.py, tests/fixtures/upstream-stages.json and 95 more".
  The lane's `--accept-judge` text in *For the lane, as built* covers it.
- **The `ab5cde5b` fix is sound, and the row still checks what it claims.**
  - With lxml's tree present, the full JSON and the staged list are compared, as before.
  - Without the tree, lxml's JSON is compared with the tree-free digest.
  - That digest is main's harness's own value: I recomputed it from a clean `git archive` of
    `2a8091d7` (EXECUTED). It is not a value read off the branch.
  - Only lxml sets `keep_from_test_suite`. The other eight families' digests matched on CI
    without trees, so their JSON does not depend on the tree. A second key for them is not
    needed.
  - One residual: on a host without lxml's tree, the classes `keep_classes` reads from that
    tree are not compared. That is the same reach main's own runs have there. The lane's darwin
    tree, which holds the trees, compares them.

## Rule 3: the check before the code

- The first builder's base run fails 39 new rows on the base harness: "39 failed, 79 passed"
  (`the-build/data/base-unit-run.txt`, READ).
- The trap row's failing assertion on the unfixed harness is quoted in the Landing notes
  (`'pkg/a/tests/test_x.py::t' == '/upstream-scipy/tree/…'`, READ).
- The stage-digest row (criterion 6) is a sameness check: its fixture was recorded with the base
  harness, so it passes on the base by design.

## The release-tier claim block

- **It is complete.** The block's counts agree with what I counted in the TOMLs (EXECUTED):
  - groups: 261 (172 scipy, 38 scikit-learn, 51 statsmodels);
  - measured fuel: 63.66 T, 9.72 T and 12.84 T;
  - traps: three;
  - `units = 46`.
- **It is consistent.**
- **Its wildcards excuse no more than 095's own rows.** `test_upstream_suite[scipy-*` and its
  five siblings also match the four smoke rows, which are normal-tier rows. But the release
  acceptance runs `sameness.py --tier-rows release`, which reads only release-tier rows. And a
  `new` entry explains only a row the previous record lacks. So no smoke-row loss and no
  existing row's change can hide behind them. The `[scipy-hypothesis-*` trap wildcard matches
  only these three traps.

## The two items the builder named

- **`clock_step_ns = 100_000` on betainc and betaincc.** The key is guarded well:
  - it is a release group's key only, from 1 µs to 1 ms, with a reason;
  - the judge holds such a group to exactly one outcome (`clock_findings`);
  - the split puts each of the two tests first, alone.

  But the step changes what the test proves (M1), and its reason text is wrong (L1).
- **The `-k` `RecursionError` at about 300 terms.** Every one of the 261 groups ran in the guest
  during the build's measured passes. So every planned expression compiled there; the deepest is
  81 levels.
  - A later re-split past the limit fails loudly. pytest exits 4, and the judge reports it as a
    finding. Nothing passes vacuously.
  - The partition holds whatever the keywords select. The last group of each split takes `not
    (every earlier)`. So `ksim.py`'s model of pytest's matching affects only balance and empty
    groups, and an empty group is red (exit 5).

  No finding.

## Findings, most severe first

1. **H1 — fixed in `ab5cde5b`. The stage-digest row was red wherever lxml's tree is absent**
   (`tests/unit/test_packages.py:753`).
   - The defect: lxml's group JSON names classes read from its unpacked tree
     (`keep_from_test_suite`), but the fixture held only the digest taken with the tree present.
   - Failure: the own-rest jobs on Linux and macOS in run `39705963592`, and my fresh
     worktree's fast tier, gave "lxml's group JSON changed" (`f01719f3…` against `b439e137…`).
     It would have turned every release run red.
   - Fix (done): a second, tree-free digest, used only when the tree is not staged. Verified
     equal to main's harness above.
2. **M1 — The two clock-stepped mpmath tests compare about half their points, and nothing says
   so** (`tests/upstream/scipy.toml:772-791`, `README.md`).
   - How the test works: `time_limited` gives each mpmath reference value 0.5 s, timed by a
     clock read on every trace event. A reference value that times out becomes `nan`, and the
     comparison drops that point (`nan_ok=True`).
   - What my probe shows (EXECUTED, `probe-betainc-100us.txt`, `probe-betaincc-100us.txt`):
     at 100 µs per read, the 5,832 points leave 240 where scipy's value is not `nan`.
     - `test_betainc`: 110 of those 240 time out, 114 are compared, and 16 raise in mpmath.
     - `test_betaincc`: 149 time out, and 91 are compared.
   - Native comparison: natively the limit is `SIGALRM` over 0.5 s of untraced time
     (`_mptestutils.py:370`). So natively far fewer points drop out (INFERRED).
   - At the default 1 µs, `test_betainc` runs past 300 G (EXECUTED).
   - The result: the passes are real, but they are passes over 114 and 91 points, not 240. The
     README's "they run with the guest's clock advancing 100 µs a read" does not tell a reader
     that.
   - Evidence that would close it: the two counts written into each group's `clock_reason`
     (the builder's, a judge file), the README sentence, and the memo's build section. Or a
     step chosen by those counts, with its price.
3. **L1 — The betainc and betaincc `clock_reason` is the conv-method test's text**
   (`tests/upstream/scipy.toml:782,791`).
   - The text says "repeats a call until the clock has advanced 0.5 ms". These two tests do not
     do that.
   - Fix text, for both: "mpmath's reference value for each point is limited to 0.5 s by a clock
     read on every trace event; at the judge's 1 µs step the test runs past 16 T; at 100 µs a
     read it ends, comparing 114 of its 240 points (betaincc: 91), the rest timed out" (with
     M1's counts).
4. **L2 — The three hypothesis traps' cause can now be written in**
   (`tests/upstream/scipy.toml` `[[trap]]`, `tests/known_gaps.toml:1030-1046`, README).
   - Their reasons say "why … is not read yet". My no-shrink, verbose probes read most of it
     (EXECUTED).
   - **Not a failing example being shrunk.** No example failed before the 60 G cap.
   - **The examples that do not end** draw `intp` values near ±2³¹: `intp` is 32-bit on wasm32.
     - `yn`'s third example is `yn` with orders −2,147,425,343 … 894,018,349.
     - `hyp1f1`'s ninth is `hyp1f1(−2,147,446,720, 669,248,800, −2,147,474,440)`.
   - **Why they take so long** (INFERRED): Cephes' `yn` runs a recurrence over |n| steps, and
     `hyp1f1`'s series runs long for parameters this size.
   - `lpmv` was not probed.
   - Fix text, for `yn` and `hyp1f1`: "a derandomized example draws intp (32-bit on wasm32)
     values near ±2³¹ as the function's integer parameters, and the call runs past the trap's
     cap; no example fails". The README sentence "why … is not read yet" changes to match.
     `README.md` stays the closer.
5. **L3 — *For the lane, as built* drops three lane items from *For the lane***
   (the specification, line 1283). Write in:
   - "The lane widens 088's roadmap line to name scipy's seven test-only C modules and
     `_test_deprecation_call` (the gaps `scipy-lib-to-fft-test-only-modules` and the
     `[[not_selected]]` entry cite it; the line names numpy's and CPython's only)."
   - "The lane reserves a number for the uarray `get_native_id` product finding; it becomes
     `scipy-lib-to-fft-no-native-id-uarray`'s closer in place of `README.md`."
   - "074's line may name scikit-learn's three `mmap` files and scipy's three
     `test_cython_abi.py` files."
6. **L4 — Two self-check items.**
   - The run id is not in the Landing notes. The self-check says it is "in the next
     context-only commit's line below", but no such commit exists.
   - The Kind line lists `context/progress/README.md` and `context/roadmap.md` as changed;
     neither changes.
   - Fix: name runs `39705963592` (red, H1) and `39708064741` in *The build, completed*. Strike
     the two Kind entries, or say they are the lane's (L3).
7. **N1 — The release-tier legs are first run on the dry run on main.**
   - 13 shards hold one group past 725 G. The largest, 3.02 T, is about 940 s at 102's slow
     Linux rate (0.31 s per G) plus setup. That is past Decision 12's 360 s, but under the
     `judge-release` job's 30-minute timeout.
   - 116 release legs run at `max-parallel: 18`.
   - The `artifact-ids` expression is 7,160 characters.
   - All of this is INFERRED until that run.
8. **N2 — The two release-only covers (`sklearn.ensemble`, `sklearn.manifold`)** follow the
   cover rule's item 5: no golden line, and every file past a smoke file's reach (READ). I
   accept them.

## Constitution checks

- **§4 constraints:**
  - No `src/`, `scripts/`, `recipes/` or `downloads/` line changes; no artifact byte; no
    patch.
  - Every guest input is pinned.
  - No check reads a wall clock: `clock_step_ns` is a count.
  - Prior art: none copied.
- **Code speaks for itself:**
  - No added comment or docstring in `tests/` or `.github/` names a specification, review,
    finding or `context/` path.
  - The `(088)` and `context/roadmap.md` strings are `reason` and `closes_with` data.
  - The citation rule passes (EXECUTED).
- **Structure:** `src/` does not change, so the structural rubric does not apply. The Kind line
  correctly carries no **structural**.
- **§7 never-do list:** nothing tripped.

## The run

Run `39708064741` on `ab5cde5b` (head SHA checked), read back with `gh run view --json jobs`:
43 success, 1 failure, 6 skipped.

- **The one red job is `judge (ubuntu-24.04, upstream-plot-g)`** (job 119593308520), one of
  066's shards, not 095's. It failed in `tests/upstream/fetch.py --shard` while fetching the test
  kit's wheels from the package index: `urllib.error.URLError: [SSL:
  UNEXPECTED_EOF_WHILE_READING]` (`build/095-review/ci2-plot-g.log`). It is a download outage. It
  is not a judge verdict, not a growth line and not G7. No check ran in that job.
- Because of it the gather was skipped, so this run has **no `release-record-1`**:
  `gh run download -n release-record-1` finds no artifact. The release legs, attest and publish
  were skipped as on any branch run.
- **H1's fix holds on CI.** `own-rest` is green on Linux and macOS. Every Windows leg is green.
- **095's normal-tier shards are green:** `upstream-sci-smoke-a` in 189 s and
  `upstream-sci-smoke-b` in 178 s, both within 360 s.
- Following the owner's rule on upstream hosts, I did not re-run the job. Re-running it once,
  later, by hand is the lane's or the builder's call (`gh run rerun 39708064741 --failed`).

## Disposition (filled in by the author, then confirmed by the reviewer)

1. H1 — fixed in `ab5cde5b` (the tree-free lxml digest; confirmed above).
2. M1 — open: the builder writes the counts in (a judge-file text edit and the README), or
   says why not.
3. L1 — open (the builder's, with M1).
4. L2 — open (the builder's; text given).
5. L3 — open (context only; the text above, for the builder or the lane).
6. L4 — open (context only).

## Verdict

Lands once M1 is written in (the two clock-stepped tests' compared-point counts, in their
`clock_reason`, the README and the memo). Before the lane accepts, `upstream-plot-g` of run
`39708064741` is re-run once and read green, so that the gather runs and its `release-record-1`
is read. H1 is fixed in `ab5cde5b`, and the Lows need no further round.
