# 002 — The progress harness

- **Status:** landed, 2026-10-16 (drafted, reviewed as a
  specification, revised, built, reviewed as a build, fixed, and
  confirmed the same day; see the landing notes).
- **Owner:** Clay Gendron
- **Kind:** test infrastructure (`tests/`, `context/progress/`,
  `context/embedders.txt`, `.gitattributes`, `pyproject.toml` dev
  group). It fixes what the harness reads from the artifact directory
  (`MANIFEST`, `LICENSES/`), so it was reviewed once before build
  (constitution §5.6).
- **Depends on:** nothing. Spec 001 depends on it and lands against it.
- **Research it stands on:**
  `../research/2026-10-16-how-autonomous-ports-were-run.md` (lessons
  1 to 14), `../research/2026-10-16-fuel-as-the-operation-count.md`
  (findings 1 to 7), `../research/2026-10-16-a-host-supplied-clock-and-random-make-fuel-exact.md`
  (findings 1 to 4), `../research/2026-10-16-the-spike-that-proved-the-build.md`
  (its failure modes, jobs and layout).

## Decisions

1. **One command is the judge: `uv run pytest`.** The scoreboard is a
   pytest plugin (`tests/conftest.py` over `tests/harness/`). The
   constitution already demands a green pytest, so the judge and the
   gate are one thing.
2. **A check is a pytest test marked `goal("<area>")`.** Areas: `v1.1`
   … `v1.5` (constitution §2, items 1 to 5) and `rules` (the
   mechanically checkable parts of §4, §5 and §7). Unmarked tests are
   the unit suite, counted apart. The checks are exactly the node ids
   in the table under *Design*.
3. **Every check ends in exactly one of five states.**
   - `pass`: it ran and held.
   - `fail`: it ran and did not hold, or errored in setup, call or
     teardown, and no gap covers it. The run is red.
   - `gap`: it failed in exactly the way a gap entry names (Decision
     4).
   - `blocked`: it called `need("<name>")` and that need's predicate is
     false. A goal check that skips any other way, or names a need
     whose predicate is true, is `fail`.
   - `deselected`: pytest deselected it (`-m`, `-k`, `--deselect`).
4. **A gap names its exact case and its closer.** Each entry in
   `tests/known_gaps.toml` has `check` (a node id in the table),
   `raises` (an exception class name, default `AssertionError`),
   `match`, `reason` (one line) and `closes_with` (an existing path
   under `context/` or `README.md`). Every check reports its findings
   as `N finding(s), digest <12 hex>`, the digest being the SHA-256 of
   the sorted findings with their line numbers removed (so an edit that
   only moves a finding leaves its gap alone), and a gap's `match` must
   contain that phrase.
   So a gap admits exactly the findings it was written for: one more or
   one fewer is a different failure, and `fail`. A failure of another
   type is `fail`. A gap whose check passes is `fail` with "remove the
   gap". An `xfail` marker or `pytest.xfail()` on a goal check with no
   gap entry is `fail`.
5. **Needs are a fixed vocabulary with predicates** (`tests/harness/needs.py`).
   Each has a predicate and the document that provides it:

   | need | met when | provided by |
   |---|---|---|
   | `artifact dir` | `$WASI_PYTHON_ARTIFACTS` is set, or the wheel's `ARTIFACT_DIR` holds `MANIFEST` | spec 001 |
   | `plain binary` | the artifact directory holds `python.wasm` | spec 001 |
   | `snapshot binary` | it holds `python-snapshot.wasm` | spec 001 |
   | `stdlib zip` | it holds `python-stdlib.zip` | spec 001 |
   | `manifest` | it holds `MANIFEST` | spec 001 |
   | `runner` | `wasi_python.run` exists | spec 001 |
   | `wasmtime-py` | `import wasmtime` works | this specification |
   | `wheel` | `dist/` holds a `wasi_python` wheel | `README.md` (Next, item 4) |
   | `source tree <name>` | for `<name>` in `cpython`, `numpy`, `pandas`, `zlib`: its pinned tarball is in `downloads/` and the tarball's top directory exists under `build/` | the reproducible-builds memo |
   | `three systems` | `history.jsonl` holds accepted runs of this artifact's hash from `linux`, `darwin` and `win32` | `README.md` (Next, item 4) |
   | `oracle` | the pinned oracle environment resolves offline (Decision 11) | this specification |
   | `reference build` | `build/brett-3.14.7/python.wasm` exists (self-tests only) | this specification |
   | `prior-art clones` | `context/prior_art/` holds at least one clone | `context/prior_art/README.md` |
   | `git` | `git rev-parse HEAD` succeeds in the repository | — |

   Amended 2026-10-17 by spec 029 (Decision 7): the need `git history`, met when `git rev-parse --is-shallow-repository` prints `false` (provided by —).

   Amended 2026-10-18 by spec 062 (Decisions 1 and 7): `three systems` reads every volume of the history (`history.jsonl`, then `history-<n>.jsonl`), replaying each line's passed set; on a history that does not replay it is not met.

   Amended 2026-10-18 by spec 050 (Decision 13): the need `upstream kit`, met when every wheel of `tests/upstream/kit.txt` is in `build/upstream/wheels/` with its SHA-256 (provided by spec 050; `uv run python tests/upstream/fetch.py` fetches it). It is local tooling, not protected.

   When `$WASI_PYTHON_ARTIFACTS` is set, the artifact directory is
   that path and nothing else; there is no silent fallback. A missing
   file there makes `test_artifact_set_is_complete` fail.
