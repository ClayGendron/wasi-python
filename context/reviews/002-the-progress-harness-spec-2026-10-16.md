# Review of 002 — The progress harness

- **Date:** 2026-10-16
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author; given the
  specification, the constitution, spec 001, the three research memos
  and the tree, not the author's summary.
- **Reviewed:** the specification as drafted
  (`context/specifications/002-the-progress-harness.md`, untracked,
  259 lines, at HEAD `1ec6199`).
- **Re-ran:**
  - `uv run pytest -q` → `2 passed`, exit 0.
  - `uv run ruff check` → `All checks passed!`.
  - `uv run ruff format --check` → **exit 1**: `1 file would be
    reformatted` → `context/research/2026-10-16-fuel-as-the-operation-count.md:31:1`
    (ruff formats Python code blocks inside Markdown).
  - `grep -a -o "3\.14\.7" build/brett-3.14.7/python.wasm | wc -l` → `2`
    (one match followed by NUL, one by `-`).
  - `tar tzf downloads/zlib-1.3.1.tar.gz` → the tarball holds
    `zlib-1.3.1/Makefile` and `zlib-1.3.1/zconf.h`.
    `tar xzOf … zlib-1.3.1/configure` → line 568 `cp -p ${SRCDIR}zconf.h.in zconf.h`,
    lines 578–594 rewrite `zconf.h` with `sed`, lines 870–901 write `Makefile`.
  - `du -sh context/prior_art` → `496M`; `find … -name '*.c' -o '*.h' -o
    '*.py' -o '*.sh' -o '*.rs' -o '*.cpp' -o '*.pyx' | wc -l` → `13320`.
  - READ: `recipes/vfs_main.c` (`PyConfig_InitIsolatedConfig`, no hash
    seed set; `vfs_run` skips `-I`); `context/prior_art/wasmtime/crates/wizer/src/rewrite.rs:127-138`
    (Wizer drops the `wizer.initialize` and `_initialize` exports from
    the snapshot); `scripts/00_download.sh`; `scripts/09_build_zlib.sh`;
    `downloads/SHA256SUMS` (nine lines, no python-dateutil, tzdata or
    six); `pyproject.toml`; `uv.lock`; no `.gitattributes` in the repo.

## Acceptance criteria against evidence

For a specification review: is each criterion checkable, and is it
sufficient for the design it guards?

1. *`uv run pytest` exits 0 with no artifacts, ≤ 25 lines, writes
   `latest.json`* — checkable. Not sufficient: with no artifacts nearly
   every goal check is `blocked`, so exit 0 says little (finding 1). The
   25-line cap disagrees with Decision 12's "about twenty", and one
   `FAIL` line per failure is unbounded.
2. *≥ 4 checks per v1 area, ≥ 10 in `rules`, none `fail`* — checkable.
   Not sufficient: it counts checks rather than naming them. A build
   that omits "imports come only from `wasi_snapshot_preview1` and
   `host`" (the wall itself) still meets it (finding 17).
3. *Every blocked check names a vocabulary need; every gap names an
   existing closer* — checkable. Not sufficient: nothing checks that a
   need is actually unmet when a check claims it (finding 13).
4. *Each detector in `scan.py`, `wasm.py`, `pins.py`, `scoreboard.py` is
   tested both ways* — checkable. Leaves out `paths.py` (the `MANIFEST`
   reader, which Decision 11 fixes) and the `guest.py` door binding.
5. *pytester self-test: unnamed skip, passing gap, lost pass, fuel
   ±1%, `--accept` refuses a loss* — checkable. Covers five of the
   ratchet's behaviours. Not covered: `unrun`/absent, `gained`, `bytes`
   growth, judge-changed, the wasmtime-version gate, `--accept-growth`,
   `--retire`, "a check that did not run keeps its accepted entry", and
   append-only history (finding 17).
6. *Driver self-tests against Brett's 3.14.7 build* — checkable here
   (`build/brett-3.14.7/` is present). Not sufficient: Brett's build is
   a command module with no `host` import and no `host_alloc`, so the
   reactor path, the snapshot path and the door binding are never run
   before landing (finding 6).
7. *`accepted.json` with "initial baseline" and one history line* —
   checkable. Sufficient for what it says.
8. *`ruff check` and `ruff format --check` clean* — checkable, and
   **fails on the current tree** before any 002 code exists (finding 11).

## Findings, most severe first

1. **A missing or broken artifact set reads as green** (`002:35-39`,
   `002:52-54`, `002:106-108`) — artifact discovery falls back silently,
   `blocked` is not red, and an accepted pass that becomes `blocked` is
   only "reported".
   Failure: an agent's build step dies before writing `MANIFEST`
   (or deletes `src/wasi_python/artifacts/` while rebuilding). The
   wheel fallback finds no `MANIFEST`, the "artifact set" need is unmet,
   and every v1.1–v1.4 check turns `blocked`. All their accepted passes
   become `unrun`, which is red only under `--strict`. `uv run pytest`
   exits 0 and the scoreboard looks like a source checkout. The same
   question has no answer when `$WASI_PYTHON_ARTIFACTS` is set but the
   directory is incomplete: if the need means "all files present", the
   check "the set is complete" can never fail; if it means "the variable
   is set", the spec does not say so. Fix: when
   `$WASI_PYTHON_ARTIFACTS` is set, the need is met and every missing
   file is a `fail`; and make `unrun` red whenever the need that blocks
   it was met on the accepted run's machine class (or simply: an accepted
   artifact pass that turns `blocked` is red unless `--no-artifacts` is
   passed explicitly, which the scoreboard prints).

2. **Deleting, renaming or deselecting a passing check is not red**
   (`002:53-54`) — "absent" is lumped with `blocked` as `unrun`.
   Failure: a guest check that passed and now fails is renamed
   (`test_pandas_job` → `test_pandas_job_v2`) or deleted, or
   `pyproject.toml` gains `addopts = "--deselect …"`. The old node id is
   absent → `unrun` → reported, not red. The run is green. ts-rust,
   which the spec cites for this rule (memo lesson 3), treats lost,
   absent and unrun alike as a STOP. Fix: pytest tells the plugin which
   items were deselected (`pytest_deselected`) and which were collected.
   Deselected (`-m "not slow"`, `-k`) → `unrun`, reported. Accepted but
   neither collected nor deselected → **absent, red**, until `--retire`
   records it.

