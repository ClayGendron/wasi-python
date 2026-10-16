# Review of 002 — The progress harness

- **Date:** 2026-10-16
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author; given the
  constitution, `AGENTS.md`, the specification, its spec review, the
  three research memos and the change, not the author's summary. The
  landing notes were checked, not trusted.
- **Reviewed:** the uncommitted change on top of `2828f2c` (modified
  `AGENTS.md`, `README.md`, `context/README.md`, the spec's landing
  notes, `pyproject.toml`, `uv.lock`, `tests/test_api.py`; new
  `tests/harness/`, `tests/checks/`, `tests/unit/`, `tests/jobs/`,
  `tests/conftest.py`, `tests/known_gaps.toml`, `context/progress/`,
  `context/embedders.txt`, `.gitattributes`).
- **Re-ran (EXECUTED, this machine, darwin-arm64):**
  - `uv run pytest -q -p no:cacheprovider` → `wasi_python v1: 14/67 pass ·
    8 gap · 45 blocked · 0 fail (unit suite 115/115)`; `129 passed, 45
    skipped, 8 xfailed`; ratchet `lost 0 · absent 0 · unrun 0 · gained 0 ·
    grew 0`; exit 0. The progress section is 12 lines.
  - `uv run pytest -q -p no:cacheprovider -m "not slow"` → `13/67 pass ·
    8 gap · 42 blocked · 0 fail · 4 deselected`; `128 passed, 42 skipped,
    4 deselected, 8 xfailed`; ratchet `… not selected 1`; exit 0.
  - `uv run ruff check src tests` → `All checks passed!`, exit 0.
  - `uv run ruff format --check src tests` → `35 files already
    formatted`, exit 0.
  - `uv run python tests/jobs/regen.py --check` → `ok numpy_csv`, `ok
    pandas_csv`, `ok numpy_random`, exit 0.
  - `--collect-only tests/checks` → 67 items; the 56 function names equal
    the 56 in the Design table (`diff` empty).
  - The accepted judge hash equals the judge hash of the tree now;
    `accepted.json` holds 14 `pass` and 8 `gap`; `history.jsonl` line 1
    has `reason: "initial baseline"`, `prev: null`, `platform:
    darwin-arm64`, `wasmtime: 49.0.0`.
  - Tamper experiments ran in a copy of the tree (with its own copy of
    `.git`) in the session scratch directory, using this repository's
    `.venv/bin/python -m pytest`. The real `context/progress/*` and
    `tests/known_gaps.toml` were hashed before and after (`shasum -a 256
    -c` → all OK) and `git status --short` is unchanged. Only the
    git-ignored `build/progress/latest.json` was rewritten by the runs
    above.

## Acceptance criteria against evidence

1. *`uv run pytest` exits 0 with no artifacts, ≤ 25 lines, writes
   `latest.json`* — **met here, not met on a fresh clone.** Here: exit 0,
   12 lines, `build/progress/latest.json` written. In a copy without the
   git-ignored `context/prior_art/` clones and `build/oracle/`, both tiers
   exit 1: `RED: 1 accepted pass(es) blocked` (fast) and `2 …` (full).
   See finding 3.
2. *Every node id collected, with its file's area, none `fail`* — met
   (67 items, names equal the table, each file sets its `goal` area).
3. *Every `blocked` names a false need; every gap an existing closer* —
   met. The plugin re-evaluates the predicate (`plugin.py:185-199`);
   `test_known_gaps_are_well_formed` passes. But a goal check can reach
   the `gap` state without any gap entry (finding 4).
4. *Each detector has a unit test both ways* — met for `scan.py`,
   `wasm.py`, `pins.py`, `paths.py` (MANIFEST, licences), `jobs.py`
   (`test_golden_comparison_…`) and `scoreboard.py`.
5. *Plugin end-to-end self-tests* — met in substance: 17 pytester cases
   cover every listed state and flag except three, which are pure-function
   tests in `test_scoreboard.py` (gained, carry-over, another platform's
   fuel), as the landing notes say. The pytester "path-limited run"
   (`test_plugin.py:172-182`) runs a file with no goal checks, so it
   exercises the plugin's early return (`plugin.py:272`), not the
   `outside` classification.
6. *Driver self-tests* — met. WAT modules cover dispatch, the door's
   three codes, exits, a third import, the fuel cap (exactly 10 000),
   random and clock; Brett's build ran here (no skips: unit suite
   115/115) for stdout, root isolation, a 10⁹ cap and two `-I` runs
   within 0.01%.
7. *Each v1.1 check passes on a good synthetic set and fails on a bad
   one* — met (`test_artifact_rules.py`, and `test_checks_wiring.py`
   running the real check file in a subprocess).
