# Build review of spec 087: the 0.1.0a7 review's guest follow-ups

- **Date:** 2026-10-19
- **Reviewer:** a fresh agent (Claude Opus 5.5). It wrote none of the specification, the code,
  the checks or the landing notes, and did not do the pre-build review.
- **Reviewed:** `spec/087-the-a7-reviews-guest-follow-ups` in `wasi_python-087`, on main
  `91eb2c7`: `2abcba0` (the build, pushed for its dry run) and `9a02d68` (the landing notes). I
  read the whole diff `91eb2c7..9a02d68` outside `context/research/`: the patch and its sheet,
  `scripts/assemble_artifacts.py`, `src/wasi_python/__init__.py`, `src/wasi_python/runner.py`,
  the driver and WAT changes, every new check, the README and CHANGELOG hunks, and the landing
  notes. In `runner.py` I also read the code S3's check leans on: `_digest`, `_module`,
  `_module_miss`, `_zip_folder`, `_copy_zip` and `_runtime_folders`.
- **S3 is reviewed here for the first time.** It joined the scope during the build (Departure 1),
  so this is its only review before landing.
- **Set judged:** the builder's `build/artifacts` in the worktree. `shasum -a 256 -c SHA256SUMS`
  passed on every file; `SHA256SUMS` is `89b14f67…`, the landing notes' and `build/087/`'s. Every
  file has one link (nlink 1).
- **Scoreboard (EXECUTED):**
  - Full judge, `uv run pytest -n 3`, on the committed tree `9a02d68`, with no lane lock held:
    **549/630 pass · 77 gap · 4 blocked · 0 fail** (unit suite 1593/1600, 7 skipped); 2,142
    passed, 11 skipped, 77 xfailed in 962 s. These are the builder's counts.
  - Ratchet against `b91e0eaa4e`: lost 0 · absent 0 · unrun locally 2 · gained 7 · **grew 3**.
    The builder had grew 2. Two of the three are the binaries' +202 bytes. The third is
    `test_upstream_suite[cpython-c]`: fuel 372,458,058,296 → 372,501,650,245 (+1.18e-4, just past
    the 1e-4 tolerance). See F5.
  - `tests/harness/sameness.py build/087/latest-full.json reviewer-latest.json`: one row differs,
    `cpython-c` (builder 372,457,643,534, mine 372,501,650,245). Every other row and every
    verdict are the same.
  - My record is `build/progress/latest.json` in the worktree, copied beside this file as
    `reviewer-latest.json`.
  - `ruff check` and `ruff format --check` on `src` and `tests` are clean. `git status` in the
    worktree is clean.
- **Probes** (EXECUTED, in `probes/` beside this file; each `.py` has its `.txt`; each runs
  against the worktree read-only, on a small WAT set or package copies in the scratch folder):
  - `toctou.py`: does the found-set check bind the bytes the runner then uses?
  - `layout.py`: which set a copy of the package picks in eight layouts.
  - `grant.py`: whether a guest can write the `pyproject.toml` that makes a vendored copy a
    "checkout".

Labels: **EXECUTED** (I ran it), **READ** (code or document), **INFERRED** (reasoned, not run).

## Short version

The build matches its specification.

- **The patch is right and recorded.** 0002 widens regex's ticks to `long long` in every place
  that carries them, and guards the double-to-integer conversion. It is under
  `recipes/patches/`, hashed in `MANIFEST`, named in the CHANGELOG and in `LICENSES/regex.txt`,
  and byte for byte the drafted upstream `fix.patch`.
- **The checks are honest.** No existing expectation moved; the judge's only removed lines are
  the driver's two clock lines, now parameterised. The mutants show each new check failing where
  it should.
- **S3's location rule holds.** I found no practical way for an installed copy to reach a
  neighbouring set:
  - a `--target` install, a vendored `src/` copy and symlinks either way all take the package's
    own set;
  - a malformed `pyproject.toml` fails closed;
  - a guest cannot write the `pyproject.toml` that would make a vendored copy look like a
    checkout, because the grant judge refuses any writable grant above wasi_python's own code.

One weakness: the check of a found set does not bind the bytes the runner then uses. A file
swapped after the check is compiled or copied, and a swap inside `_module` leaves a `.cwasm`
under the good digest. A later process, with the set restored and passing the check, then
loads the planted code (F1, EXECUTED). The only actor who can win that race can also rewrite
`SHA256SUMS`, and the specification says the check does not stop such a writer. So F1 is Low,
but its fix is small. The README does not carry the specification's own limit on the check (F2).