3. **The ratchet state is not tamper-evident, and two inputs that
   decide it are outside the judge** (`002:46-50`, `002:129-131`) —
   `context/progress/` is not hashed or cross-checked, and
   `pyproject.toml` and `uv.lock` are not judging files.
   Failure (a): an agent removes one entry from `accepted.json` by hand.
   The lost pass is no longer protected; nothing notices.
   Failure (b): a `uv.lock` bump from wasmtime 49.0.0 to 49.0.1 makes
   every fuel comparison "different wasmtime version", so no fuel
   growth is ever red, and the judge hash does not move. Failure (c):
   `pyproject.toml` `addopts` deselects checks (finding 2) without a
   judge change. Fix: each `history.jsonl` line carries the hash of the
   `accepted.json` it produced (and of the previous line); a `rules`
   check replays the history, compares with `accepted.json`, and checks
   that `history.jsonl` extends `git show HEAD:context/progress/history.jsonl`.
   Add `pyproject.toml` (`[tool.pytest.*]`) and `uv.lock` to the judging
   files. A wasmtime version change is red until accepted with a reason,
   which re-baselines fuel explicitly.

4. **A changed judge, a new gap or a retirement is accepted by any
   `--accept`** (`002:59-60`, `002:62-68`) — "judge changed" is never red
   and `--accept` does not refuse it, so a weakened check becomes the
   baseline in one step.
   Failure: an agent loosens `test_v1_3_data_stack.py` to compare only
   the versions line, sees "judge changed", runs `--accept "fix job"`.
   The new judge hash is accepted; the next run reports nothing; the
   landing review sees a clean ratchet report. ts-rust (memo lesson 6)
   requires "an explicit, reviewed entry". Fix: `--accept` refuses a run
   whose judge hash differs unless `--accept-judge "<reason>"` is given;
   the history line lists the changed judging files; the scoreboard
   prints every judge change, gap addition and retirement since the last
   landed review, so the reviewer cannot miss them.