8. *Goldens exist, `regen.py` reproduces them, the oracle check passes*
   — met (`regen.py --check` exit 0; v1.3 shows 1/10 pass in the full
   run, which is the oracle check).
9. *`accepted.json` with "initial baseline", history line 1* — met.
10. *ruff clean on `src tests`* — met.

## Findings, most severe first

1. **A gap admits any number of new violations of its rule, with no
   judge change** (`tests/harness/plugin.py:201-211`,
   `tests/known_gaps.toml:8`, `tests/checks/test_rules.py:23`) — the
   scanner checks join every finding into one message, and a gap matches
   a substring of it, so one known finding (or the constant prefix)
   covers all others.
   Failure (EXECUTED, scratch copy): add `src/wasi_python/vfs_bridge.py`
   containing `vfs` and a new `scripts/77_new.sh` that runs a bare
   `python3`. `pytest tests/checks/test_rules.py` → both checks stay
   `gap` (`embedder names in code: 57 hits, first: …`; the
   bare-python message still contains `scripts/00_download.sh:17`),
   ratchet clean, exit 0, judge hash unchanged. The embedder gap's
   `match` is the assertion's fixed prefix, so it is an unconditional
   xfail for any `AssertionError`. The same holds for the other
   scanner gaps: a new pin without a URL (`…_literal_url`, any finding
   sorted with `pandas-3.0.6.tar.gz`), a second missing recipe path
   (`…_names_exists`, matches only the first), a removed macOS
   toolchain pin (`…_linux_and_macos`), and a download script that
   also writes `SHA256SUMS`. This is spec-review finding 12 coming back
   through aggregation. Fix: a gap must pin the whole failure, not a
   fragment: either `match` must equal the complete message (with its
   count), or the gap lists every expected finding and the check fails
   on any finding not listed; and `test_known_gaps_are_well_formed`
   rejects a `match` that is the check's constant prefix.

2. **Files that steer pytest are outside the judge, so the ratchet can be
   silenced without a judge change** (`tests/harness/paths.py:57-66`,
   `tests/harness/plugin.py:58-60`) — a root `conftest.py`, `pytest.ini`,
   `tox.ini` or `setup.cfg` (any of which pytest reads before or instead
   of `pyproject.toml`), and the `--known-gaps` / `--progress-dir`
   options, change the verdict without touching a judging file or
   printing anything.
   Failure (EXECUTED, scratch copy): a 9-line root `conftest.py` with a
   `trylast` `pytest_runtest_makereport` wrapper that flips one goal
   check's failure to passed, plus a unit test that reads `time.time()`.
   `test_no_test_reads_a_clock` (an accepted pass) is recorded `pass`;
   ratchet `lost 0`; exit 0; judge hash equal to the accepted one; no
   "judge changed". Without the conftest the same tree is `LOST … RED`.
   Likewise `--known-gaps /elsewhere.toml` turns any not-yet-accepted
   failure into a `gap` that `test_known_gaps_are_well_formed` never
   sees. Fix: hash every `conftest.py` and every pytest config file the
   repository could hold (or fail a `rules` check if any exists outside
   the three known conftests and `pyproject.toml`); record
   `config.inipath` in the run and fail unless it is `pyproject.toml`;
   print a line whenever `--known-gaps` or `--progress-dir` is not the
   default, and refuse `--accept` with a non-default gaps file.