Two findings to fix before landing:
- F2: one README clause.
- F3: one token at the rebase, which a build-class landing needs anyway.

F1 and F4 are Low. F5 to F8 are notes.

## S3, judged

### The location rule (Decision 10)

`_checkout_artifact_dir()` takes `<repo>/build/artifacts/` only when the resolved package is
`<repo>/src/wasi_python/` and `<repo>/pyproject.toml`'s `[project] name` is exactly
`wasi-python`. Any error reading the file means "not a checkout" (READ).

`layout.py` (EXECUTED). Each case plants a consistent set, with a `MANIFEST`, at
`<proj>/build/artifacts`:

| layout | picks |
|---|---|
| `src/wasi_python` a symlink to a real copy in `deps/`, pyproject names wasi-python | own |
| `deps/wasi_python` a symlink to a real copy in `src/`, pyproject names someproj | own |
| `src/` layout, pyproject names `wasi_python` (underscore) | own (fails closed) |
| `src/` layout, pyproject not TOML | own |
| `src/` layout, `project = "wasi-python"` (a string) | own |
| `src/` layout, `pyproject.toml` a folder | own |
| zipimport from `proj/deps.zip` | no set: `ArtifactsMissing` (as before 087) |
| zipimport from a zip file literally named `src`, beside a pyproject naming wasi-python | **planted** |

The last row is self-inflicted: the embedder must name the zip `src` and put a pyproject that
names wasi-python beside it. No guest can arrange that (see below). It is a note, not a finding
(F6).

- **The three tested layouts** of check 7 (`--target` install, `--target` install in a project
  named wasi-python, vendored under `src/` in another project) pick the package's own set. The
  first one fails on main (`seen-failing.txt`, READ).
- **An editable install, or a symlink from `site-packages` into a checkout,** resolves to the
  checkout and uses its `build/artifacts/`. That is intended: it is how the judge, the build and
  the release workflow import the package (INFERRED from `.resolve()`, consistent with the
  symlink rows above).
- **Can a guest spoof the layout?** It would have to write `<repo>/pyproject.toml`, which needs a
  writable grant at or above `<repo>`, so above `<repo>/src/wasi_python`. `grant.py` (EXECUTED):
  a vendored copy at `proj/src/wasi_python`, run with `Grant(proj, "/w", writable=True)`, is
  refused: *"grants[0] at /w is writable and holds wasi_python's own code"*. A grant at
  `proj/build` runs, and the copy still ignores `proj/build/artifacts`, since the pyproject names
  someproj.
- **In a real checkout,** a writable grant at `build/` is refused while `build/artifacts` is the
  set in use (`_runtime_folders` lists "the artifact set", READ). When the set comes from
  `$WASI_PYTHON_ARTIFACTS` instead, `build/` is not protected. A guest could then plant a
  consistent set there, and a later run without the variable would load it (INFERRED). That is
  a developer's checkout, not an installed wheel. F2 asks the README to say so.

### The check of a found set

`_found_and_checked(snapshot)` reads the set's `SHA256SUMS`. It checks `MANIFEST`, the binary
this call runs and the stdlib zip, refusing a file that is unlisted or differs (READ). It runs
for `run`, `run_async` (through `_run_checked`) and `Session` (`_open_session`), and nothing else
calls `find_artifacts()` (READ, grep).

- **Complete for what is loaded.** The other binary is never loaded by that call. `LICENSES/`
  is never loaded. The `.cwasm` is keyed by the binary's digest, under N3's private-folder rule.
  So the three files checked are the three a call reads.
- **The cost is unchanged.** `_module` and `_zip_folder` already hashed the binary and the zip
  per file stamp. The check adds two small reads a call.