5. **The fuel ratchet creeps, and its 1% tolerance rests on two runs of
   `pass`** (`002:56-58`, `002:76-80`).
   Failure (a): each acceptance writes the new fuel. Ten acceptances at
   +0.9% each raise the baseline by 9.4% with no reason ever stated.
   Memo lesson 4 says a cap "can only go down". Fix: `--accept` keeps
   `min(accepted, measured)` for every metric; only `--accept-growth`
   raises one.
   Failure (b): `PYTHONHASHSEED=0` is inert on both product binaries.
   The plain reactor uses `PyConfig_InitIsolatedConfig` (READ,
   `recipes/vfs_main.c`), so it ignores the variable (fuel memo,
   finding 6; confirmed by the recipe: no `use_hash_seed`); the
   snapshot's secret is baked at Wizer time. The only seeded binary the
   spec tests is Brett's command module (criterion 6). The plain
   reactor's spread was measured on two unseeded `-c pass` runs (0.32%);
   a pandas job hashes far more strings, and its spread is unmeasured,
   so 1% is an INFERRED number used as a red line. Fix, chosen here
   because it removes the variance instead of tolerating it: the driver
   enables `Linker.allow_shadowing` and binds
   `wasi_snapshot_preview1::random_get` to a fixed-seed generator and
   `clock_time_get` to a fixed value. The guest's imports are unchanged
   (still WASI only); the hash secret and the clock then come from the
   judge, fuel becomes exact on every binary, and the tolerance can be
   0 (or the memo's 1e-6 spread). If that is refused, the tolerance must
   come from a measured spread on the heaviest job, which is a
   placeholder memo the spec waits for (§5.2).

6. **The guest-facing checks are never seen to fail, or to run, before
   landing** (`002:248-251`) — in a source checkout every v1.1–v1.4
   check is `blocked`, and the only real guest the criteria run is a
   command module.
   Failure: the export check compares against `"wizer_initialize"`
   instead of `"wizer.initialize"`, or the driver writes the door's
   response length to the wrong pointer. 002 lands green. When 001's
   artifact appears the check fails, and the agent is now "fixing the
   judge" under the pressure of a red run, which is exactly what
   Decision 13 tries to prevent. Fix: add fixtures, built at test time
   with `wasmtime.wat2wasm` (already in the dev dependency), for a
   reactor with `_initialize`/`run`/`host_alloc`/`host::call`, a
   snapshot-shaped module, a module with a third import, and a module
   with a missing export; a synthetic artifact directory (`MANIFEST`,
   `SHA256SUMS`, `LICENSES/`) good and bad. Each v1.1/v1.4 check runs
   against both in `tests/unit/`. Add the same for the golden-job
   comparison (run the job natively, compare with its own `.expected`).

7. **The `MANIFEST` contract lets the artifact checks pass vacuously
   and lacks the lines v1.3 needs** (`002:111-120`, `002:181-184`,
   `002:192-193`).
   Failure (a): v1.3 checks "numpy and pandas import … at the `MANIFEST`
   versions", but Decision 11 defines only `python`, `pin` and `recipe`
   lines. The version must be parsed out of a tarball file name
   (`numpy-2.5.2.tar.gz`), which the spec never fixes.
   Failure (b): a `MANIFEST` with zero `recipe` lines satisfies "recipe
   hashes match the tree". A `MANIFEST` that lists only `recipes/` passes
   while `scripts/wasi-cc` (a compiler wrapper, a recipe by AGENTS.md's
   own definition) changed after the build.
   Failure (c): pins are required only for CPython, numpy, pandas and
   zlib. The wasi-sdk, Wizer, python-dateutil, tzdata and six may be
   missing. The last three are not in `downloads/SHA256SUMS` today at
   all, yet ship in the zip and get licence files, so the §4.2 violation
   is invisible.
   Failure (d): "ignores the rest" means `pins d48…` (typo) is silently
   dropped, and two `python` lines are not an error. Fix: add
   `package <name> <version>` lines for everything in the zip and the
   binary; require exactly one `python` line; require a `recipe` line
   for every tracked file under `recipes/` and every `scripts/` file the
   build ran, and a `pin` line for the toolchain, Wizer and every
   pure-Python package; reject a line whose first word is unknown but
   close to a known one, or reserve a prefix for extensions.

8. **The licence layout is incomplete, accepts empty files, and cannot
   be a GitHub release** (`002:109-111`, `002:184`).
   Failure (a): `python.wasm` statically links wasi-libc (MIT/Apache)
   and, for pandas' C++ modules and pocketfft, wasi-sdk's libc++,
   libc++abi and compiler-rt (Apache-2.0 with LLVM exception). None is
   in the seven-component list, so "one licence file per component"
   passes while §4.6 ("the licence notices of everything inside") and
   §4.12 are unmet. Bundled code inside the named components (pandas'
   own `LICENSES/` directory; numpy's bundled-licence file; CPython's
   libmpdec, expat, HACL*) is not addressed either.
   Failure (b): a zero-byte `LICENSES/numpy.txt` passes a count.
   Failure (c): release assets are flat files (README: "GitHub release
   assets (xz…)"); a `LICENSES/` directory is not one. The release
   specification must then rename or archive it, which Decision 11
   forbids ("may not change these"). Fix: list wasi-libc and the
   wasi-sdk runtime libraries; define the check as "each
   `LICENSES/<component>.txt` contains, byte for byte, the licence file
   from that component's pinned tarball"; say how the directory maps to
   release assets (for example, one `LICENSES.txt` concatenation in the
   release and the directory in the wheel), or leave layout to the
   release spec and fix only the content rule.

9. **002 decides two things that belong to 001, and 001 contradicts
   them** (`002:84-87`, `002:203-204`; `001:15-19`, `001:39-46`,
   `001:68-77`).
   Failure (a): 002 fixes the default door binding at −1 ("no host").
   001 says only "a small negative code on a host fault" and "the
   default binding sets a flag through a second response code". If 001
   is built with −1 for a fault and −2 for "no host", the judge's
   default binding makes every guest call look like a host fault, and
   "the door with no host says so" fails against a correct artifact.
   Failure (b): 002's v1.4 check "stops a runaway guest" has only one
   mechanism in 001's API: `deadline_s` (wall clock). 001's own test
   ("a spinning script with `deadline_s=0.5` reports `trapped`") is a
   timing test that §4.9 calls a bug; the fuel memo (finding 4) says a
   runaway is bounded by fuel. Failure (c): 001's tests live in
   `tests/test_run.py`, marked `artifact` and "skipped cleanly"; under
   002 they are unit tests that skip silently and sit outside the
   ratchet, duplicating v1.4. Failure (d): 001 says "Depends on:
   nothing; first specification"; 002 says 001 lands against it. Fix:
   amend 001 before either is built: name the no-host code (−1) and the
   fault code; give the runner a `fuel` limit (or make `deadline_s`
   epoch-based and test it by fuel, not time); move its tests into
   `tests/checks/test_v1_4_embedding.py` as goal checks with
   `needs: runner`/`needs: artifact set`; make 001 depend on 002.

10. **The native oracle is not pinned, so goldens depend on who ran
    `regen.py`** (`002:93-105`).
    Failure (a): `--python 3.14` floats the patch version (the guest is
    3.14.8; the fuel memo's host was 3.14.2), and python-dateutil,
    tzdata and six float to whatever PyPI serves that day. A tzdata
    release changes a timezone job's golden without any pin moving, and
    the versions line still matches. Nothing is hash-checked, and uv
    caches and runs the native wheels outside `downloads/` and
    `build/` (§4.2, §4.8 tension; the spec gives no reason why that is
    allowed).
    Failure (b): `python -I` ignores `PYTHONHASHSEED` (fuel memo,
    finding 3), so the native run is unseeded too. A job that prints a
    set, or a pandas result whose tie order follows a Python-object hash
    table, is different on each regen and on each plain-reactor run.
    Failure (c): no `.gitattributes`. A Windows checkout with
    `core.autocrlf=true` rewrites `.expected` to CRLF; the guest writes
    LF; the byte compare fails on Windows only, and v1.2's three-OS check
    can never pass. If `regen.py` is ever run on Windows, pandas'
    `to_csv` uses `os.linesep` and the goldens themselves turn CRLF.
    Failure (d): any first-line difference is reported as "goldens are
    stale". If the guest fails to import pandas, the first line is a
    traceback, and the message tells the agent to regenerate goldens.
    Failure (e): "floats are printed rounded" does not say to how many
    digits (§5.2), and "every file it wrote" does not fix the order.
    Fix: pin the oracle in a committed lock (a `tests/jobs/oracle.lock`
    or a second uv project) with hashes and the exact Python patch;
    point `UV_CACHE_DIR` under `build/`; run regen twice with two hash
    seeds and fail if outputs differ; add `tests/jobs/*.expected -text`
    to `.gitattributes`; say "goldens are stale" only when the first
    line parses as a versions line and differs; fix the rounding (for
    example `f"{x:.6g}"`) and sort the written files by path.

11. **Criterion 8 and the `rules` ruff check fail today, on a file
    that may never be edited** (`002:218-219`, `002:254`).
    Failure: `uv run ruff format --check` exits 1 on
    `context/research/2026-10-16-fuel-as-the-operation-count.md:31`
    (ruff formats Python blocks in Markdown). Research memos are "never
    edited after the fact", so a gap for this has no possible closer,
    and the check stays red or gapped forever. Fix: the constitution
    says ruff is green "on `src/` and `tests/`"; run
    `ruff check src tests` and `ruff format --check src tests` in the
    check and the criterion, or add `context` to `extend-exclude`.

12. **A gap swallows any failure, including a different one**
    (`002:31-34`, `002:40-45`).
    Failure: a gap for "the pandas job matches native" (reason: a float
    formatting difference) stays a `gap` when the guest later traps on
    `import pandas`, or when `guest.py` raises `TypeError`. A strict
    `xfail` accepts any exception, so the regression is invisible on that
    check. Memo lesson 5 says an allowance "must name the exact case".
    Errors in setup or teardown have no state among the four. Fix: each
    gap entry carries `raises` (an exception type) and `match` (a message
    prefix); a different failure is `fail`. A pytest `error` outcome is
    `fail`.

13. **`blocked` is self-declared and the need vocabulary is not in the
    spec** (`002:35-39`, `002:152`).
    Failure: a check calls `pytest.skip("needs: owner")` while the thing
    it waits for is present; it reads as `blocked` forever. The spec
    names needs only in passing ("artifact set", "wheel", "owner",
    "the runner", "upstream subsets", "downloads and build trees", "a
    second build host", "accepted runs from all three") and defines no
    predicate for any; that is an undecided choice (§5.2). And `next:`
    will name "artifact set" on every run until v1 is nearly done, which
    tells an agent nothing it can do in one specification. Fix: list the
    vocabulary in the spec, each need with its predicate;
    `need("<name>")` evaluates the predicate and skips only if it is
    false; a skip whose reason names a need whose predicate is true is
    `fail`. Split "artifact set" into the needs a single spec can meet
    (for example "door", "reactor exports", "snapshot", "manifest").

14. **Three checks have no mechanical pass condition** (`002:186`,
    `002:190-191`, `002:212-213`).
    Failure: "the same bytes passed on Linux, macOS and Windows" reads
    the history, but Decision 5's history fields (status, metrics,
    commit, wasmtime version, artifact hash) do not include the
    platform. `accepted.json` is keyed by node id only, so three
    machines overwrite one another's entries. "A second host rebuilt the
    same hash" has the same hole. "The release is published" needs a
    network call to GitHub or PyPI, which the spec neither allows nor
    pins. All three stay `blocked` on needs that no predicate can ever
    find met. Fix: add `platform` and `host_id` to each history line and
    say how the check reads them; for "published", either define it
    (fetch the release's `SHA256SUMS` and compare, marked `slow` and
    `network`) or drop it from the harness and leave it to the release
    spec.

15. **The zero-patch check will be red on the first full build, with no
    closer to name** (`002:209-212`; `scripts/09_build_zlib.sh:6-7`).
    Failure: the script extracts zlib into `build/zlib-1.3.1` and runs
    `./configure` there. zlib's configure copies `zconf.h.in` over
    `zconf.h` and rewrites it with `sed` (configure lines 568–594), and
    writes `Makefile` (870–901). Both files are in the tarball, so the
    tree is not byte-identical. That is a real modification of an
    upstream file, so the check is right; but the spec scopes script
    changes out and names no document that will close the gap. Also,
    "every file the tarball holds" lets added files through: a new
    header placed earlier on the include path shadows an upstream one
    and passes. Fix: name the closer (a script fix building zlib out of
    tree, or the reproducible-build placeholder); define the check as
    "the tree right after extraction and after the build both equal the
    tarball for tarball files, and every added non-generated file is a
    byte copy of a `recipes/` file".

16. **The prior-art overlap scan is undefined, unreproducible and the
    least valuable check for its cost** (`002:216-217`).
    Failure: the clones are git-ignored and refreshed to upstream HEAD,
    so the input differs between machines and days (the index records
    `cpython` on 3.14 at `7c04882`; the spike memo read `main` at
    `fdec4df`). Normalisation is not specified: with identifiers kept,
    `guest.py`'s six lines of wasmtime-py set-up (`Config`,
    `consume_fuel`, `Engine`, `Store`, `Linker`, `define_wasi`) can
    match a wasmtime-py example line for line; with identifiers erased,
    every C module's `PyModuleDef` boilerplate matches CPython. The
    input is 496 MB and over 13,000 source files. A red here invites a
    gap whose closer is nothing. §6.4 (smallest thing): drop the check,
    or narrow it to `recipes/` against the two clones it could be copied
    from (pyodide-recipes, componentize-py), with whitespace-only
    normalisation and the clone commit recorded in the result.

17. **The criteria do not cover the design, and the design's checks are
    not named** (`002:232-254`).
    Failure: criterion 2 accepts four arbitrary checks per area; the
    Design lists about fifty. Criterion 5 omits most ratchet states
    (see criterion 5 above). No criterion requires a job or its
    `.expected` to exist, `regen.py` to reproduce them, the `next:`
    line, Decision 14, or `context/progress/README.md`. The memo's
    lesson 13 names `Generator.poisson` as the call that trapped; v1.3
    says only "`numpy.random` (both APIs)". The wall check does not
    assert `host::call`'s signature `(i32,i32,i32,i32)->i32` from 001.
    Fix: put a table of check node ids in the spec and make criterion 2
    "every listed node id is collected"; extend criterion 5 to every
    ratchet transition and flag; name `Generator.poisson` and the door
    signature; align the line cap (25 everywhere, with at most ten
    `FAIL` lines and a "+N more" line).

18. **Small inconsistencies** (`002:116-119`, `002:74-80`,
    `tests/test_api.py:13-15`).
    - The EXECUTED claim "`grep -a` … finds `3.14.7` once" has no
      command output beside it (§4.10), and
      `grep -a -o "3\.14\.7" build/brett-3.14.7/python.wasm | wc -l`
      gives 2. The conclusion (the binary's version string is not a
      reliable source) still holds.
    - The wheel fallback (`ARTIFACT_DIR` with a `MANIFEST`) is exactly
      the state in which `test_source_checkout_has_no_artifacts` fails;
      the release workflow drops artifacts there before `uv build`. Say
      what happens to that test.
    - The driver's dispatch rule is implicit. State it by exports:
      `_start` → command; `_initialize` and `run` → plain reactor;
      `run` without `_initialize` → snapshot (Wizer removes both init
      exports, READ `wizer/src/rewrite.rs:127-138`). Brett's stdlib is a
      directory (`lib/python3.14`), not a zip; say the driver lays out
      both.
    - Compile each binary once per session: the spike measured
      2.3–2.7 s and up to 1,474 MiB host RSS per in-process compile of
      the 55–94 MB modules (spike memo, finding 8).
    - The embedder-name detector must contain the embedder's name,
      which §4.5 forbids in "code … or test". State the exception, or
      keep the deny-list in a `context/` data file the scanner reads.

## Constitution checks

- §4.1 zero patches — the spec adds the check that enforces it; its
  definition misses added files (finding 15). Holds.
- §4.2 pinned and hashed — the oracle environment is version-pinned
  for two packages only and hash-pinned for none (finding 10); the
  `MANIFEST` check does not require the toolchain, Wizer or the
  pure-Python packages (finding 7). Does not fully hold.
- §4.3 one target — untouched; the harness is host-side test code.
  Holds.
- §4.4 two imports — the spec checks it. The proposed `random_get` /
  `clock_time_get` shadowing (finding 5) changes host bindings, not the
  guest's imports. Holds.
- §4.5 embedder-neutral — the detector itself names the embedder
  (finding 18). Needs a stated exception.
- §4.6 artifact set — adds `LICENSES/` to the set; the list omits
  statically linked components (finding 8). Does not fully hold.
- §4.7 prior art — the scan is undefined (finding 16). No copying
  proposed. Holds.
- §4.8 downloads untrusted — Decision 14 holds for tarballs; native
  oracle wheels are cached and executed outside `build/` without a
  stated reason (finding 10).
- §4.9 tests count — fuel and bytes only; holds in 002. 001's
  `deadline_s=0.5` test, which 002's v1.4 check would inherit, does not
  (finding 9).
- §4.10 claims carry evidence — one EXECUTED claim without output, and
  its count is off (finding 18).
- §4.12 licences — see finding 8.
- §4.13 tooling — wasmtime is added with a reason; holds. Criterion 8 is
  red today (finding 11).
- §4.14 git — `--accept` writes tracked files and never commits. Holds.
- §5.2 no open questions — undecided: the need predicates (finding 13),
  the float rounding rule (finding 10), how three history checks pass
  (finding 14), the `MANIFEST` version lines (finding 7), the scan's
  normalisation (finding 16), and the door's no-host code, which 001
  has not decided (finding 9).
- §5.6 review before build — this review. Holds.
- §6.4 smallest thing — the prior-art scan and the three
  history-dependent checks cost more than they signal (findings 14, 16).
- §7 never-do list — nothing tripped by the spec as written. The
  regen command fetches wheels without hashes, which is close to
  "fetch anything unpinned" (finding 10).

## Disposition (filled in by the author, then confirmed by the reviewer)

By the author, 2026-10-16. "Fixed" means fixed in the revised
specification (and, where named, in spec 001 or a memo), before any
code exists.

1. Missing artifacts read as green — **fixed.** Decision 5: a set
   `$WASI_PYTHON_ARTIFACTS` is the only artifact directory, with no
   fallback, and a missing file fails `test_artifact_set_is_complete`.
   Decision 6: an accepted pass that turns `blocked` is red unless the
   run says `--partial "<why>"`, which the scoreboard prints. Needs are
   split per file (`plain binary`, `snapshot binary`, `stdlib zip`,
   `manifest`), so a partial build blocks only what it lacks.
2. Deleted or renamed checks are not red — **fixed** as proposed:
   deselected is reported; absent (neither collected nor deselected) is
   red until `--retire` records it.
3. Ratchet not tamper-evident; inputs outside the judge — **fixed.**
   History lines chain `prev` and carry the hash of the
   `accepted.json` they wrote; `test_progress_history_is_intact`
   verifies the chain, the last hash, and that the file extends its
   committed version. `pyproject.toml` and `uv.lock` are judging files
   (Decision 14), so a wasmtime bump is a judge change that needs
   `--accept-judge`, which re-baselines fuel.
4. Any `--accept` accepts a weakened judge — **fixed.** `--accept`
   refuses a changed judge without `--accept-judge "<reason>"`; the
   scoreboard lists changed judging files. Gaps live in a judging file,
   so adding one is a judge change; retirements need `--retire` and are
   recorded.
5. Fuel creeps; the tolerance rests on an inert seed — **fixed**, with
   the proposed driver change, after measuring it. New memo
   `2026-10-16-a-host-supplied-clock-and-random-make-fuel-exact.md`
   (EXECUTED): with the host answering `random_get` and
   `clock_time_get`, `-I` runs repeat to within 160 instructions in
   1.14 billion. The tolerance is now 0.01% (Decision 6), and
   `--accept` keeps the minimum of each metric unless
   `--accept-growth` gives a reason (Decision 7).
6. Guest checks never seen to run or fail — **fixed.** Criterion 6:
   `wat2wasm` modules (command, plain reactor, snapshot shape, a third
   import, a missing export) exercise dispatch, the door in all three
   cases, exit codes and the fuel cap. Criterion 7: every v1.1 and v1.4
   check function runs on a good and a bad synthetic artifact
   directory.
7. `MANIFEST` passes vacuously — **fixed.** Decision 12: exactly one
   `python` line; required `package` lines; required pins (CPython,
   each package, wasi-sdk, Wizer); `recipe` lines exactly equal to the
   tracked recipe and script files; unknown first words are errors,
   with `x-` reserved for extensions. The missing python-dateutil,
   tzdata and six pins are now a check of their own
   (`test_pure_python_packages_are_pinned`), a gap closed by the
   CPython 3.15 line memo, which decides the first release's pins.
8. Licences incomplete, empty, not a release asset — **fixed.**
   `wasi-libc` and `llvm-runtimes` join the list; a licence file must
   be non-empty and contain its pinned source's top-level licence byte
   for byte. The layout binds the artifact directory and the wheel
   only; the release specification decides how it ships as assets.
   Bundled sub-licences inside a component (pandas' `LICENSES/`,
   CPython's libmpdec and expat) are **not fixed here**: the rule
   requires the top-level file and allows more, and the release
   specification owns the full notice set (§4.12).
9. 002 decides 001's things, and 001 contradicts them — **fixed by
   amending 001**: it depends on 002; door codes are 0, −1 ("no host")
   and −2 ("host fault"), with `ConnectionRefusedError` and `OSError`
   in the guest; the runner gains `fuel`, and the runaway check uses
   it; `deadline_s` stays as an embedder feature that no test asserts
   on; 001's tests are 002's goal checks; its build writes
   `build/artifacts/`.
10. Oracle not pinned — **fixed.** Decision 11: an oracle uv project
    with a lock and hashes, Python `==3.14.8` and all six packages
    pinned; caches and the interpreter under `build/oracle/`; two runs
    with different seeds must agree; `.gitattributes` keeps goldens
    LF; "stale" only when both lines are versions lines; `.9g` floats;
    files in path order.
11. Ruff red on a memo — **fixed.** Ruff runs on `src tests`, as the
    constitution says (§4.13).
12. A gap swallows any failure — **fixed.** Gaps carry `raises` and
    `match`; setup and teardown errors are `fail` (Decision 3).
13. `blocked` is self-declared — **fixed.** The vocabulary, predicates
    and providers are a table in Decision 5; `need()` skips only when
    the predicate is false, and a skip naming a met need is `fail`.
    `next:` names a providing document, not a need.
14. Three checks cannot pass — **fixed.** History lines carry
    `platform` and `host`, so `test_same_bytes_passed_on_three_systems`
    can read them. The publication check and the second-host check are
    removed from the harness and listed as not machine-checked on the
    scoreboard (Decision 17).
15. Zero-patch red after the first build — **fixed in part.** Its
    closer is named: the reproducible-builds placeholder memo now
    lists configuring zlib outside its tree among the recipe fixes. The
    proposal to also judge added files is **not adopted**: the build
    writes many generated files into the CPython and numpy trees, and
    telling a shadowing header from a generated one needs the build's
    own output list. Building outside the source trees, which that memo
    names, removes the question.
16. Prior-art scan undefined — **fixed by removal** (§6.4). Copying is
    left to review, with the reason stated in Decision 17.
17. Criteria do not cover the design — **fixed.** The checks are a
    table of node ids; criterion 2 requires every one; criterion 5
    lists every ratchet transition and flag; criterion 8 covers the
    goldens; `Generator.poisson` and the door's type are named; the
    line cap is 25 with at most ten `FAIL` lines.
18. Small inconsistencies — **fixed.** The version-string claim now
    carries its command and the count 2. `tests/test_api.py` accepts an
    installed artifact directory. Dispatch is stated by exports, with
    Brett's directory layout supported. Each binary compiles once per
    session. Embedder names move to `context/embedders.txt`.

### Confirmation by the reviewer, 2026-10-16

I checked each finding against the revised documents: spec 002 as
revised (360 lines), spec 001 as amended, the reproducible-builds memo,
and the new memo
`2026-10-16-a-host-supplied-clock-and-random-make-fuel-exact.md`. I did
not rely on the disposition text above.

1. **Confirmed.** Decision 5 (lines 68–70) gives no fallback once
   `$WASI_PYTHON_ARTIFACTS` is set. The needs are split per file.
   Decision 6 (lines 82–83) makes an accepted pass that turns `blocked`
   red unless `--partial` is given, and the scoreboard prints that
   flag. One correction to the disposition text: the fallback to the
   wheel's `ARTIFACT_DIR` still applies when the variable is *unset*
   (Decision 5's table, line 54). That is harmless now, because a
   missing artifact there is `unrun` and so red.
2. **Confirmed.** Decision 3 adds `deselected`. Decision 6 makes
   `absent` red until `--retire`. Criterion 5 tests both. See N8 for
   two run shapes still left without a state.
3. **Confirmed.**
   - History lines now carry `prev` and `accepted`.
   - `test_progress_history_is_intact` checks the chain, the last
     hash, and that the file extends its committed version.
   - `pyproject.toml` and `uv.lock` are judging files (Decision 14),
     so a wasmtime bump goes through `--accept-judge`.
   - Residual: lines not yet committed can still be fabricated as a
     consistent chain. Only review catches that, and §7 already
     forbids it. That is enough.
4. **Confirmed.** `--accept` refuses a judge change without
   `--accept-judge` (Decision 7), and the scoreboard lists the changed
   files. Residual (N8): a history line has one `reason` field, so a
   later reviewer cannot tell which acceptance changed the judge,
   grew a metric or retired a check.
5. **Confirmed for the plain reactor and command modules. Not
   confirmed for the snapshot** (see N1).
   - The driver now answers `random_get` and `clock_time_get` itself
     (Decision 9). The new memo shows that this works under `-I`,
     which I read in its output: spreads of 80–440 in 1.14×10⁹.
   - The tolerance of 0.01% and the minimum-keeping acceptance are in
     Decision 6 and Decision 7.
   - The snapshot is different. Its hash secret is chosen once, inside
     Wizer, at build time, from the build host's real randomness. The
     driver's `random_get` never reaches it.
6. **Confirmed for criterion 6 and for the v1.1 half of criterion 7.
   Not confirmed for the v1.4 half** (see N3).
7. **Confirmed.**
   - Decision 12 has exactly one `python` line, required `package`
     lines, the required pins including wasi-sdk and Wizer, exact
     `recipe` coverage, and errors for unknown first words.
   - `test_pure_python_packages_are_pinned` makes the missing pins
     visible.
   - Small residuals are in N8.
8. **Confirmed in part.**
   - `wasi-libc` and `llvm-runtimes` are listed. Non-empty and
     byte-for-byte rules exist. Leaving the release asset layout to
     the release spec is reasonable.
   - **The partial non-adoption (bundled sub-licences) is acceptable
     on one condition: say it on the scoreboard.** As written, the
     licence check goes green while pandas' bundled notices (klib,
     ujson and the rest) and CPython's libmpdec and expat notices are
     absent. Add them to Decision 17's not-checked list, so the
     scoreboard does not claim §4.12 is fully met.
   - Also see N5: the byte-for-byte rule cannot apply to `wasi-libc`
     or `llvm-runtimes` as worded.
9. **Confirmed in substance.**
   - 001 now depends on 002.
   - The door codes are 0, −1 and −2, with the exceptions named in
     001 Decisions 1–2, matching 002 Decision 9 and the v1.4 table.
   - The runner has `fuel`, and the runaway check uses it.
   - `deadline_s` is untested, and 001 has no tests of its own.
   - Three leftovers in 001 are listed in N4.
10. **Confirmed.**
    - The oracle is its own locked project with Python `==3.14.8`.
    - Caches live under `build/oracle/`.
    - Regeneration runs twice, with two seeds.
    - `.gitattributes`, the stricter rule for "stale", the `.9g`
      format and the file order are all in Decision 11.
    - One residual is N6.
11. **Confirmed in 002** (table lines 295–296, criterion 10). **Not
    yet fixed in 001:** its criterion 4 still runs
    `uv run ruff format --check` on the whole repository, which exits
    1 today (N4).
12. **Confirmed.** Gaps now carry `raises` and `match` (Decision 4).
    Errors in setup, call or teardown are `fail` (Decision 3).
13. **Confirmed.** Decision 5 has the table with predicates and
    providers. `need()` checks the predicate, and a met need is
    `fail`. `next:` names a providing document.
    - The `source trees` predicate is weak (N7).
    - `test_same_bytes_passed_on_three_systems` can only be `pass` or
      `blocked`, never `fail`. That is acceptable for an evidence
      check, but it should be said.
14. **Confirmed.**
    - History lines carry `platform` and `host`.
    - The publication and second-host checks are removed and named
      in Decision 17.
    - But accepted metrics are still one entry per node id across
      platforms (N2).
15. **Confirmed in part.**
    - The closer is named: the reproducible-builds memo, step 1, now
      says zlib is configured outside its tree.
    - **The non-adoption (not judging added files) is acceptable.**
      CPython's `Tools/wasm/wasi` builds into `cross-build/` inside
      its source tree, and the recipe copies two C files into
      `Modules/` on purpose. Telling an added shadowing header from a
      generated file would need the build's output list. The residual
      risk is small, and review can see it, because every copy is a
      line in a script.
    - One correction: the disposition says "building outside the
      source trees, which that memo names, removes the question". The
      memo names this for zlib only, not for CPython or numpy. Drop
      that sentence, or extend the memo.
16. **Confirmed. The removal is acceptable.**
    - Decision 17 states the reason: the input is unpinned because the
      clones are refreshed to upstream heads, and boilerplate makes
      the findings noise.
    - §5.6 already makes the reviewer check §4.7 on every change.
    - A check that cannot be reproduced is worse than an honest
      "not checked" line on the scoreboard.
17. **Confirmed.**
    - The table of node ids, criterion 2, the extended criterion 5,
      criterion 8, `Generator.poisson`, the door's type and the line
      cap are all present.
    - Some table rows cannot be implemented as written (N7, N8, N9).
18. **Confirmed.**
    - The version claim now carries its command and the count 2.
    - Dispatch is stated by exports. Brett's directory layout is
      supported. Each binary compiles once per session.
    - `context/embedders.txt` is in place.
    - The `tests/test_api.py` change is a scope statement. Nothing is
      built yet, so it is checked at landing.

### New findings from the revision, most severe first

N1. **The snapshot's fuel changes on every rebuild by far more than
    0.01%.** (002 Decisions 6, 7 and 9; 001 Decision 4 and
    `recipes/vfs_main.c`.)
    - The snapshot's hash secret is set when `wizer.initialize` runs
      `Py_InitializeFromConfig` with an isolated config. That is at
      build time, inside Wizer, using the build host's real
      `random_get`. The driver's deterministic `random_get` never
      reaches it.
    - Failure: rebuild the snapshot from the same pins and recipes.
      It gets a new secret, so its dict and set layouts differ.
      INFERRED: its fuel on the same job moves by roughly the seed
      effect, measured at 0.21–0.32% for start-up in the two fuel
      memos. That is 20 to 30 times the tolerance.
    - Because acceptance keeps the minimum, about half of all rebuilds
      go red on every snapshot fuel metric. The agent then learns to
      pass `--accept-growth "rebuild noise"`, which is the habit the
      ratchet exists to prevent.
    - The same secret also makes the snapshot impossible to reproduce
      byte for byte. That defeats step 3 of the reproducible-builds
      memo.
    - Fix (001, a recipe decision): `wizer.initialize` sets
      `config.use_hash_seed = 1; config.hash_seed = 0`. This costs no
      security. The published snapshot's secret is already the same
      for every embedder, and anyone can read it from the published
      bytes, so fixing it reveals nothing new. The plain reactor keeps
      a secret chosen at run time.
    - Alternatively, compare snapshot fuel only within one artifact
      hash, and state that the plain reactor carries the
      cross-build fuel ratchet.

N2. **Fuel is compared across platforms against one accepted value,
    with a 0.01% tolerance and minimum-keeping.** (002 Decisions 6 and
    7.)
    - `accepted.json` keeps one entry per node id. The new memo
      measured the residual on one Mac only. Its finding 3 attributes
      that residual to host facts the guest reads, such as inode
      numbers, which differ between operating systems.
    - Failure: macOS accepts fuel F. A Linux run in the release job
      measures F × 1.0002 because its directory listings or stat
      fields differ. The run is red. Acceptance on Linux would lower
      the stored value to the smaller of the two, so macOS goes red
      next.
    - Fix: key accepted metrics by `(node id, platform)`, or compare
      fuel only against an acceptance from the same platform. Record
      in the memo that cross-OS spread is unmeasured.

N3. **Criterion 7 cannot be met for v1.4 before spec 001 exists.**
    (002 lines 349–350 and 272–279.)
    - The v1.4 checks run Python inside the guest (`_host.call`,
      `sys.exit(3)`, `sys.argv`, `os.environ`) or call
      `wasi_python.run`, which 001 has not built yet.
    - A synthetic artifact directory made of `wat2wasm` modules runs
      no Python. No "good" synthetic directory can pass these check
      functions.
    - Fix: limit criterion 7 to v1.1. Rely on criterion 6 for the
      door, exit-code and fuel-cap behaviour at the driver level. Say
      that the v1.4 checks are first seen to pass and fail when 001
      lands, and require that 001's review shows each one failing
      once against a deliberately broken artifact.

N4. **001 has three leftovers that contradict the revision.**
    - 001 Decision 7 (lines 64–68) lists the build's artifact
      directory as the two binaries, the zip, `MANIFEST` and
      `SHA256SUMS`. It has no `LICENSES/`. So
      `test_artifact_set_is_complete` and
      `test_licence_notices_cover_every_component` fail against 001's
      output, and no document is named to close them. 001's criterion
      2 allows only gaps "whose closer is another document". Either
      001 writes `LICENSES/`, or a closer is named.
    - 001 criterion 4 still runs `uv run ruff check` and
      `uv run ruff format --check` on the whole repository. The format
      check exits 1 today on a research memo (finding 11). Change both
      to `src tests`.
    - 001's Design (lines 83–85) still says `_host.available()` is set
      "through a second response code". That contradicts Decision 2,
      which says `True` only after a 0. Delete the sentence.

N5. **The byte-for-byte licence rule has no source to compare against
    for four of the nine components.** (002 lines 174–176.)
    - `wasi-libc` and `llvm-runtimes` have no pinned source of their
      own. They come inside the wasi-sdk binary tarball, whose
      top-level licence is wasi-sdk's own. So the rule is either
      wrong (it compares the wrong file) or empty.
    - python-dateutil, tzdata and six are not pinned, so for them the
      rule falls back to "non-empty".
    - Fix: map each component to its pinned file and the licence path
      inside it, for example the wasi-libc and libc++ licence paths in
      the wasi-sdk tarball, if it ships them. Where there is no such
      file, the check is a gap with a closer, not a silent "non-empty
      is enough".

N6. **The oracle pins three packages that the guest has not pinned,
    and the versions line cannot see a mismatch.** (002 Decision 11.)
    - The oracle fixes python-dateutil 2.9.0.post0, tzdata 2026.5 and
      six 1.17.0. The guest's versions of these are undecided: they
      are a gap closed by the CPython 3.15 memo.
    - The versions line prints only python, numpy and pandas.
    - Failure: the guest ships tzdata 2025.2. A timezone job differs,
      and the agent sees "a plain mismatch" instead of a pin mismatch.
    - Fix: put all six versions in the versions line, and have the
      oracle check compare the oracle lock with `MANIFEST`'s `package`
      lines.

N7. **`test_source_trees_match_their_tarballs` and its need are vague.**
    (002 lines 61 and 288.)
    - The need is met when *a* pinned tarball has *a* tree. The check
      covers "every file the tarball holds" without saying which
      tarballs count.
    - Toolchains (wasi-sdk, Wizer, wasmtime) and Brett's zip are
      pinned too, but they are not source trees. Brett's zip has no
      single top directory, and `build/brett-3.14.7` is a name the
      unpacker chose.
    - Failure: on a machine with only `build/zlib-1.3.1`, the need is
      met, CPython's tree is never compared, and the check passes.
    - Fix: parametrize the check over the four source tarballs
      (CPython, numpy, pandas, zlib), each blocked by its own tree.

N8. **Smaller undecided points and table rows that cannot pass as
    written.**
    - `test_specifications_have_no_open_question` forbids the words
      `TBD`, `TODO` and "open question" in a specification. Spec
      002's own table row (line 299) contains all three. The check
      fails on 002 itself unless quoted or code-span text is exempt.
      Say which.
    - `test_toolchain_is_pinned_for_linux_and_macos` names
      `arm64-macos`. The pinned wasmtime and Wizer files are named
      `aarch64-macos`. Use each tool's own platform string.
    - The driver's random and clock streams must restart for each
      instance. Otherwise fuel depends on test order and on `-k`.
      Decision 9 implies this but does not say it.
    - Two run shapes have no ratchet state:
      - A check that was collected but never ran (`-x`, `--maxfail`,
        an interrupt).
      - Every check after a path-limited run (`uv run pytest
        tests/unit`), which reads as `absent`, so the run is red.
      Say that a run that does not collect `tests/checks/` is
      partial, and that a collected check with no outcome is
      `unrun`.
    - Decision 8 says the plugin timestamps history lines, but
      Decision 6's field list has no timestamp. History lines should
      also carry the judge, growth and retire reasons, and the changed
      judging files, as separate fields.
    - `python` and `package` lines are not checked against the pin
      file names. For example, `python 3.14.8` should agree with
      `Python-3.14.8.tar.xz`. Say how the CPython pin is matched, so
      that a case-insensitive "python" prefix does not match Brett's
      `python-3.14.7-…zip`.
    - `recipe` lines cover every tracked file under `scripts/`,
      including the `bench_*.py` scripts and `01_hello.py`. Editing a
      benchmark then makes the artifacts "stale". Either accept that
      in writing, or limit the lines to files the build runs.

## Verdict

First review: build after the findings are answered. As drafted, the
spec gave false greens for missing artifacts, deleted checks, a
hand-edited ratchet and a weakened judge (findings 1–4). Its fuel
signal rested on a seed that neither product binary honours
(finding 5).

After the revision: **build after the new findings N1–N4 are
answered.**
- Twelve of the eighteen original findings are confirmed fixed
  outright: 1–4, 7, 10, 12–14 and 16–18. Finding 16's removal is
  acceptable.
- Findings 5, 6, 9 and 11 are fixed except for the parts carried into
  N1, N3 and N4.
- Findings 8 and 15 are confirmed in part. Their non-adoptions are
  acceptable, 8 on the condition stated above.
- N1 (the snapshot's hash secret chosen at build time) and N2
  (cross-platform fuel) would make the fuel ratchet noisy enough to
  train an agent to accept growth.
- N3 is a criterion that cannot be met before spec 001 exists.
- N4 is a set of edits to 001.
- N5–N8 may be answered in writing or fixed while building.

## Disposition of the confirmation's findings (by the author, 2026-10-16)

- N1 snapshot hash secret — **fixed in 001** (Decision 4):
  `wizer.initialize` initializes with `use_hash_seed = 1`,
  `hash_seed = 0`; 002 Decision 9 says why the driver's `random_get`
  cannot reach a snapshot and points there.
- N2 cross-platform fuel — **fixed**: metrics are keyed by platform in
  `accepted.json`, compared only on the same platform and wasmtime
  version, and the minimum is kept per platform (Decisions 6 and 7).
- N3 criterion 7 for v1.4 — **fixed**: criterion 7 covers v1.1 only;
  the v1.4 host side is criterion 6, the guest side is first run by 001.
- N4 leftovers in 001 — **fixed**: its artifact directory carries
  `LICENSES/` (Decision 7); criterion 4 scopes ruff to `src tests`; the
  Design's `available()` wording matches Decision 2.
- N5 licence content — **fixed**: the content rule names its sources
  per component, wasi-libc and llvm-runtimes are presence-only and
  listed in Decision 17, with bundled sub-licences (the condition on
  finding 8) and build-added files (finding 15's corrected scope).
- N6 oracle versions — **fixed**: the versions line carries all five
  packages. Also changed here, from a fact found while answering: the
  oracle's interpreter is pinned at 3.14.2, because the pinned uv
  cannot install 3.14.8 (Decision 11 gives the command and output); the
  versions line carries Python as `X.Y`.
- N7 source trees — **fixed**: the zero-patch check is parametrized
  over `cpython`, `numpy`, `pandas`, `zlib`, each blocked by its own
  tree.
- N8 — **fixed**: inline code is exempt from the open-question lint;
  the toolchain row accepts `arm64`/`aarch64` and `x86_64-linux` /
  `linux-x86_64`; the streams restart per instance; path-limited and
  early-stopped runs are reported, not absent; history lines carry
  `at` and separate reason fields; `python`/`package` versions must
  match their pins, and the CPython pin is matched case-sensitively as
  `Python-<X.Y.Z>.tar.xz`; `scripts/bench_*` are not recipe lines.
  `scripts/01_hello.py` stays a recipe line: it is the toolchain probe,
  and editing it should mark an artifact stale.

The verdict's condition (N1–N4 answered) is met; the build proceeds.
The build's own review re-checks these against the code.