3. **A fresh clone is red on its first run, which trains `--partial`**
   (`context/progress/accepted.json`; `tests/checks/test_rules.py:38-41`;
   `tests/checks/test_v1_3_data_stack.py:101-103`) — the baseline
   protects two passes whose needs are git-ignored local state
   (`context/prior_art/` clones, `build/oracle/`).
   Failure (EXECUTED): a copy of the tree with `downloads/SHA256SUMS`
   but no prior-art clones, no `build/` → `uv run pytest -m "not slow"`
   exits 1 with `RED: 1 accepted pass(es) blocked (say --partial to
   allow)`; the full run exits 1 with 2. Criterion 1 ("a source
   checkout with no artifacts") fails on every new machine, CI job and
   agent sandbox, and AGENTS.md's first step ("Start every session with
   `uv run pytest -m "not slow"`") is red before any work. `--partial`
   then allows every blocked pass, so the habit hides real unrun losses.
   Fix: do not protect passes whose need is local tooling state (mark
   such needs `local`, and treat their accepted passes turning blocked as
   reported, not red), or block the oracle and prior-art checks on a
   predicate that a fresh clone can meet; and run criterion 1 in a clean
   clone before landing.

4. **A goal check marked `xfail` without a gap entry reads as `gap`**
   (`tests/harness/plugin.py:201-211`) — the `else` branch records any
   xfailed report as `gap` with an empty closer when `state.gaps` has no
   entry for it.
   Failure (EXECUTED, scratch copy): append to
   `test_v1_5_rebuild_from_pins.py` a check that calls
   `pytest.xfail("not yet")` and one decorated `@pytest.mark.xfail`
   that fails. Both are `gap` (`closer: ''`, scoreboard `gaps close
   with: ? 2`), exit 0. Decisions 3 and 4 make `gap` mean "failed in
   exactly the way a gap entry names"; this is a gap with no entry,
   no match and no closer. It shows only as "judge changed", which is
   reported, not red. Fix: when `gap is None` and the report carries
   `wasxfail`, record `fail` ("xfail without a gap entry") and turn the
   report into a failure; add the pytester case.

5. **"Absent" is misclassified both ways** (`tests/harness/plugin.py:121`,
   `plugin.py:137`; `tests/harness/scoreboard.py:96-101`,
   `scoreboard.py:62`, `scoreboard.py:154`, `scoreboard.py:166`) — a file
   counts as collected only through goal-marked items, and a node-id
   selection counts the rest of its file as gone.
   Failure (a), a false green (EXECUTED, scratch copy): set `pytestmark
   = []` in `test_rules.py`. Its 11 accepted passes become "not selected
   12", not absent; the checks now run as unit tests, where a plain
   `pytest.skip` is silent. Fix: record every collected file (goal or
   not), so a file collected without its accepted checks is absent.
   Failure (b), a false red with harmful advice (EXECUTED):
   `pytest tests/checks/test_rules.py::test_ruff_check_is_clean` →
   `absent 10`, `RED: 10 accepted check(s) absent (retire them with
   --retire)`, exit 1. Following the advice works: the same command
   with `--accept tidy` and twelve `--retire` flags (against a scratch
   `--progress-dir`) exits 0 and drops twelve still-existing, passing
   checks from the protected set; nothing refuses retiring a check that
   is still defined. Fix: treat items outside an explicit node-id
   selection as `outside`; call a check absent only when its function
   is gone from its file (as `test_known_gaps_are_well_formed` already
   tests); refuse `--retire` of a check that is still collected or still
   defined.

6. **The judge and two checks are not portable to Windows**
   (`tests/harness/paths.py:115`, `tests/harness/artifacts.py:35`,
   `.gitattributes:1`) — paths are keyed with the OS separator and
   judging files are hashed as checked out.
   Failure (INFERRED from the code): on Windows `judge_files()` keys are
   `tests\harness\plugin.py`, so every file differs from the darwin
   baseline; with Git for Windows' default `core.autocrlf=true` every
   judging text file is CRLF and hashes differently too. Every Windows
   run reports the whole judge changed, and the win32 acceptance that
   `test_same_bytes_passed_on_three_systems` needs requires
   `--accept-judge`, after which macOS reports the judge changed.
   `sums_errors` builds `LICENSES\cpython.txt` and fails against a
   `SHA256SUMS` that lists `LICENSES/cpython.txt`; `recipe_files()`
   hashes CRLF copies of `recipes/` and `scripts/`, so a Linux-built
   `MANIFEST` is "stale" on Windows. Fix: key by `as_posix()`;
   `.gitattributes` `* text=auto eol=lf` (or `-text`) for the judging
   files, `recipes/` and `scripts/`.

7. **The zero-patch and licence-content checks never verify the
   tarball's pin** (`tests/harness/pins.py:45-50`,
   `tests/harness/paths.py:261-277`) — `source_pair` reads `SHA256SUMS`
   only for names, and `licence_source` takes any downloaded file with
   the right prefix, pinned or not, and for CPython falls back to any
   `Python-*.tar.xz`.
   Failure: re-pack `zlib-1.3.1.tar.gz` with the same edit made in
   `build/zlib-1.3.1/zconf.h`; `test_source_tree_matches_its_tarball[zlib]`
   passes against a tarball that is not the pinned one. AGENTS.md:
   "verified before use". Fix: compare `sha256_file(tarball)` with the
   pin before use, and fail (not block) on a mismatch; take the licence
   source only from a pinned, verified file of the `MANIFEST` version.

8. **The scoreboard still implies §4.12 is fully checked**
   (`tests/harness/scoreboard.py:32-35`) — the "not machine-checked"
   line lists wasi-libc and llvm-runtimes but not bundled sub-licences
   (pandas' `LICENSES/`, CPython's libmpdec and expat), files a build
   adds inside a source tree, or components whose pin is missing.
   The spec review accepted the non-adoption of bundled sub-licences "on
   one condition: say it on the scoreboard", and Decision 17 lists all
   three. Failure: a green licence check with pandas' bundled notices
   absent, and nothing on the scoreboard says they were not looked at.
   Fix: add the three items to `NOT_MACHINE_CHECKED`.