6. **The ratchet.** `context/progress/accepted.json` holds, per check,
   its last accepted status, commit and artifact hash, and its
   metrics keyed by platform (`darwin-arm64`, `linux-x86_64`, …), plus
   the judge hash and the per-file judge hashes.
   `context/progress/history.jsonl` gets one line per acceptance, never
   rewritten. Each line carries `prev` (the SHA-256 of the previous
   line) and `accepted` (the SHA-256 of the `accepted.json` it wrote),
   plus `at` (UTC time), `platform`, `host` (a hash of the host name),
   `commit`, `artifact`, `wasmtime`, `reason`, `judge_reason`,
   `growth_reason`, `partial_reason`, `retired`, and the list of checks
   that passed. (Amended 2026-10-18 by spec 062: the history continues in
   volumes named by their first line, each within `1 << 19` bytes, chained as
   one; a line written since then records the change in the passed set and a
   digest of the whole set, not the list.) After every
   run the plugin compares the run with `accepted.json` by node id; for
   each accepted `pass`:
   - now `fail` or `gap` → **lost**, red;
   - now `blocked` by a protected need (`artifact dir`, `plain
     binary`, `snapshot binary`, `stdlib zip`, `manifest`, `runner`,
     `wheel`) → **unrun**, red unless the run says `--partial
     "<why>"`, which the scoreboard prints: a missing product is how a
     regression would hide;
   - now `blocked` by any other need (local tooling a fresh clone
     lacks: clones, the oracle, source trees, git) → **unrun
     locally**, reported;
   - now `deselected` → reported;
   - not run because its file was outside the paths this run was
     given, or because the run stopped early (`-x`, `--maxfail`) →
     reported;
   - its file is gone, or its file was collected (as a whole, not
     narrowed to node ids) without it, including when its `goal`
     marker was removed → **absent**, red until `--retire` records
     it; `--retire` accepts only absent checks;
   - and for any check now `pass` that was not → **gained**, reported.
   **Metrics:** a `fuel` value above the accepted one by more than
   0.01% on the same platform and wasmtime version is red; a `bytes`
   value above the accepted one at all is red; a metric a passing check
   no longer records is red. Fuel on a platform with
   no accepted value is recorded, not compared. On a different wasmtime version fuel is
   not compared, and the change shows as a judge change (`uv.lock`).
   **Judge:** a judge hash different from the accepted one is reported
   with the changed files.

   Amended 2026-10-18 by spec 050 (Decisions 9, 12, 13; condition C1):
   - a metric that must not fall (`passes`) that falls goes to its own list, `fewer`, red, printed
     `FEWER <node>: passes <old> -> <new>` before any `GREW` line and never cut; one that rises
     goes to `more`, reported, not to `gained` (which counts checks);
   - an accepted `gap` whose check is absent from a run that collected its whole file (or whose
     file is gone) is reported **absent**, as an accepted pass is, so `--retire` can take it; an
     accepted gap is never "lost";
   - an accepted pass or gap in `tests/checks/test_v1_3_upstream_suites.py` that did not run here
     (blocked, deselected, unrun, or outside the run) is counted as `upstream unrun`.
7. **Acceptance is explicit and narrow.** `uv run pytest --accept
   "<reason>"` writes `accepted.json` and appends to `history.jsonl`,
   only when the run is green and the ratchet is not red. It also
   refuses a changed judge unless `--accept-judge "<reason>"` is given,
   and metric growth unless `--accept-growth "<reason>"` is given.
   Without `--accept-growth`, each accepted metric (per platform)
   becomes the minimum of the old and the new value, so a metric can only move down
   quietly. `--retire <node id>` (repeatable, with `--accept`) removes a
   check from the protected set; the reason is recorded. A check that
   did not run keeps its accepted entry.

   Amended 2026-10-18 by spec 050 (Decisions 12, 13): a fall in `passes` is accepted only with
   its own flag, `--accept-fewer-passes "<why>"`, recorded in the history line's `fewer_reason`;
   `--accept-growth` never accepts it. Without the flag, acceptance keeps the maximum of the old and
   new `passes`. `--accept` refuses while any upstream-suite check with an accepted pass or gap did
   not run here, unless `--partial "<why>"` is given.