- **The wheel's own set still works.** The release copies the whole `build/artifacts/`,
  `SHA256SUMS` included, into `src/wasi_python/artifacts/` (`release.yml:75,186,249`, READ). The
  dry run's three `verify` jobs, which install the wheel, passed (EXECUTED: `gh run view
  39346784823`).
- **Not time-of-check to time-of-use safe** (F1).
- **Integrity, not authenticity.** `SHA256SUMS` sits in the folder it vouches for. The
  specification says so plainly (Decision 10, "What the check does and does not do"). The README
  does not (F2).

### The narrowing on `run(artifacts=…)`

This is acceptable, and the specification states it honestly. `Artifacts` is public API for four
paths of the caller's choosing. Three existing checks pass WAT stand-ins that way. The
docstrings of `run`, `run_async` and `Session`, the README reference and the README prose all say
a passed set is used as given, and the prose calls it trusted input.

One consequence is worth knowing: the narrowing is by argument, not by where the set came from.
`run(artifacts=wasi_python.artifacts())` skips the check that `run()` alone would make (READ;
`test_a_set_the_caller_passes_is_its_own` relies on this). That is consistent with the docstring;
see F2 for one clause.

## The rest, judged

- **The patch (criterion 4).** It is minimal and correct (READ):
  - `typedef long long RE_Ticks`, used for `RE_State.timeout`, `decode_timeout`'s return, the
    three `timeout` parameters and the nine `tim` locals;
  - `check_timed_out` casts the elapsed ticks to `RE_Ticks`;
  - `decode_timeout` maps negatives, NaN and anything at or above `(double)LLONG_MAX` ticks
    (2**63, exact) to `RE_NO_TIMEOUT`, so the conversion is never out of range.

  A grep of the patched `build/regex-2026.9.29/src/_regex.c` finds no other `Py_ssize_t` holding
  ticks. `clock_t` is `long long` on wasi-libc, so `clock() - start_time` does not wrap (the
  check's 3.0 to 3.1 s confirms it). The file is recorded in every place the rules ask:
  - under `recipes/patches/regex-2026.9.29/`;
  - in `MANIFEST` as `recipe 9da893d0…`, equal to `shasum` of the file;
  - in `MODIFIED` and `LICENSES/regex.txt`;
  - in the CHANGELOG;
  - in `context/upstream/README.md` row 24;
  - with its sheet at `context/upstream/patches/regex-2026.9.29/0002-timeout-ticks.md`.

  `fix.patch` equals the recipe byte for byte (`cmp`, EXECUTED). The README's count is 8.
- **Decision 6's restated depths.** Each new "completes at" is ¾ of the lowest edge of both
  hosts, rounded down. For example, XPath parentheses has a lowest edge of 324, ¾ is
  243, and the check uses 240. They stay meaningful checks:
  - each sits at 72.8% to 74.9% of the lowest measured edge;
  - a change that took away more than about a quarter of the frame budget fails the row;
  - the trap depths are unchanged, so each row still pins both sides of its edge.

  The edges fell on amd64 (larger x86-64 frames), which the specification foresaw. Windows
  x86-64 passed check 4 in the dry run's `judge (windows-2025, own-guest)` (EXECUTED: job list).
- **AGENTS rule 4.** No expectation was weakened. `git diff 91eb2c7..9a02d68 -- tests/` removes
  only the driver's docstring end and its two clock lines, which become `clock_step_ns` and its
  stated resolution. `known_gaps.toml`, `tests/upstream/` and `context/progress/` are untouched
  (EXECUTED).
- **The accepting texts.** They are exact:
  - `--accept-growth`'s four byte counts equal main's sizes and this set's (`ls -l`, EXECUTED);
  - `--accept-judge` names every judge file the diff touches, including the shard file;
  - `--accept` describes the change.
- **The checks.** Check 1 times nothing: with the driver's clock at 2 ms a read, a guest second
  is 500 reads. The mutants (`build/087/mutants.log`, READ) each fail the check they aim at.
  Check 8's refusals fail on main (`seen-failing.txt`).
- **The dry run.** Its one red job, `judge (macos-15, own-guest)`, shows `lost 0`, `0 fail` and
  `RED: 2 metric(s) grew` (`build/087/dryrun-macos-own-guest.log`, READ). Criterion 9 asks for
  every job green. That is met in substance: the growth is the lane's to accept, and rule 6b's
  dry run on main follows the acceptance (F7).
- **Ruff.** `ruff check` and `ruff format --check` on `src` and `tests` are clean (EXECUTED).

## Findings, most severe first

### F1 (Low): the check of a found set does not bind the bytes the runner then uses; a swap leaves a `.cwasm` under the good digest

- **What happens (EXECUTED, `probes/toctou.py`, `toctou.txt`).** The probe builds a small WAT set
  with a correct `SHA256SUMS` at `$WASI_PYTHON_ARTIFACTS`. It then simulates a writer of that
  folder at three moments:
  - **a.** The snapshot is replaced after `_found_and_checked` returns. `run` returns 42, the
    planted module's answer, not 101, the checked one's. `_module` hashes the file again and
    compiles what it finds now.
  - **b.** The snapshot is replaced between `_module`'s `_digest` and `wt.Module.from_file`. The
    run returns 42. The cache now holds
    `20fe24c7337738c2…-wasmtime49.0.0-plain.cwasm`, named by the *checked* digest and holding the
    planted code.
  - **c.** A fresh process, with the original snapshot restored, so the set matches its
    `SHA256SUMS` again: the check passes, `_module` loads that `.cwasm` (`loaded: 1, compiled:
    0`), and the run returns 42.
  - **z.** The stdlib zip is replaced after the check. `_zip_folder` hashes the zip again, takes
    that as `want`, and `_copy_zip` checks the copy against it. The guest's private copy then
    holds the planted `sitecustomize.py`, with no error.
- **Why Low.** The race needs a writer of the set's folder during a call. The grant judge keeps a
  guest of the call from being that writer, since a writable grant at or above the set in use is
  refused. Any other writer can also rewrite `SHA256SUMS`, and Decision 10 says the check does not
  stop such a writer. The `_module` race existed before 087.
- **Why it is still worth fixing now.**
  - `_found_and_checked`'s docstring promises "a changed or half-written file is refused, not
    compiled". A file that changes during the call is compiled.
  - Case c shows that one transient change becomes permanent. It survives in the user's module
    cache after the set is put right, where neither the check nor N3's private-folder rule can
    see it.
- **Fix.** Have `_found_and_checked` return the digests it checked, and use them:
  - `_zip_folder` takes the checked zip digest as `want`. `_copy_zip` already checks the private
    copy against `want`, and the guest reads only that copy, so this closes the window for the
    zip entirely. It is one argument.
  - `_module` reads the binary once, hashes those bytes, refuses on a difference from the checked
    digest, and compiles the same bytes with `wt.Module(engine, data)`. It writes the `.cwasm`
    only from them. The 45 MB in memory is transient.
  - For a set the caller passes, `_module` keeps today's path.
  - Add `toctou.py` cases a, b and z as unit rows in `tests/unit/test_runner_sets.py`, swapping
    through a monkeypatched `_found_and_checked` or `_digest`, as the probe does.

  If the lane prefers, this can be a follow-up specification. It does not change F2's README
  sentence.

### F2 (fix before landing): the README does not carry the specification's own limit on the check

- **Where.** README, the runner section: "`run` and `Session` check the set they find against its
  `SHA256SUMS` before using it. A folder named by `$WASI_PYTHON_ARTIFACTS`, and a set passed as
  `artifacts=`, are trusted input: keep them where only you can write."
- **What is missing.** Decision 10 says it plainly: the check "refuses a changed or half-written
  file. It does not stop a guest that writes a whole consistent set, `SHA256SUMS` included: the
  location rule does that." The README states the check without that limit, so a reader can take
  it for a defence against tampering. It also leaves out two places a set comes from:
  - a source checkout's `build/artifacts/`, where a guest can plant a consistent set whenever the
    set in use comes from `$WASI_PYTHON_ARTIFACTS` instead (INFERRED, section "The location rule");
  - `run(artifacts=wasi_python.artifacts())`, which is a passed set and so skips the check.
- **Fix.** One clause after the check sentence, for example: "The check catches a file changed or
  half-written since the build, not a set rewritten whole with its `SHA256SUMS`: where the set
  lives is what keeps it safe. So a folder named by `$WASI_PYTHON_ARTIFACTS`, a checkout's
  `build/`, and a set passed as `artifacts=` (even one from `artifacts()`) are trusted input:
  keep them where only you can write, and out of any writable grant." This is README only: no
  rebuild, and no check reads that paragraph (READ: the reference section is the generated part,
  and this is prose).

### F3 (fix before landing, at the rebase): after 083, the driver's file times keep the default step while its clocks take `clock_step_ns`

- **What (EXECUTED: `git merge-tree --write-tree main HEAD`).** The rebase onto main `45b917c` has
  one textual conflict, `CHANGELOG.md`. `tests/harness/guest.py` merges cleanly, but the result
  is wrong in one place:

  ```
  606:    files = _FileCalls(counted, FileFacts(lambda: REALTIME_START_NS + next(ticks) * CLOCK_STEP_NS))
  614:        value = start + next(ticks) * clock_step_ns
  ```

  083 makes a file's times follow the driver's stepped realtime clock, and draws them from the
  same `ticks`. With a step other than the default, file times would advance 1 µs per tick while
  the clocks advance `clock_step_ns`. A file written later would then carry a time far behind the
  clock. No check today reads file times with a changed step (check 1 does not), so nothing turns
  red. That is exactly why the merge would go unseen.
- **Fix.** At the rebase, line 606 uses `clock_step_ns`. Decision 9, which names 083's textual
  merge in `guest.py`, gains one sentence saying so. Add a unit row: under
  `clock_step_ns=2_000_000`, a file written after two clock reads has an `mtime` within one step
  of the second read. 083's `FILE_FACTS` WAT probe can carry it. The delta review then sees the
  merged driver.

### F4 (Low): `LICENSES/regex.txt` says "the module is otherwise compiled as released" after each of its two patch lines

- **What (EXECUTED, `tail -4 build/artifacts/LICENSES/regex.txt`).** regex is the first tree
  with two carried patches in a modification notice. `modified_notice` appends "the module is
  otherwise compiled as released" to every patch line. Each line therefore ignores the other
  patch. The function's own docstring says "one line per carried patch …; then that the rest is
  compiled as released", which is once.
- **Fix.** Write the closing clause once, after the last line. This changes
  `LICENSES/regex.txt`, and with it `SHA256SUMS` and the set's name. So it suits a follow-up, or
  the next build-class specification that reassembles the set, rather than a rebuild now. The
  notice is present and names each patch and file, which is what the licence asks.

### F5 (note): my record grew `cpython-c` by 1.18e-4; this is the base's known noise, which 083 removes

- **What (EXECUTED).** `cpython-c`'s fuel was 372,501,650,245 against the accepted
  372,458,058,296 and the builder's 372,457,643,534. `passes` is the same (7,867). Every other
  CPython group stayed inside 1e-4 (`cpython-a` +7.3e-5 against the builder).
- **Why it is not 087's.** 087's base `91eb2c7` predates 083. 089's build review measured this
  same row on the same kind of base: main gave up to +9.3e-5 in alternating runs, and 089 itself
  gave +1.21e-4 (`context/reviews/089-…-build-2026-10-19.md`, section 5). 083, now on main,
  removes the noise from the CPython groups. The machine was heavily loaded during my run (load
  average about 140, with two other judges running).
- **For the lane.** The branch must rebase onto `45b917c` anyway, which brings 083 (F3). The lane's
  serial record and the sameness comparison should be taken on the rebased commit, against a
  reviewer record taken there too, not against this one or the builder's. A post-rebase delta
  review is due in any case, since 083 moves fuel numbers.

### F6 (note): a zip literally named `src` beside a `pyproject.toml` naming wasi-python passes the rule

`layout.py`'s last row (EXECUTED). Only an embedder can make that layout. No guest can, because
the grant judge refuses writable grants above wasi_python's own code. No fix is needed. I record
it so that nobody reads the rule as path-proof.

### F7 (note): criterion 9 is met in substance, not in letter

The dry run's one red job, `judge (macos-15, own-guest)`, is red only for the two growth lines
(READ: `build/087/dryrun-macos-own-guest.log`). The lane accepts those lines. Rule 6b's dry run
on main after acceptance is the real gate. The landing notes say this plainly.

### F8 (note): `Session`'s `artifacts` docstring continues at the argument's indent

In `runner.py`'s `Session.__init__`, the second line of the `artifacts` entry ("against its
SHA256SUMS first. …") sits at 12 spaces, the level of the argument names, not 16. The README
generator joins it correctly, so the reference reads right (READ). Indent it with the other
continuations when the file is next touched.

## Verdict

**Lands once F2 and F3.**
- F2 is one README clause.
- F3 is one token in the rebased driver, with its unit row, seen by the post-rebase delta review
  the landing needs anyway (F5).
- F1 is Low but cheap, and closes the zip's window completely. I recommend taking it in the same
  change. If it is not taken, it becomes a follow-up specification, and the docstring's "refused,
  not compiled" should then say "at the time of the check".
- F4 waits for the next reassembly of the set.

S3's location rule, the carried patch and its records, the restated depths, and the judge's
integrity (no expectation weakened, accepting texts exact) all hold as built.

One line: the patch and the checks are right, and S3's location rule holds against every layout
I tried. The SHA256SUMS check does not bind the bytes it checked (F1, Low), the README must state
its limit (F2), and the rebase must give 083's file times the new clock step (F3).