9. **The 25-line cap can cut the RED line and the growth lines**
   (`tests/harness/scoreboard.py:319-335`, `tests/harness/plugin.py:340-341`).
   Failure (EXECUTED, `scoreboard.render` with 12 fails, 3 lost, 3
   absent, 1 growth): 25 lines ending at `ABSENT f`; the `GREW` line,
   the `RED:` line and "not machine-checked" are dropped. The exit code
   stays 1, but the one line saying why is gone. `--accept` also appends
   a 26th line. Fix: reserve the last lines for the ratchet line, `RED:`
   and the accept line, and cap the FAIL/LOST/ABSENT/GREW lines around
   them.

10. **Smaller points** — each may be fixed or answered in writing.
    - `paths.py:209`: a `package` version is matched as a prefix of the
      pin name, so `package numpy 2.5` passes against `numpy-2.5.2.tar.gz`.
      Require a delimiter after the version.
    - `scoreboard.py:184-190`: a metric a check stops recording is
      silently dropped from `accepted.json` (and never compared); say so
      in the ratchet line.
    - `tests/jobs/oracle/pyproject.toml:2` and Decision 11 call uv 0.9.22
      "pinned"; nothing pins it (no `required-version`); the uv here is
      Homebrew's. Pin it or drop the word.
    - `needs.py:117`: `wasmtime-py` is a need that Decision 5's "fixed
      vocabulary" table does not list. Add it to the table.
    - `test_v1_1_artifact_set.py:99`: the newest wheel is chosen by string
      sort (`0.9.0` after `0.10.0`).
    - `test_v1_4_embedding.py:72-74`: each runner check leaves a
      directory in `build/harness/`; `build/harness/accepted.bak` from the
      author's tamper test is also left behind.
    - `plugin.py:272`: `--accept` on a run that collects no goal check
      does nothing and says nothing.
    - `plugin.py:179-181`: the unit-suite count shows skips as not passed
      (`108/114` in a copy without the reference build), which reads as
      failures.
    - Landing notes say "14 to 16 scoreboard lines"; the runs here print
      12 (13 with the accept line). Accurate in spirit; correct the
      number.

## Constitution checks

- §4.1 zero patches — no upstream tree is touched. The new zero-patch
  check holds for tarball files but trusts an unverified tarball
  (finding 7).
- §4.2 pinned and hashed — wasmtime-py is in `uv.lock`; the oracle is
  its own locked project with 45 SHA-256 hashes, fetched only by
  `regen.py --online`. uv itself is called pinned but is not
  (finding 10). Holds otherwise.
- §4.3 one target — the harness is host-side test code. Holds.
- §4.4 two imports — `wasm.wall_errors` enforces WASI preview1 plus
  `host::call` of type `(i32,i32,i32,i32)->i32`; shadowing `random_get`
  and `clock_time_get` changes host bindings only. Holds.
- §4.5 embedder-neutral — no hit in `src/` or `tests/` (EXECUTED:
  `embedder_hits` → 55 hits, all in `recipes/`, `scripts/`,
  `fixtures/`); the name lives in `context/embedders.txt`. Holds. The
  check that guards it is a blanket gap today (finding 1).
- §4.6 artifact set — the harness reads the set and `LICENSES/` as
  Decision 12 says; nothing is published. Holds.
- §4.8 downloads untrusted — every extraction is under
  `build/harness/` (`tests/unit/test_pins.py:44,81,110`); the oracle's
  caches, interpreter and venv are under `build/oracle/`. Tarballs are
  read in memory by `tarfile` without extraction in the checks. Holds;
  verification before use is missing (finding 7).
- §4.9 tests count — no clock read in `tests/checks`, `tests/unit`,
  `tests/jobs`, `tests/test_*.py`; the plugin reads one only for the
  history timestamp (Decision 8). Holds.
- §4.10 claims carry evidence — the landing-note numbers reproduce,
  except the line count (finding 10).
- §4.12 licences — see finding 8.
- §4.13 tooling — ruff and pytest green; wasmtime added with its reason.
  Holds.
- §4.14 git — `--accept` writes tracked files and never commits. Holds.
- §5.6 review — this review; the landing notes still read "to be filled
  in".
- §7 never-do list — nothing tripped. No unpinned fetch, no download
  installed into the system, no prior-art code, no commit.

## Disposition (filled in by the author, then confirmed by the reviewer)

By the author, 2026-10-16. All fixes are in the uncommitted change;
each attack the review ran is now a self-test that fails without its
fix. Re-ran: `uv run pytest -q -p no:cacheprovider` → `143 passed, 45
skipped, 8 xfailed`, exit 0; in a fresh `git clone` with the change
overlaid → exit 0 on both tiers (`unrun locally 2`).