8. **Metrics are counts.** `fuel` (wasm instructions executed) and
   `bytes`. Checks record them through a `metric(name, value)` fixture.
   No check, job or unit test reads a clock; the plugin reads one only
   to timestamp a history line.

   Amended 2026-10-18 by spec 050 (Decision 12): a third metric, `passes`, the number of upstream
   tests a group check saw pass. It must not fall; acceptance keeps the maximum. A check may also
   attach reported facts to its record in `build/progress/latest.json` through a `fact(name,
   value)` fixture, under `facts` (a group's `passed_digest`, its outcome counts, the files left
   out of its staging); facts are never ratcheted.
9. **The harness drives the guest itself.** `tests/harness/guest.py` is
   a minimal wasmtime-py driver, kept apart from the runner it judges
   (lesson 2). It compiles each binary once per session. It lays out
   the guest root (`/usr/local/lib/python3XY.zip` from a zip, or
   `/usr/local/lib/python3.XY/` from a directory, `3.XY` from
   `MANIFEST`'s `python` line or given by the caller), preopens it at
   `/`, and keeps stdout and stderr outside it. It dispatches by
   exports: `_start` → a command module; `_initialize` and `run` → the
   plain reactor, `_initialize` then `run`; `run` without `_initialize`
   → a snapshot, `run` alone. It binds `host::call` with the type
   `(i32, i32, i32, i32) -> i32`: the default binding returns −1 ("no
   host") and writes nothing; a check may pass a callable from request
   bytes to response bytes, which the driver writes through the
   guest's exported `host_alloc`, storing the pointer and length, and
   returning 0; a callable that raises returns −2 ("host fault"). It
   answers `random_get` from a SHA-256 counter stream and
   `clock_time_get` from a fixed start advancing one microsecond per
   call (clock memo), both restarting for each instance, so every run
   is seeded alike. A snapshot's hash secret is set inside Wizer, not
   by these calls; spec 001 fixes it (its Decision 4), so snapshot fuel
   repeats across rebuilds too. It
   meters fuel and caps it at 2×10¹¹ by default, a deterministic
   deadline. It is also the evidence that the bare contract (preopen,
   bind one function, call one export) runs the artifact.
   Amended 2026-10-19 by spec 065 (Decision 9, the clock): the driver also answers `clock_res_get`
   itself, so the guest sees each clock's resolution from the judge, not the host: realtime and
   monotonic 1 µs (the step), the CPU-time clocks 1 ns, though every clock steps 1 µs. These are
   the values a darwin host answered, so no accepted darwin result moved; a Linux host answered
   1 ns for all of them. One consequence: CPython's four `test_int` denial-of-service tests skip
   on every host (a 1 µs conversion is below twice the resolution), so the judge does not exercise
   the integer-to-string limit. Guarded by
   `tests/checks/test_v1_2_portable_and_sealed.py::test_the_guest_clocks_resolution_is_the_judges`.

10. **wasmtime-py joins the dev group** (`wasmtime>=49,<50`; the exact
    version is in `uv.lock`). Reason: the checks need an engine with a
    fuel meter, custom imports and import shadowing, and wasmtime-py is
    the engine the `run` extra already names. `wasmtime.wat2wasm`
    builds the self-tests' small modules.
11. **The oracle is native Python at the guest's pins.** It is its own
    uv project, `tests/jobs/oracle/` (`pyproject.toml` and `uv.lock`
    with hashes): Python `==3.14.2`, numpy 2.5.2, pandas 3.0.6,
    python-dateutil 2.9.0.post0, tzdata 2026.5, six 1.17.0. Reason: the
    guest is built from these package pins, so the same pins natively
    are the only fair oracle. The interpreter is 3.14.2, not the
    guest's 3.14.8, because 3.14.2 is the newest 3.14 that the installed
    uv (0.9.22; uv itself is not pinned by this repository) can install
    and verify (EXECUTED: `uv python list
    --all-versions` lists 3.14.1 and 3.14.2 at most; `uv lock` with the
    six pins resolves with 45 SHA-256 hashes). INFERRED: a CPython patch
    release changes nothing these jobs print. `tests/jobs/regen.py` runs it with
    `UV_CACHE_DIR`, `UV_PYTHON_INSTALL_DIR` and
    `UV_PROJECT_ENVIRONMENT` under `build/oracle/`, so its downloads
    stay under `build/` (§4.8). It runs each job twice, with
    `PYTHONHASHSEED` 0 and 1, and refuses to write when the two
    outputs differ. Each job takes a data directory and an output
    directory as arguments, prints `versions python=<X.Y> numpy=…
    pandas=… python-dateutil=… tzdata=… six=…` first, formats every float as `format(x, ".9g")` (pandas
    with `float_format="%.9g"`), writes files with `\n` line endings,
    and the expected output is its stdout followed by each written
    file in path order, each after a `=== <name>` line.
    `.gitattributes` marks `tests/jobs/*.expected` as `-text`. The
    guest check says "goldens are stale" only when both first lines
    parse as versions lines and differ; any other difference is a
    plain mismatch with the first differing line.
12. **What the harness reads from the artifact directory.** In it:
    `python.wasm`, `python-snapshot.wasm`, `python-stdlib.zip`,
    `MANIFEST`, `SHA256SUMS`, and `LICENSES/<component>.txt` for
    `cpython`, `numpy`, `pandas`, `zlib`, `python-dateutil`, `tzdata`,
    `six`, `wasi-libc` and `llvm-runtimes` (libc++, libc++abi and
    compiler-rt, which wasi-sdk links in). This is the directory's
    layout and the wheel's; how the release ships it as assets is the
    release specification's choice. `MANIFEST` is text, one entry per
    line; blank lines, `#` comments and lines starting `x-` are
    ignored; any other first word than these four is an error:
    - `python <X.Y.Z>`: exactly one;
    - `package <name> <version>`: one each for `numpy`, `pandas`,
      `zlib`, `python-dateutil`, `tzdata`, `six`;
    - `pin <sha256> <file>`: each must equal a line of
      `downloads/SHA256SUMS`; there must be one for the CPython source,
      for each package, for wasi-sdk and for Wizer (matched by file
      name prefix, `-` and `_` alike), and the version in each
      `python` and `package` line must be the version in its pin's file
      name; the CPython pin is the one named exactly
      `Python-<X.Y.Z>.tar.xz` (case-sensitive), so Brett's
      `python-3.14.7-…zip` never matches it;
    - `recipe <sha256> <path>`: exactly one per file tracked under
      `recipes/` and `scripts/` except `scripts/bench_*` (benchmarks
      are not build inputs), each matching the tree; otherwise the
      artifact is stale.
    A licence file must be non-empty. For `cpython`, `numpy`,
    `pandas` and `zlib`, when the pinned tarball is in `downloads/`, it
    must also contain the tarball's top-level licence file byte for
    byte; for `python-dateutil`, `tzdata` and `six` the same holds
    against the pinned wheel's licence file once they are pinned. The
    check's message lists which components were checked for content
    and which for presence only. Reason: the guest's zip is named
    `python3XY.zip` and the binary does not state its version reliably
    (EXECUTED: `grep -a -o '3\.14\.7' build/brett-3.14.7/python.wasm |
    wc -l` → `2`, one followed by a NUL and one by `-dirty`); and a
    rule per line and per file makes each check mechanical.
13. **Output is written for an agent.** At the end of every run the
    plugin prints at most 25 lines: the totals; one line per area; the
    blocked checks grouped by need and the gaps grouped by closer; a
    `next:` line naming the document that unblocks or closes the most
    checks; at most ten `FAIL <node id> — <reason>` lines and a `+N
    more` line; and the ratchet result. The full record is
    `build/progress/latest.json` (git-ignored). The fast tier is
    `-m "not slow"`; `slow` marks the golden jobs and the oracle check.
14. **The judging files** are everything under `tests/`,
    `context/embedders.txt`, `pyproject.toml`, `uv.lock`,
    `.gitattributes`, any `pytest.ini`, `tox.ini`, `setup.cfg` at the
    root, and any `conftest.py` anywhere outside build output,
    downloads, clones and virtual environments: every file that can
    decide a check or steer pytest from inside the repository. Their
    combined hash is the judge hash, keyed by POSIX paths;
    `.gitattributes` checks out every text file with LF endings, so the
    hashes agree across hosts. What can steer pytest from outside the
    repository is refused instead of hashed: in a run of this
    repository, a configuration file other than `pyproject.toml`, or a
    plugin that is neither pytest's own nor a judged file, turns the run
    red; `PYTEST_ADDOPTS` and a non-default `--progress-dir`,
    `--known-gaps` or `--progress-latest` are announced on the
    scoreboard, and `--accept` refuses while `PYTEST_ADDOPTS` is set.
    The harness guards against drift and mistakes, not against an agent
    that rewrites the interpreter; review is the backstop for that.
15. **Embedder names live in `context/embedders.txt`**, a data file the
    scanner reads, so no code or test names an embedder (§4.5).
16. **Downloads stay under `downloads/` and `build/`.** Any check or
    self-test that unpacks one does it under `build/harness/`, never in
    the system temporary directory (§4.8).
17. **Not checked by the harness, and said so on the scoreboard's last
    two lines:**
    licence content for `wasi-libc` and `llvm-runtimes` (the wasi-sdk
    tarball carries them; their paths in it are not yet read) and for
    any component whose pin is missing (presence only); bundled
    sub-licences inside a component (pandas' `LICENSES/`, CPython's
    libmpdec and expat), which the release specification owns; files
    a build adds inside a source tree (CPython and numpy build in their
    trees and the recipe copies files into `Modules/` on purpose; the
    zero-patch check judges every file the tarball holds);
    publication of the release and the wheel (an owner action, §7);
    a rebuild on a second host reproducing the hash (the
    reproducible-builds memo decides how that is recorded); copying
    from prior art (left to review: the clones are refreshed to
    upstream heads, so a scan has no pinned input, and boilerplate
    makes its findings noise); numpy's and pandas' own test subsets
    (`README.md`, Next, item 5, will add their checks).

    Amended 2026-10-18 by spec 050 (Decision 17): numpy's and pandas' own tests are checked
    (`tests/checks/test_v1_3_upstream_suites.py`); the line's first part now reads "publication ·
    copying from prior art · numpy's 25 files that need its C test modules (number 89) · pandas
    beyond eight groups".

## Intent

After this specification an agent working alone can answer three
questions at any moment, from one command, without reading a summary:
how far is v1, what broke since the last accepted state, and what to
do next. Every later specification lands by moving named checks from
`blocked` or `gap` to `pass`.

## Design

```
tests/
  conftest.py            markers, needs, gaps, metrics, scoreboard, ratchet, --accept
  known_gaps.toml        allowances, each with its exact failure and closer
  harness/
    needs.py             the need vocabulary, predicates, providers; need()
    paths.py             repository paths; the artifact directory; MANIFEST parsing and rules
    wasm.py              a reader for a core module's types, imports and exports
    pins.py              SHA256SUMS parsing; tarball against tree (zero patches)
    guest.py             the wasmtime-py driver
    scan.py              repository scanners and document lint
    scoreboard.py        states, summary, ratchet, acceptance (pure functions)
    jobs.py              golden comparison
  checks/                the goal checks below
  jobs/                  golden jobs, .expected outputs, regen.py, oracle/
  unit/                  self-tests: every detector both ways; the plugin end to end
context/progress/        accepted.json, history.jsonl, README.md
context/embedders.txt    the embedder names no code may use
```

The checks. Every node id below is collected; `[b]` means the check
is parametrized over `plain` and `snapshot`.

| node id (under `tests/checks/`) | holds when | needs |
|---|---|---|
| **`test_v1_1_artifact_set.py`** | | |
| `test_artifact_set_is_complete` | all files of Decision 12 exist | artifact dir |
| `test_sha256sums_match_the_files` | `SHA256SUMS` lists every file of the set, each matching | artifact dir |
| `test_no_compiled_module_in_the_set` | no `.cwasm` anywhere in it | artifact dir |
| `test_binary_is_a_core_wasm_module[b]` | magic and version 1 | the binary |
| `test_imports_are_wasi_and_the_door_only[b]` | import modules are exactly `wasi_snapshot_preview1` and `host`; `host` gives only `call` of type `(i32,i32,i32,i32)->i32` | the binary |
| `test_plain_reactor_exports` | `memory`, `_initialize`, `wizer.initialize`, `run`, `host_alloc` | plain binary |
| `test_snapshot_exports` | `memory`, `run`, `host_alloc`; no `_initialize`, no `wizer.initialize` | snapshot binary |
| `test_manifest_is_well_formed` | Decision 12's line rules | manifest |
| `test_manifest_pins_match_the_pin_list` | every `pin` line is in `downloads/SHA256SUMS`; the required pins are present; `python` and `package` versions match their pins' names | manifest |
| `test_manifest_recipes_match_the_tree` | `recipe` lines are exactly the tracked recipe and script files (not `scripts/bench_*`), hashes equal | manifest |
| `test_licence_notices_cover_every_component` | Decision 12's licence rule | artifact dir |
| `test_stdlib_zip_is_bytecode_only_and_deflated` | no `.py` member, every member deflated | stdlib zip |
| `test_wheel_carries_the_artifact_set` | the wheel holds the set under `wasi_python/artifacts/`, same bytes | wheel, artifact dir |
| **`test_v1_2_portable_and_sealed.py`** | | |
| `test_guest_runs_here[b]` | `print(1)` → exit 0, stdout `1\n`; fuel recorded | the binary, stdlib zip, manifest |
| `test_guest_sees_only_its_root` | `/` lists exactly the root; `/..` is `/`; `/etc/hosts` is absent | plain binary, … |
| `test_guest_has_no_network` | creating and connecting a socket raises `OSError` | plain binary, … |
| `test_nothing_is_a_shared_library` | no `.so`, `.dylib`, `.pyd` in the zip; every numpy and pandas extension module's origin is `built-in` | plain binary, … |
| `test_same_bytes_passed_on_three_systems` | the need's predicate | three systems |
| **`test_v1_3_data_stack.py`** | | |
| `test_numpy_and_pandas_are_builtin_at_manifest_versions[b]` | versions equal the `package` lines | the binary, … |
| `test_numpy_csv_job_matches_native` (slow) | output equals `jobs/numpy_csv.expected` | plain binary, … |
| `test_pandas_csv_job_matches_native` (slow) | output equals `jobs/pandas_csv.expected` | plain binary, … |
| `test_random_matches_native` (slow) | `Generator` (`random`, `normal`, `integers`, `poisson`, `choice`, `multinomial`) and the legacy API (`seed`, `rand`, `normal`, `binomial`, `randint` with `dtype=int64`, `poisson`, `multinomial`) equal `jobs/random.expected` | plain binary, … |
| `test_longdouble_parses` | `np.longdouble("0.1")` parses; `finfo(longdouble).bits == 128` | plain binary, … |
| `test_gzip_round_trips` | `gzip` and a deflated `zipfile` round-trip | plain binary, … |
| `test_default_integer_width_is_documented` | the README's "default integer is N-bit" matches `np.dtype(np.int_).itemsize * 8` in the guest | plain binary, … |
| `test_snapshot_preimports_the_stack` | `numpy` and `pandas` are in `sys.modules` before user code; `import pandas` costs the snapshot under a tenth of the plain binary's fuel | both binaries, … |
| `test_goldens_reproduce_under_the_pinned_oracle` (slow) | `regen.py --check` reproduces every `.expected` | oracle |
| **`test_v1_4_embedding.py`** | | |
| `test_door_without_a_host_says_so[b]` | `_host.call(b"x")` raises `ConnectionRefusedError`; `_host.available()` is `False` | the binary, … |
| `test_door_round_trips_bytes_through_a_host[b]` | with `frame[::-1]` bound, `_host.call(b"abc") == b"cba"` and `_host.available()` is `True` | the binary, … |
| `test_run_returns_the_exit_code[b]` | `sys.exit(3)` → 3 | the binary, … |
| `test_run_reads_argv_and_environment_each_call[b]` | `sys.argv[1:]` and `os.environ` are this call's | the binary, … |
| `test_runner_runs_a_program_in_one_call` | `wasi_python.run(["-c", "print(1)"], root=…)` → exit 0, stdout `1\n` | runner, artifact dir |
| `test_runner_binds_a_host` | `host=lambda f: f[::-1]` round-trips through `_host.call` | runner, artifact dir |
| `test_runner_stops_a_runaway_guest_by_fuel` | `fuel=10**9` on `while True: pass` → `trapped`, no exit code | runner, artifact dir |
| **`test_v1_5_rebuild_from_pins.py`** | | |
| `test_pin_list_is_well_formed` | `<64 hex>  <name>` lines, names unique | — |
| `test_every_pin_is_fetched_from_a_literal_url` | every pinned name is the basename of a literal URL in `scripts/00_download.sh` | — |
| `test_download_script_verifies_and_never_writes_the_pins` | it runs a hash check against `SHA256SUMS` and never redirects into it | — |
| `test_no_build_script_fetches_outside_the_download_script` | no `curl`, `wget`, `pip`, `uv pip`, `uv add`, `git clone` elsewhere in `scripts/` | — |
| `test_every_repository_path_a_recipe_names_exists` | each `$HERE/<p>` or `@S12@/<p>` outside `build/`, `downloads/`, `.venv-build/` exists | — |
| `test_toolchain_is_pinned_for_linux_and_macos` | wasi-sdk, Wizer and wasmtime pins exist for Linux x86_64 and macOS arm64 (a file name containing `x86_64-linux` or `linux-x86_64`, and one containing `arm64-macos` or `aarch64-macos`) | — |
| `test_pure_python_packages_are_pinned` | python-dateutil, tzdata and six are in `SHA256SUMS` | — |
| `test_source_tree_matches_its_tarball[cpython\|numpy\|pandas\|zlib]` | every file the tarball holds is byte-identical in `build/<top>/` | source tree `<name>` |
| `test_release_workflow_runs_the_zero_patch_check` | a workflow under `.github/workflows/` has `workflow_dispatch` and runs `test_source_tree_matches_its_tarball` | — |
| **`test_rules.py`** | | |
| `test_no_embedder_name_in_code` | no name from `context/embedders.txt` in any path or text under `recipes/`, `scripts/`, `src/`, `tests/`, `fixtures/` | — |
| `test_no_artifact_or_large_file_is_tracked` | no tracked `*.wasm`, `*.cwasm`, `*.zip`, `*.tar.*`; none over 1 MiB | git |
| `test_every_prior_art_clone_has_its_licence_recorded` | each clone has a licence file and a row with a licence in the index | prior-art clones |
| `test_no_test_reads_a_clock` | no clock call in `tests/checks/`, `tests/unit/`, `tests/jobs/`, `tests/test_*.py` | — |
| `test_ruff_check_is_clean` | `ruff check src tests` exits 0 | — |
| `test_ruff_format_is_clean` | `ruff format --check src tests` exits 0 | — |
| `test_build_scripts_call_python_only_through_uv_or_a_path` | no bare `python`, `python3` or `pip` command word in `scripts/` shell files | — |
| `test_specifications_have_their_header_and_sections` | the header fields and the six sections of `context/README.md` | — |
| `test_specifications_have_no_open_question` | outside inline code, no `TBD`, `TODO`, `open question` or a heading containing `Questions` in a specification, `README.md` or `AGENTS.md` | — |
| `test_landed_specifications_cite_an_existing_review` | a landed specification's landing notes name a file under `context/reviews/` that exists | — |
| `test_executed_memos_label_their_claims` | every non-placeholder memo uses EXECUTED, READ or INFERRED | — |
| `test_known_gaps_are_well_formed` | Decision 4's fields; the check is in this table; the closer exists | — |
| `test_progress_history_is_intact` | the `prev` chain holds; the last line's `accepted` is the hash of `accepted.json`; the file extends its committed version | — (git for the last part) |

## Scope

In: the above, and these amendments elsewhere, each answering the
review: spec 001 depends on this one, names the door's codes, gives the
runner a fuel limit, moves its tests here, and writes its outputs as
an artifact directory; the reproducible-builds placeholder memo names
the recipe fixes its run needs; `tests/test_api.py` accepts an
installed artifact directory; ruff's checks run on `src` and `tests`.
Out: building or fetching any artifact; changing any recipe or script
(the gaps name who will); the runner itself (spec 001); running the
checks in CI (the release specification); parallel agents (research
memo, lesson 15).

## Acceptance criteria

1. `uv run pytest` exits 0 in a source checkout with no artifacts,
   prints the scoreboard in at most 25 lines, and writes
   `build/progress/latest.json`.
2. Every node id in the table is collected, each with the area of its
   file, and none ends `fail`.
3. Every `blocked` check names a need of Decision 5 whose predicate is
   false; every gap names a node id from the table and an existing
   closer.
4. Each detector in `scan.py`, `wasm.py`, `pins.py`, `paths.py`
   (`MANIFEST` and licence rules), `jobs.py` and `scoreboard.py` has a
   unit test that shows it firing on a bad input and quiet on a good
   one.
5. The plugin's end-to-end self-tests (pytester) show each of: an
   unnamed skip of a goal check is `fail`; a skip naming a met need is
   `fail`; an error in setup is `fail`; a gap with the wrong message is
   `fail`; a gap that passes is `fail`; lost, unrun (and `--partial`),
   deselected, absent (and `--retire`), gained; fuel over and under
   0.01%; fuel on another platform or wasmtime version not compared;
   bytes growth; a path-limited run reporting, not failing;
   `--accept` refusing a loss, a judge change without `--accept-judge`
   and growth without `--accept-growth`; `--accept` keeping the
   minimum metric; carried-over entries; history appended with a valid
   `prev` chain.
6. The driver's self-tests pass: against small modules built with
   `wasmtime.wat2wasm` (a command, a plain reactor, a snapshot shape,
   one with a third import, one missing an export) for dispatch, the
   door (no host, a host, a host that raises), exit codes and the fuel
   cap; and against Brett's 3.14.7 build when present for stdout, root
   isolation, a fuel cap that traps, and two `-I` runs whose fuel
   differs by under 0.01%.
7. Each v1.1 check function is shown passing on a synthetic good
   artifact directory and failing on a bad one. The v1.4 checks run
   Python in the guest or call the runner, so their host side (the
   driver's door) is covered by criterion 6 and their guest side is
   first run by spec 001.
8. `.expected` files exist for the three jobs, produced by `regen.py`,
   and `test_goldens_reproduce_under_the_pinned_oracle` passes here.
9. `context/progress/accepted.json` exists, accepted with the reason
   "initial baseline", and `history.jsonl` has its first line.
10. `uv run ruff check src tests` and `uv run ruff format --check src
    tests` are clean.

## Landing notes

Built and landed 2026-10-16 by the author agent, after two reviews by
fresh agents.

**What exists.** `tests/harness/` (needs, paths, wasm, pins, guest,
scan, scoreboard, jobs, plus two modules the Design did not list:
`plugin.py`, the plugin itself, loaded by a three-line
`tests/conftest.py`, and `artifacts.py`, the v1.1 rules as functions
over a directory so criterion 7 can run them on synthetic sets);
`tests/checks/` (67 goal checks over six files, every node id of the
table); `tests/unit/` (113 self-tests); `tests/jobs/` (three jobs,
their goldens, `regen.py`, the oracle project with its `uv.lock`);
`tests/known_gaps.toml` (eight gaps); `context/progress/`;
`context/embedders.txt`; `.gitattributes`.

**Numbers (EXECUTED, this machine, `uv run pytest -q -p no:cacheprovider`):**
`wasi_python v1: 14/67 pass · 8 gap · 45 blocked · 0 fail (unit suite
133/133)`; `147 passed, 45 skipped, 8 xfailed`, exit 0. In a fresh
`git clone` with the change overlaid (no downloads, build trees,
clones or oracle): `12/67 pass · 8 gap · 47 blocked · 0 fail`,
`unrun locally 2`, exit 0 on both tiers. Fast tier
(`-m "not slow"`): 4 deselected, the accepted oracle pass reported as
"not selected 1", exit 0. `--accept "initial baseline"` wrote
`accepted.json` and history line 1 (14 passes protected). Hand-removing
one entry from `accepted.json` turned the run red twice over
(`test_progress_history_is_intact` failed, and the ratchet reported a
lost pass); restoring the file made it green.

**Criteria.**
1. Exit 0 with no artifacts, here and in a fresh clone; 13 scoreboard
   lines; `latest.json` written.
2. All 67 node ids collected, none `fail`.
3. Every blocked check names a need with a false predicate (enforced
   by the plugin, shown by `test_unnamed_skip_and_a_skip_naming_a_met_need_are_failures`);
   all eight gaps name existing closers (`test_known_gaps_are_well_formed`).
4. Detectors both ways: `test_scan.py`, `test_wasm.py`, `test_pins.py`,
   `test_artifact_rules.py`, `test_scoreboard.py`.
5. `test_plugin.py`, 27 pytester cases end to end, including each
   attack from the build review; `test_scoreboard.py` adds the pure
   cases.
6. `test_guest.py`: WAT modules for dispatch, the door (no host, host,
   raising host), exits, the fuel cap, random and clock; Brett's build
   for stdout, isolation, a fuel cap of 10⁹ that traps at exactly 10⁹,
   and two `-I` runs within 0.01%.
7. `test_artifact_rules.py` (each rule, good and bad) and
   `test_checks_wiring.py` (the real v1.1 file in a subprocess against
   a good set, a set missing its snapshot, and a set with a third
   import).
8. Goldens written by `regen.py --online`; `regen.py --check` and
   `test_goldens_reproduce_under_the_pinned_oracle` reproduce them
   offline, both hash seeds agreeing.
9. `context/progress/accepted.json` and `history.jsonl` line 1.
10. `ruff check src tests` and `ruff format --check src tests` clean.

**Where the build departs from the text above, and why.**
- The random job is `tests/jobs/numpy_random.py`, not `random.py`:
  run natively, a script named `random.py` shadows the stdlib module
  of that name.
- `test_guest_sees_only_its_root` accepts `/..` being refused as well
  as listing `/`: wasmtime refuses it (EXECUTED: `PermissionError:
  [Errno 63] Operation not permitted: '/..'` on Brett's build).
- `--accept` judges the ratchet inside `accept()` and, once it
  succeeds, the run is re-judged against what was just accepted, so
  `--retire` and `--accept-growth` can turn a red run green. A
  self-test caught the first version refusing them.

**Review.** Specification review:
`../reviews/002-the-progress-harness-spec-2026-10-16.md` (18 findings,
then 8 on the revision; all dispositioned before build). Build review:
`../reviews/002-the-progress-harness-2026-10-16.md` (10 findings, then
4 on the fixes; verdict **lands** after the reviewer re-ran its attacks
on the final tree). The fixes it drove: gaps match an exact finding set
by digest; the judge covers every file under `tests/`, any
`conftest.py` and the pytest config files; pytest steered from outside
the judge turns the run red; only a missing product (artifact, runner,
wheel) makes a blocked pass red, so a fresh clone is green; absent
checks are found across all collected files and only they can be
retired; tarballs are checked against their pins.

**Residuals, accepted in the review.** A plugin written to replace the
judge's own functions inside the process is not detected (Decision 14:
review is the backstop). Because digests drop line numbers, a finding
removed from one line of a file and added on another line of the same
file leaves a gap's digest unchanged; any net new finding still changes
it. Windows was not executed; the three-systems check will be the
evidence. The baseline protects 14 passes (history lines 1 and 2).