1. Gaps admit new violations — **fixed.** Every check reports
   `N finding(s), digest <sha of the sorted findings>`
   (`scan.report`), every gap's `match` names that phrase, and
   `test_known_gaps_are_well_formed` refuses a gap without a digest. A
   new finding or a fixed one changes the digest, so the gap fails
   differently and the run is red until the gap is edited (a judge
   change). Self-test: `test_a_gap_admits_exactly_its_findings_and_no_new_one`
   (one more, one fewer).
2. Files that steer pytest outside the judge — **fixed.** The judge is
   all of `tests/`, `.gitattributes`, `pytest.ini`, `tox.ini`,
   `setup.cfg`, and any `conftest.py` found by a walk that skips build
   output, downloads, clones and virtual environments
   (`test_the_judge_includes_any_conftest_and_pytest_config`).
   Non-default `--progress-dir`, `--known-gaps`, `--progress-latest`
   print `JUDGE INPUTS OVERRIDDEN` on the scoreboard and are recorded in
   `latest.json` (`test_overridden_judge_inputs_are_announced`).
   **Not fixed:** a plugin disabled with `-p no:harness.plugin`, or
   options injected through `PYTEST_ADDOPTS`. The first removes the
   scoreboard entirely, which is visible; the second can only deselect
   (reported as "not selected") or override the inputs above (announced).
3. Fresh clone red — **fixed.** An accepted pass blocked by a protected
   need (the artifact files, the runner) stays red; one blocked by
   local tooling (clones, the oracle, source trees, git) is "unrun
   locally", reported. Evidence: the fresh-clone run above, and
   `test_a_pass_blocked_by_local_tooling_is_not_red`.
4. `xfail` without a gap — **fixed**: `fail`, for both the marker and
   `pytest.xfail()` (`test_an_xfail_without_a_gap_entry_is_a_failure`).
5. Absent misclassified — **fixed.** Collected files now include
   files with no goal checks, so removing a `goal` marker makes its
   passes absent (`test_removing_a_goal_marker_makes_its_accepted_passes_absent`).
   Files named by node ids on the command line are not judged whole,
   and `--retire` accepts only absent checks
   (`test_a_run_narrowed_to_one_node_id_is_not_absent_and_cannot_retire`).
   Absence is judged against the session's root, not the repository's.
6. Windows — **fixed as far as can be done here**: judge keys,
   `SHA256SUMS` and `.cwasm` findings use POSIX paths; `.gitattributes`
   checks out every text file with LF. Not executed on Windows (no
   Windows host in this session); the three-systems check will be the
   evidence.
7. Tarballs not checked against their pins — **fixed**: the zero-patch
   check asserts the tarball's SHA-256 equals its pin before comparing;
   the licence rule trusts only the exact pinned file named by the
   MANIFEST, present and matching its pin, with no `Python-*` fallback
   (unit test: a mismatched pin makes zlib presence-only).
8. Scoreboard implies §4.12 is checked — **fixed**: the last two lines
   list bundled sub-licences, build-added files and presence-only
   components (Decision 17 too).
9. Line cap cuts RED and GREW — **fixed**: the ratchet, RED and
   not-machine-checked lines are reserved first and the FAIL lines give
   way (`test_the_ratchet_and_red_lines_survive_the_line_cap`).
10. Smaller points:
    - package version as a prefix — **fixed** (`paths.is_version_of`:
      2.5.2 does not match 2.5.20);
    - a metric no longer recorded — **fixed**: red
      (`test_a_metric_that_stops_being_recorded_is_red`, both levels);
    - "pinned uv" — **fixed in the text**: uv is the installed 0.9.22,
      not pinned by this repository;
    - `wasmtime-py` missing from the table — **fixed**;
    - wheel chosen by string sort — **fixed**: more than one wheel in
      `dist/` fails the check;
    - leftovers in `build/harness/` — **fixed**: runner roots use the
      session work directory, which is removed; the author's
      `accepted.bak` is deleted;
    - `--accept` with no goal checks — **fixed**: red, "collected no
      goal checks" (`test_accept_with_no_goal_checks_is_refused`);
    - unit-suite count — **fixed**: skips are shown;
    - "14 to 16" lines — **fixed**: the notes say 13, as counted.

### Confirmation by the reviewer, 2026-10-16

I checked the code and re-ran everything. I did not rely on the text
above.

**Re-ran (EXECUTED).**
- `uv run pytest -q -p no:cacheprovider` → `14/67 pass · 8 gap · 45
  blocked · 0 fail (unit suite 129/129)`, `143 passed, 45 skipped, 8
  xfailed`, exit 0.
- `-m "not slow"` → `142 passed, 42 skipped, 4 deselected, 8 xfailed`,
  exit 0.
- `ruff check src tests` and `ruff format --check src tests` are clean.
  `regen.py --check` → three `ok`, exit 0.
- The attacks ran in a fresh `git clone` of this repository with
  `git ls-files -co --exclude-standard` overlaid, in the session scratch
  directory. They used this repository's `.venv/bin/python -m pytest`.
- `context/progress/*` and `tests/known_gaps.toml` were hashed before
  and after (`shasum -c` → OK).

**Per finding.**
1. **Confirmed fixed.** A new `vfs` file in `src/` and a new bare
   `python3` script make both gaps "fail differently" (`57 finding(s)`
   ≠ `55`; `2` ≠ `1`). The run is exit 1. A side effect is new finding
   N2.
2. **Not fixed.**
   - The root `conftest.py` attack is now announced
     (`judge changed: … conftest.py …`). It is still green, but a judge
     change is reported, not red, by Decision 6, and `--accept` needs
     `--accept-judge`. That is acceptable.
   - But pytest 9.1.1 (the locked version) also reads `pytest.toml`,
     `.pytest.toml` and `.pytest.ini`, and none of them is a judging
     file. Decision 14 says the judge covers "every file that can …
     steer pytest", which is not true.
   - The residual reasoning is also wrong. `PYTEST_ADDOPTS` can do more
     than deselect: it can load an arbitrary plugin.
   - See N1.
3. **Confirmed fixed.**
   - In the fresh clone both tiers exit 0, with `unrun locally 1` (fast)
     and `unrun locally 2` (full).
   - `PROTECTED_NEEDS` keeps the artifact files and the runner red.
   - One gap in which needs are protected is listed as N3.
4. **Confirmed fixed.** `pytest.xfail()` and an `xfail` marker without
   a gap entry are both `fail`, and the run exits 1. A non-strict xfail
   that passes is recorded `pass`, which is right.
5. **Confirmed fixed.**
   - With `pytestmark = []`, the run reports `absent 11`, RED, exit 1.
   - A run narrowed to one node id reports `not selected 13` and exits 0.
   - `--retire` of a check that is still present is refused with
     "not absent". I ran this against a scratch `--progress-dir`, and
     the scoreboard printed `JUDGE INPUTS OVERRIDDEN`.
   - A contrived residual remains: a file named both whole and by a
     node id is treated as narrowed. That is acceptable.
6. **Fix confirmed in the code; the reasoning for not executing it is
   accepted.**
   - Judge keys, `SHA256SUMS` and `.cwasm` findings use `as_posix()`.
   - `.gitattributes` has `* text=auto eol=lf`.
   - No Windows host was available. The first win32 acceptance will be
     the evidence. A wrong judge there shows as "judge changed", which
     is visible, not silent.
7. **Confirmed fixed.** The zero-patch check compares the tarball's
   SHA-256 with its pin before reading it. The licence rule takes only
   the exact pinned, verified file of the `MANIFEST` version.
   - Residual: a download that does not match its pin silently drops
     that component to presence-only. It does not fail. The check's
     message lists presence-only components, so this is acceptable.
     Calling the mismatch out by name would be better.
8. **Confirmed fixed.** Both "not machine-checked" lines list
   presence-only components, bundled sub-licences and files a build
   adds inside a source tree.
9. **Confirmed fixed.** I rendered the scoreboard with an overrides
   line, 12 fails, 4 lost, 4 absent and 4 growth lines. It is 25 lines,
   and the ratchet, `GREW`, `RED` and both not-machine-checked lines
   survive; the FAIL lines give way. The accept line can still be a
   26th line, but only on a green run. That is acceptable.
10. **Confirmed**, with two notes:
    - `is_version_of`, the dropped-metric red, the `wasmtime-py` table
      row, the one-wheel rule, the skip count and the "13 lines" text
      are all in place.
    - `--accept` on a run with no goal checks → `RED: --accept refused:
      this run collected no goal checks`, exit 1.
    - Note: `build/harness/tmpyedx4wr0` is still there, and
      `accepted.bak` is gone.
    - Note: the uv wording was fixed in the text only. That is
      acceptable.

**New findings.**

N1. **pytest config files and plugins outside the judge still silence
    the ratchet** (`tests/harness/paths.py` `JUDGE_PATHS`; finding 2's
    residual).
    - Failure 1 (EXECUTED, scratch clone):
      - Add a `.pytest.toml` that copies the `[tool.pytest]` settings
        and adds `pythonpath = ["tests", "tools"]` and
        `addopts = ["-p", "quiet"]`.
      - Add `tools/quiet.py`, a `trylast` makereport wrapper that flips
        `test_no_test_reads_a_clock` to passed.
      - Add a unit test that reads `time.time()`.
      - Result: the run exits 0 with `lost 0`. `judge_files()` gives the
        same hash with and without the two files.
    - Failure 2 (EXECUTED): `PYTHONPATH=<outside dir>
      PYTEST_ADDOPTS="-p quiet"` with no repository change → exit 0,
      `lost 0`, and nothing announced.
    - Fix:
      - Record `config.inipath` and fail the run unless it is
        `pyproject.toml`. That covers every config name, present and
        future.
      - Record `PYTEST_ADDOPTS` and the plugins pytest loaded that are
        not pytest's own or `harness.plugin`
        (`config.pluginmanager.list_name_plugin()`).
      - Announce them on the `JUDGE INPUTS OVERRIDDEN` line, and refuse
        `--accept` while any is present.
      - Correct Decision 14's "every file that can … steer pytest" and
        the residual text in this disposition.
    - Any code that runs inside the judge's process can patch the
      harness: an outside plugin, or the product's own
      `wasi_python/__init__.py`, which `needs` imports. So "announce,
      and refuse to accept" is the reachable bar. It is not reached yet.

N2. **A gap's digest includes line numbers, so a harmless edit breaks
    it** (`tests/harness/scan.py:289-297`).
    - Failure (EXECUTED): add one comment line near the top of
      `scripts/04_link_python_numpy.sh`. The embedder check still has
      `55 finding(s)`, but its digest changes, so it "fails
      differently" and the run is red.
    - Every routine edit to `recipes/` or `scripts/` above a gapped hit
      then needs a `known_gaps.toml` edit and an `--accept-judge`.
      Spec 001 will make many such edits. Accepting the judge becomes a
      reflex, which is the habit the ratchet exists to prevent.
    - Fix: hash each finding without its line number (path plus the
      matched text, or path plus a count per path). The set stays
      exact, and the digest survives line moves.

N3. **A pass blocked by `wheel` is not red** (`tests/harness/scoreboard.py`
    `PROTECTED_NEEDS`).
    - The wheel is a product output, like the artifacts, not local
      tooling.
    - Failure: once `test_wheel_carries_the_artifact_set` is accepted,
      a wheel build that stops producing a wheel leaves `dist/` empty.
      The check is then "unrun locally", and the run stays green.
    - Fix: add `wheel` to `PROTECTED_NEEDS`.
    - The same reasoning makes `source tree <name>` blocking silent in
      the release workflow. When 001 or the release spec writes that
      workflow, it should fail if the zero-patch check is blocked.

N4. **The accepted baseline predates the fixes.**
    - `accepted.json` still holds the old judge. Today's runs report
      `judge changed` for 23 files, among them `.gitattributes`, every
      harness module and `known_gaps.toml`.
    - Criterion 9 needs the baseline re-accepted on the final tree
      before landing: `--accept "…" --accept-judge "review fixes"`,
      which writes history line 2. Otherwise the first post-landing run
      opens with a judge change nobody accepted.

## Verdict

**Lands** (final, 2026-10-16, after the confirmation of the N1 and N2
fixes below).
- Findings 1–10 and N1–N4 are confirmed fixed or answered in writing.
- The baseline is re-accepted on the final tree (history line 2), and
  both tiers are green here and in a fresh clone.
- The one residual, a plugin written to patch the harness in-process,
  is stated in Decision 14 as review's to catch.

The earlier verdict, kept for the record:

Does not land yet.
- Findings 1 and 3–10 are confirmed fixed or acceptably answered.
- Finding 2 is not fixed (N1): a `.pytest.toml`, or a plugin loaded
  through `PYTEST_ADDOPTS`, still turns a lost pass green, with no
  judge change and no announcement.
- N2 makes the gaps red on harmless line moves. Fix it before 001
  starts editing scripts.
- N3 is a one-line fix. N4 is a landing step.
- With N1 and N2 fixed and N3 and N4 done, this lands without another
  full review: a re-run of the N1 and N2 experiments is enough.

## Disposition of the confirmation's findings (by the author, 2026-10-16)

- Finding 2 (not fixed at confirmation) and N1 — **fixed** together. In
  a run of this repository, pytest configured from any file other than
  `pyproject.toml`, or any registered plugin that is neither pytest's
  own (`_pytest`) nor a judged file, makes the run red ("steered from
  outside the judge"). `PYTEST_ADDOPTS` is announced and blocks
  `--accept`. Self-tests reproduce the attacks in a subprocess at the
  repository root: `test_a_plugin_from_outside_the_judge_turns_the_run_red`
  (`-p quiet` from a directory on `PYTHONPATH`),
  `test_a_config_file_other_than_pyproject_turns_the_run_red` (`-c`),
  `test_pytest_addopts_is_announced_and_blocks_acceptance`. Decision 14
  no longer claims to hash "every file that can steer pytest"; it says
  what is hashed, what is refused, and that review is the backstop
  against an agent that rewrites the interpreter.
- N2 — **fixed**: digests drop line numbers (`scan.digest`); the gaps
  were rewritten with the new digests;
  `test_a_digest_ignores_line_numbers_but_not_findings`.
- N3 — **fixed**: `wheel` is a protected need. The release workflow
  failing when the zero-patch check is blocked is the release
  specification's to decide; it is recorded there as a requirement by
  this line, and `test_release_workflow_runs_the_zero_patch_check`'s gap
  points at `README.md` (Next, item 4).
- N4 — **done** after the fixes: the baseline was re-accepted with
  `--accept-judge "review fixes"` (history line 2).
- Finding 7's residual — **fixed**: a pinned download that does not
  match its pin is a licence error, not a fallback to presence only.
- Finding 10's leftover `build/harness/tmp*` — **deleted**.

Re-ran: `uv run pytest -q -p no:cacheprovider` → `147 passed, 45
skipped, 8 xfailed`, exit 0.

### Confirmation of the N1 and N2 fixes by the reviewer, 2026-10-16

I checked the code (`plugin.py` `foreign_steering`, `scan.digest`,
`scoreboard.PROTECTED_NEEDS`, `paths.licence_source`) and re-ran the
experiments. I did not rely on the disposition text.

**The real repository, read-only (EXECUTED).**
- `uv run pytest -q -p no:cacheprovider` → `14/67 pass · 8 gap · 45
  blocked · 0 fail (unit suite 133/133)`; `147 passed, 45 skipped, 8
  xfailed`; ratchet `lost 0 · absent 0 · unrun 0 · gained 0 · grew 0`,
  with no judge change; exit 0.
- `-m "not slow"` → `146 passed, 42 skipped, 4 deselected, 8 xfailed`;
  `… not selected 1`; exit 0.
- `test_progress_history_is_intact` is `pass`.
  `scoreboard.history_errors` on the two-line history → `[]`. Line 2
  has `reason: "review fixes"`, a `judge_reason`, 23 `judge_changed`
  files, and a `prev` that hashes line 1. The judge hash of the tree
  equals the accepted one.
- `wheel` is in `PROTECTED_NEEDS`.
- `licence_source` raises "does not match its pin", and
  `licence_errors` reports it as an error.
- `build/harness/` holds only `oracle-check`.

**The attacks, in a fresh `git clone` with `git ls-files -co
--exclude-standard` overlaid, in the session scratch directory
(EXECUTED).**
- **N1, config file.** I added a `.pytest.toml` with `pythonpath =
  ["tests", "tools"]` and `addopts = ["-p", "quiet"]`, a
  `tools/quiet.py` that flips `test_no_test_reads_a_clock` to passed,
  and a unit test that reads `time.time()`.
  - Result: `RED: steered from outside the judge: pytest is configured
    from …/.pytest.toml, not pyproject.toml; plugin quiet from …`, exit
    1. **Fixed.**
- **N1, environment.** `PYTHONPATH=<outside dir> PYTEST_ADDOPTS="-p
  quiet"` produced:
  - `JUDGE INPUTS OVERRIDDEN: PYTEST_ADDOPTS` and `RED: steered from
    outside the judge: plugin quiet from …/outside/quiet.py`, exit 1;
  - and `--accept` (against a scratch `--progress-dir`) was refused.
  - **Fixed.**
- **N2.** I added one comment line near the top of
  `scripts/04_link_python_numpy.sh`. The run exits 0 and the gap holds.
  **Fixed.** Exactness still holds:
  - a duplicated `vfs` line in the same script gives `56 finding(s)`,
    "fails differently", exit 1;
  - a second bare `python3` in `scripts/00_download.sh`, the file that
    already holds the known one, gives `2 finding(s)`, exit 1.
- **Residual, accepted as stated.** I wrote a plugin that, on import,
  replaces `harness.plugin.foreign_steering` and removes
  `PYTEST_ADDOPTS` from `os.environ`, then loaded it through
  `PYTEST_ADDOPTS` with an outside `PYTHONPATH`.
  - Result: the run exits 0, and `--accept` to a scratch progress
    directory succeeds.
  - This is code written to rewrite the judge in its own process.
    Decision 14 now says plainly that the harness does not guard
    against that and that review is the backstop.
  - Any in-process check could be patched the same way, so I accept
    the line as drawn.
  - One smaller tolerance: findings are compared without line numbers.
    So a hit removed from one line of a file and added on another line
    of the same file leaves the digest unchanged. That is the intended
    trade (N2), and the count still catches any net addition.

**Findings N1 to N4: confirmed fixed or done.** No new finding.
