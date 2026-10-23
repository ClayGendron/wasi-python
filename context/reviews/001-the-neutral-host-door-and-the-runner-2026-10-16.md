# Review of 001 — The neutral host door and the runner

- **Date:** 2026-10-16
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read the constitution, `AGENTS.md`, `context/README.md`, the review template, specification 001 with its landing notes, 003's Decisions 5, 6, 9 and 10, and 002's Decisions 2 to 7, 13 and 14. I then read the change itself. I did not rely on the landing notes; each claim below is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** everything uncommitted on top of `8e3428a`:
  - `src/wasi_python/runner.py` (new, untracked);
  - `src/wasi_python/__init__.py`;
  - `README.md` ("Running it", "Next");
  - the judge edits in `tests/checks/conftest.py`, `tests/checks/test_v1_4_embedding.py`, `tests/test_api.py` and `tests/unit/test_plugin.py`;
  - the spec's own amendments and landing notes.

  `.idea/` is untracked and not part of the change.
- **Re-ran (EXECUTED, darwin-arm64, wasmtime-py 49.0.0):**
  - `uv run pytest -q -p no:cacheprovider` → `wasi_python v1: 82/86 pass · 2 gap · 2 blocked · 0 fail (unit suite 136/136)`; v1.4 `26/26`; `218 passed, 2 skipped, 2 xfailed`; **exit 0**. Ratchet line: `ratchet vs f2292dbaf4: lost 0 · absent 0 · unrun 0 · gained 8 · grew 0 · judge changed: tests/checks/conftest.py, tests/checks/test_v1_4_embedding.py, tests/test_api.py`.
  - The run is green, not red. A changed judge is *reported*; only `--accept` refuses it without `--accept-judge` (002 Decisions 6 and 7, READ). The scoreboard prints only the first three changed judge files (`scoreboard.py:378`, `[:3]`, READ). Comparing `build/progress/latest.json` with `context/progress/accepted.json` gives four (EXECUTED): the three above and `tests/unit/test_plugin.py`.
  - `uv run ruff check src tests` → `All checks passed!` (exit 0). `uv run ruff format --check src tests` → `36 files already formatted` (exit 0).
  - I did not run `--accept`.
  - My own probes of `wasi_python.run`, run through `uv run python` with `WASI_PYTHON_CACHE` and `WASI_PYTHON_ARTIFACTS` in my scratchpad.
    - Each probe used its own copy of the artifact set. The probes that damage the zip ran on a copy, never on `build/artifacts/`.
    - `build/artifacts/python-stdlib.zip` still hashes `adf440a3…` after the review (EXECUTED).
    - Scripts and logs are under the session scratchpad, `review-001/scripts/` and `review-001/*.log`.

## Acceptance criteria against evidence

1. *The three runner checks pass against `build/artifacts/`, and the run is accepted into `context/progress/`.* — **Partly met.**
   - The three checks pass (EXECUTED, above).
   - The run is not yet accepted. That is correct before review.
   - Its acceptance needs `--accept-judge` (READ, 002 Decision 7).
2. *`import wasi_python` works without wasmtime, and the five new checks pass.* — **Met as written, but two checks do not test what they say.**
   - EXECUTED: with `sys.modules['wasmtime'] = None`, the package imports and `run` is callable. Calling `run` then raises `ImportError`.
   - All five checks pass.
   - `test_runner_caches_the_compiled_module` never loads a `.cwasm` from disk (finding 5).
   - `test_runner_runs_the_plain_reactor` would pass if `snapshot=False` were ignored (finding 6).
3. *README's "Running it" shows the runner call and the three-step contract, and no longer mentions the spike's import.* — **Met.**
   - EXECUTED: the example, with `root` moved into my scratchpad, gives `(0, b'6\n')`.
   - READ: the three steps match 003 Decision 5 and 001 Decision 4.
   - READ: the spike's import and Brett Cannon's build are gone.
   - NOT RE-RUN: the `wasmtime run -W unknown-imports-default` sentence. This machine has no wasmtime CLI.
4. *ruff check, ruff format --check and pytest are green.* — **Met** (EXECUTED, above).

Against spec 001 Decision 3, behaviour by behaviour, on both binaries (EXECUTED unless marked):

- **argv.** `sys.argv` is `['-c', 'a']`.
- **stdin.** stdin bytes reach `sys.stdin`. A program given on stdin with no argv prints `42`.
- **env.** `env` is the whole environment: `{}` when it is not given.
- **Host round trips.** Three calls and an empty request work. An empty response comes back as `b''`. A 5 MiB response works. `bytearray` and `memoryview` responses work.
- **Host faults.** A host that raises answers −2. So does a host that returns `str` or `None`. The guest sees `OSError the host faulted while answering the door`, and `available()` is `False`.
- **No host.** The guest gets `ConnectionRefusedError`.
- **proc_exit.** `os._exit(7)` gives 7, and the stdout flushed before it is kept. `sys.exit(3)` gives 3.
- **Fuel.** `fuel=10**9` on a loop gives `"out of fuel"` with `fuel_used=1000000000`. `fuel=0` gives `"out of fuel"`.
- **Memory.** `memory_bytes=128 MiB` turns a 256 MiB `bytearray` into a `MemoryError`. Without the cap the same allocation succeeds. A cap below the module's initial memory reports `trapped='memory minimum size of 878 pages exceeds memory limits'` and exit `None`.
- **Deadline.** `deadline_s` traps as `"deadline"`. A quick program under `deadline_s=5` is not affected.
- **Threads.** Six threads at once, on different roots, mixing fuel, no fuel, snapshot and plain: each gets its own stdout and stderr.
- **Stale or corrupt `.cwasm`.**
  - A truncated `.cwasm` is recompiled and replaced.
  - A zero-filled one is recompiled and replaced.
  - A fuel `.cwasm` under the plain name is refused and replaced.
- **A root holding a different zip.** The zip is replaced by the artifact set's own, and the program runs.
- **Explicit `artifacts=`.** It is used, and the environment variable is not consulted.
- **`ArtifactsMissing`.** The message names `$WASI_PYTHON_ARTIFACTS`, both directories and `scripts/build.sh`.
- **A root on another filesystem.** I used a mounted 64 MB HFS+ disk image. The zip is copied (`nlink 1`) and the program runs. A guest write to the copy leaves the artifact untouched.

## Findings, most severe first

1. **The guest can rewrite the artifact set's stdlib zip** (`runner.py:174-187`, `_place_stdlib`, `os.link`).
   - The defect: on one filesystem, the runner hard-links the artifact zip into a root the guest can write.
   - So the guest's `/usr/local/lib/python314.zip` is the same inode as `build/artifacts/python-stdlib.zip`, or as the installed wheel's copy.
   - Failure (EXECUTED, on a copy of the set): one guest run writes the artifact zip itself, for every later run on every root.
     - `open('/usr/local/lib/python314.zip','r+b')` then a write at the end → exit 0. The artifact zip's SHA-256 went from `adf440a3…` to `736b072f…`.
     - `.write(b'XXXX')` at offset 0 → `3d388ad6…`.
   - Every later run, on every root, then reads the changed zip. A program that replaces a module's bytecode in the zip plants code in every later program of every user of that artifact set.
   - It also breaks the snapshot/zip pair of 003 Decision 9.
   - This crosses the wall the mission promises ("a sandbox it fully controls"): what one guest does reaches outside its root.
   - The risk is live today. `build/artifacts/python-stdlib.zip` has link count 25. Twenty-four links sit in the author's scratch roots (EXECUTED, `find -inum`).
   - Fix:
     - Never share the inode. Give each root a private copy: write it to a temporary name in the lib directory, then `os.replace` it into place. A copy-on-write clone where the filesystem has one also works.
     - Before reusing an existing file, check it, for example against `MANIFEST`'s `x-snapshot-zip` hash.
     - A separate read-only preopen for `/usr/local/lib` is probably not open to the snapshot: wasi-libc's preopen table is frozen in it (003; INFERRED).
     - Add a check that a guest write to its zip leaves the artifact's hash unchanged.
2. **The runner follows a symlink the guest planted, and writes outside the root** (`runner.py:180-187`).
   - The defect: the guest can make `/usr/local/lib/python314.zip` a relative symlink that points out of the root. wasmtime allows creating it (EXECUTED).
   - On the next run on that root, the runner follows it:
     - `dest.exists()` is `False` for the dangling link;
     - `os.link` fails with `FileExistsError`;
     - `shutil.copyfile` follows the link and creates the target on the host.
   - Failure (EXECUTED, two runs on one root, on a copy of the set): the guest chose both the bytes and the host path.
     - Run 1: truncate the zip and write `echo chosen by the guest\n` (finding 1). Unlink it. Symlink `../../../../../victim/dotfile`.
     - Run 2, any program: the host file `review-001/victim/dotfile`, outside the root, now holds `b'echo chosen by the guest\n'`.
   - So the guest picks a host path the user can write and its contents, for example a shell start-up file that does not exist yet.
   - An absolute symlink target was refused by wasmtime (EXECUTED); a relative one was not.
   - A symlinked `usr/local/lib` would also make `dest.unlink()` and the link or copy act outside the root (INFERRED).
   - Fix:
     - `lstat` the destination and remove any symlink without following it.
     - Create the file only with `O_EXCL|O_NOFOLLOW` (or a temporary name plus `os.replace`).
     - Check that `dest.parent.resolve()` is inside `root.resolve()`.
     - Add a check that plants the link and asserts nothing appears outside the root.
3. **The `.cwasm` cache is trusted by its file name, and its "only its user can write" rule is not enforced** (`runner.py:206-218`, `259-288`).
   - The defect: a `.cwasm` is native code, and spec 001 Decision 3 says the cache directory must be one only its user can write. Nothing enforces this.
   - Failure (EXECUTED):
     - Under `umask 002` the runner creates the cache directory `0775`.
     - A directory set to `0777` holding a `0666` `.cwasm` is loaded without complaint.
     - The plain reactor's `.cwasm` copied under the snapshot's name is loaded and run as the snapshot: `'numpy' in sys.modules` → `False`.
     - So a `cache_dir` or `$WASI_PYTHON_CACHE` on a shared path (`/tmp/…`) lets another local user run native code as this user.
   - Fix:
     - Create the directory `0o700`.
     - On POSIX, refuse to read or write a cache whose directory or file is not owned by the current user, or is writable by group or other. Compile in memory instead, and say so once.
     - Say in the README that the cache must be private.
4. **The runner and the judge find different artifact sets** (`__init__.py:47-59` against `tests/harness/paths.py:74-83`).
   - The defect: spec 001 Decision 3 says its order "is the harness's order (003 Decision 10), so the judge and the runner find the same set". It is not.
     - The runner looks at the environment variable, then the wheel's `artifacts/`, then `build/artifacts/`.
     - The harness looks at the environment variable, then `build/artifacts/`, then the wheel.
     - An empty `$WASI_PYTHON_ARTIFACTS` is "unset" to the runner. To the harness it is the current directory.
   - Failure (EXECUTED): with a `MANIFEST` in the wheel directory, the runner resolves the wheel copy and the harness resolves `build/artifacts/`.
   - That state is planned. `pyproject.toml` says the release workflow drops the artifacts into `src/wasi_python/artifacts/` before `uv build`. Then the runner checks judge one set and every other check judges another.
   - In an installed wheel, `CHECKOUT_ARTIFACT_DIR` is `<prefix>/lib/python3.X/build/artifacts`. It is searched and named in the error message (INFERRED from `parents[2]`).
   - Fix:
     - Use one order: 003 Decision 10's, or amend both specs.
     - Give the empty variable one meaning in both places.
     - Use the checkout directory only when `<repo>/pyproject.toml` is there.
     - Add a unit test that the two resolvers agree.
5. **`test_runner_caches_the_compiled_module` does not test the disk cache** (`tests/checks/test_v1_4_embedding.py:190`).
   - The defect: the module is cached in the process (`_modules`), keyed without the cache directory.
     - Both of the check's calls are served from memory.
     - The first call only serializes the in-memory module to the new directory.
     - The second call never reads the file.
     - The docstring's "the next loads it" and spec 001's "a second call loads the `.cwasm`" are therefore not checked.
   - Failure (EXECUTED): I replayed the check's steps with counters on `Module.from_file` and `Module.deserialize_file`.
     - After an earlier runner call, as in a judge session, the check's two calls made 0 compiles and 0 disk loads.
     - With `deserialize_file` made to raise, in a fresh process, every assertion of the check still held.
   - So a runner whose disk cache never loads passes it.
   - Fix: make the second call in a subprocess (or clear `_modules`), and assert that it compiled nothing and loaded one `.cwasm`. Both are counts, not times.
6. **`test_runner_runs_the_plain_reactor` cannot tell the plain reactor from the snapshot** (`tests/checks/test_v1_4_embedding.py:156`).
   - Failure (EXECUTED): the check's program prints `['-c', 'a']` on both binaries. A runner that ignored `snapshot=False` would pass.
   - Fix: also print something only the plain reactor gives. In the snapshot `'numpy' in sys.modules` is `True`, and in the plain reactor `False` (EXECUTED).
7. **The door breaks when guest addresses pass 2 GiB** (`runner.py:155-168`).
   - The defect: wasmtime-py passes `i32` values signed. A pointer at or above 2³¹ arrives negative. `Memory.read` and `Memory.write` treat a negative start as a Python slice from the end (READ, `wasmtime/_memory.py`).
   - So the request is read from the wrong place, and the response is written at the wrong guest address.
   - Then `struct.pack("<I", p)` raises `struct.error`. That escapes `run()` as a Python exception, not a `Completed`.
   - Failure (EXECUTED): the guest holds about 2.25 GiB of `bytearray`s, then calls `_host.call(bytes(8 << 20))` with an echoing host → `struct.error: 'I' format requires 0 <= number <= 4294967295` from `run()`.
   - This is reachable by a data workload on a 4 GiB wasm32 memory.
   - Fix:
     - Mask `ptr`, `length`, both out-pointers and `host_alloc`'s result with `& 0xFFFFFFFF`.
     - Bounds-check the request.
     - Answer −2 on any failure after the host returns.
   - The judge's driver has the same pattern (`tests/harness/guest.py:175-183`, READ). It is out of this change's scope but should get the same fix.
8. **Concurrent calls on one root fail** (`runner.py:180-187`).
   - Failure (EXECUTED): four threads with the same `root` → three raised from `run()`. They got `FileExistsError`, then `shutil.SameFileError` from the fallback copy. One returned.
   - Fix: the temporary-name-plus-`os.replace` placement of finding 1 also removes this race.
9. **Deadlines overshoot by about 40%** (`runner.py:297-333`).
   - The ticker sleeps `TICK_S` after each tick, so overhead accumulates.
   - Benchmark fact (EXECUTED, wall clock, not a test):
     - `deadline_s=0.3` traps after 0.41 to 0.48 s;
     - `1.0` after 1.40 s;
     - `2.0` after 2.79 to 2.82 s.
   - It is one ticker thread per engine (up to two), not "one per process" as spec 001 says.
   - Fix: tick against a monotonic schedule, or state the overshoot in the README and the spec.
10. **`fuel_used` after a deadline trap is not the instructions spent** (`runner.py:122`).
    - EXECUTED: `while True: pass` under `fuel=10**13, deadline_s=0.3` reports `fuel_used` 2.6M to 2.8M.
    - `-c pass` alone costs 77M to 118M in my runs. A loop that ran past start-up cannot have spent less.
    - INFERRED cause: wasmtime does not write its fuel counter back on an epoch trap in a loop with no calls.
    - Fix: report `None` when `trapped == "deadline"`, or document it.
11. **A root on another filesystem gets a fresh 10 MB copy on every call** (`runner.py:181`).
    - EXECUTED: the inode changed 22 → 23 → 24 over three calls.
    - It is correct, and safe (the copy protects the artifact), but it costs a copy per call.
    - Folding this into finding 1's fix (a verified private copy) settles both.
12. **Small things.**
    - README "Next" says spec 001 has landed. It has not.
    - README's list of `run` arguments leaves out `artifacts`.
    - README's "about 25 ms" has no command beside it (constitution §4.10). The figure is in the landing notes.
    - `run()` without the `run` extra raises a bare `ImportError` that does not name `wasi-python[run]`.
    - A `memory_bytes` below the initial memory reports `trapped` and `exit_code=None`. The spec and the README do not say so.
    - The scoreboard lists at most three changed judge files, with no "+N more". This is a pre-existing harness trait, outside this change. It hid `tests/unit/test_plugin.py` from the ratchet line that AGENTS.md says a review reads.

## The judge edits

- **`tests/checks/conftest.py`.** A session-wide autouse fixture points `$WASI_PYTHON_CACHE` at `build/cwasm-cache/` and restores it after.
  - It does not weaken any check (READ).
  - It stays set for the unit tests that run after the checks. That is harmless.
  - `build/` is git-ignored, and `.cwasm` is ignored by `.gitignore:13` (EXECUTED, `git check-ignore`).
- **`tests/unit/test_plugin.py`.** The inner sessions now patch `needs.VOCABULARY["runner"]` to an unmet `Need` named `runner` through `monkeypatch`.
  - The plugin re-checks the need in `pytest_runtest_makereport` for the call phase, before fixture teardown undoes the patch (`plugin.py:198-211`, READ).
  - So the inner check is still classified `blocked`.
  - The name is still `runner`, a protected need. So `test_a_blocked_pass_is_red_unless_partial` still proves that a protected-need block is red without `--partial`.
  - The two cases test what they tested before, independent of the repository's state. This is not a weakening and not a false green.
  - It does show that a check can make itself `blocked` by patching the vocabulary. That was always so; 002 Decision 14 leaves such tampering to review.
- **`tests/test_api.py`.** The old test asserted `ArtifactsMissing` with "source checkout", which is false now that a checkout finds `build/artifacts/`. The new tests patch the three places and check the order and the message.
  - It is hermetic and sound as a unit test (EXECUTED, it passes).
  - But it locks in the wheel-before-checkout order of finding 4.
  - It no longer checks that an installed wheel's three files exist. `test_v1_1_artifact_set` covers the set, so nothing is lost.
- **The five new v1.4 checks.**
  - Sound:
    - `test_package_imports_without_wasmtime` (a real subprocess, with wasmtime made unimportable);
    - `test_runner_reports_a_host_fault`;
    - `test_runner_caps_memory`. It does discriminate: the same allocation succeeds without the cap (EXECUTED).
  - Not sound: `test_runner_caches_the_compiled_module` (finding 5) and `test_runner_runs_the_plain_reactor` (finding 6). These two report `pass` on behaviour they do not observe. They are false greens in the narrow sense. No existing check is weakened.

## Constitution checks

- **§4.4 (two ways out).** Holds (READ). The runner defines only WASI and `host::call`, and adds no import to the guest.
  - But findings 1 and 2 let a guest reach host files outside its preopened root through the runner's own file handling. That breaks the wall the mission states (§1), though not the import rule.
- **§4.5 (embedder-neutral).** Holds.
  - EXECUTED: every name in `context/embedders.txt` grepped over `src/`, the changed tests and `README.md` → no hit.
  - `rules` is 14/14.
  - The README's earlier "for vfs" sentence is gone.
- **§4.6 (no published `.cwasm`; nothing large in git).** Holds.
  - The cache lives outside the artifact directory. `build/` and `*.cwasm` are ignored.
  - `cwasm_errors` still guards the artifact directory (READ).
  - The cache's trust model is finding 3.
- **§4.9 (tests count, never time).** Holds (READ).
  - The new checks read no clock.
  - No test uses `deadline_s`.
  - The runner's `time.sleep` is runtime code, not a test.
  - The landing notes' timings are labelled benchmark facts.
- **§4.10 (claims carry evidence).** Mostly holds.
  - The README's "about 25 ms" has no command beside it (finding 12).
  - The landing notes' claim that the runner and judge share an order is wrong (finding 4).
- **§4.13 (tooling).** ruff and pytest are green. No dependency was added.
- **Package without wasmtime.** Holds (EXECUTED).
- **Native code from a cache directory.** See finding 3. The spec states the precondition, but the code does not enforce it.
- **§7 never-do list.** Nothing tripped. No patch, no new import, no fetch, no commit.

## Disposition (filled in by the author, then confirmed by the reviewer)

The author answered every finding on 2026-10-16. The figures are in spec 001's rewritten landing notes. `uv run pytest -q -p no:cacheprovider` → `87/91 pass · 2 gap · 2 blocked · 0 fail (unit suite 137/137)`, `224 passed, 2 skipped, 2 xfailed`; ruff is clean (EXECUTED).

1. **Fixed.** The zip is always a copy, never a link: a fresh copy with a unique name in the same directory, renamed over the old one. A file that is not byte for byte the artifact's zip is replaced before the next call. Check: `test_runner_keeps_the_artifact_zip_out_of_the_guests_reach`. It writes into the zip from the guest, then checks that the artifact's hash is unchanged and that the next call on that root gets a correct zip. On the first build's code the same scenario changed the artifact zip's hash (EXECUTED, on a scratch copy). The 29 hard links earlier scratch runs had left to `build/artifacts/python-stdlib.zip` are removed, and its hash is still `adf440a3…`.
2. **Fixed.** `_real_dir` walks `usr/local/lib` with `lstat`. A link or file in place of a directory is removed and never followed, and `os.replace` replaces a link at the zip's path itself. The hash check opens with `O_NOFOLLOW`. Check: `test_runner_never_follows_a_link_a_guest_left`, with a link at the zip and a link at `/usr/local/lib`. On the first build's code the zip case wrote `outside/target` (EXECUTED).
3. **Fixed.** On POSIX the cache directory is made `0700` and files are written `0600`. A directory or file not owned by the user, or writable by group or other, is neither read nor written: the runner warns and compiles in memory. `cache_dir=False` keeps modules in memory only. The README says the cache must be private. Check: `test_runner_refuses_a_cache_others_can_write`, in a fresh process. Swapping in the plain reactor's `.cwasm` under the snapshot's name needs write access to a private cache, and that is outside the threat the cache must stop; spec 001 says so.
4. **Fixed.** The runner now uses the harness's order:
   1. `$WASI_PYTHON_ARTIFACTS`, when set and not empty;
   2. a checkout's `build/artifacts/`, detected by `pyproject.toml`;
   3. the wheel's copy.

   Both now read an empty variable as unset (a judge edit to `tests/harness/paths.py`). `tests/test_api.py` checks this order, the empty-variable case included.
5. **Fixed.** The check runs two fresh processes and reads `wasi_python.runner.stats()`. The first must show compiled 1, written 1, loaded 0; the second compiled 0, loaded 1, written 0.
6. **Fixed.** The check prints `'numpy' in sys.modules`: `False` on the plain reactor, `True` on the snapshot, both through the runner.
7. **Fixed in both doors.** Addresses, lengths and `host_alloc`'s result are masked to 32 bits in `runner.py` and in the judge's driver (`tests/harness/guest.py`, a judge edit). There is no check: the artifacts never reach 2 GiB in a test, and building such a guest would cost more than the fix. Answered in writing.
8. **Fixed.** Placing the zip uses unique temporary names, an atomic rename, and directory creation that tolerates a concurrent call. Check: `test_runner_serves_concurrent_calls_on_one_root` (four threads on one root). Spec 001 says a root may be shared, but each untrusted program should get its own.
9. **Fixed.** One ticker thread per process advances every engine's epoch once per 10 ms of elapsed wall time and catches up after a long sleep. Measured: 0.3, 1 and 2 s deadlines ended at 0.307, 1.007 and 2.009 s (EXECUTED; a benchmark fact, not a check).
10. **Fixed by reporting `None`.** wasmtime does not update its fuel count on an epoch interrupt. The reported count was about 2.7 million for both 0.3 s and 0.6 s deadlines (EXECUTED). Spec 001 says `fuel_used` is `None` after a deadline trap.
11. **Fixed by 1.** The copy is made once per root. Later calls recognise it by device, inode, size, modification time and change time (POSIX), and on other systems by its hash. There is no per-call copy any more.
12. **Small things:**
    - **README "Next" saying 001 has landed: answered.** The README ships in the landing commit, so the sentence is true when it is committed. It is not committed before this review is confirmed.
    - **`artifacts` in the README's argument list: added**, with `cache_dir=False`.
    - **"about 25 ms": rewritten.** It now gives the three measured figures and points to the landing notes, where the command and machine are.
    - **`ImportError` without the extra: it now names `pip install "wasi-python[run]"`.**
    - **`memory_bytes` below the initial memory: spec 001 now says it fails instantiation**, with `trapped` set to wasmtime's first line.
    - **Scoreboard truncation: fixed.** The ratchet line ends with "and N more", and the `--accept` refusal with "and more". A unit test covers it (`tests/unit/test_scoreboard.py`).

## Verdict

Does not land yet. Most of the runner works as spec 001 says. But findings 1 and 2 let one guest program change the shared artifact set and write files the guest chooses outside its root. Finding 3 lets a writable cache run foreign native code. Two of the five new checks are false greens. Fix findings 1 to 6, each with a check, before acceptance.

One line: the runner works, but it shares the artifact zip with the guest and follows the guest's symlinks, and that must be fixed before it lands.

## Reviewer's confirmation

- **Date:** 2026-10-16
- **Reviewer:** the same fresh agent as above. I read the author's dispositions, then the new diff: `runner.py`, `__init__.py`, `tests/harness/{paths,guest,scoreboard}.py`, `tests/test_api.py`, `tests/unit/test_scoreboard.py`, `tests/checks/test_v1_4_embedding.py`, README "Running it" and spec 001's root and cache text (READ).
- **Re-ran (EXECUTED):**
  - `uv run pytest -q -p no:cacheprovider` → `wasi_python v1: 87/91 pass · 2 gap · 2 blocked · 0 fail (unit suite 137/137)`; v1.4 `31/31`; `224 passed, 2 skipped, 2 xfailed`; exit 0. Ratchet: `lost 0 · absent 0 · unrun 0 · gained 13 · grew 0 · judge changed: tests/checks/conftest.py, tests/checks/test_v1_4_embedding.py, tests/harness/guest.py and 5 more`.
  - `uv run ruff check src tests` → `All checks passed!` (exit 0). `uv run ruff format --check src tests` → `36 files already formatted` (exit 0).
  - `build/artifacts/python-stdlib.zip` has link count 1 and still hashes `adf440a3…`.
- **My attacks:** they ran on a fresh copy of the artifact set (`review-001/art-c2`), through `uv run python`. The script is `review-001/scripts/probe_confirm.py`; its log is `review-001/probe_confirm.log`.

### Each finding

1. **Confirmed** for the artifact set (EXECUTED).
   - Three guest rewrites of `/usr/local/lib/python314.zip` left the artifact zip's hash unchanged and its link count at 1: an append, a clobbered header, and a truncation followed by a payload.
   - The next call on each root ran `import json, csv, pandas` with a correct zip.
   - A rewrite followed by `os.utime` to restore the old times was also repaired, because the change time still moved.
   - The new check `test_runner_keeps_the_artifact_zip_out_of_the_guests_reach` tests this.
   - One gap remains, on file systems with coarse times: see new finding 13.
2. **Confirmed** (EXECUTED). I planted a link and then ran a second call, with a file named `python314.zip` and a `usr/` directory waiting outside. Nothing appeared, changed or vanished outside the root in any of these cases, and the second call ran each time:
   - a dangling link at the zip;
   - a link at the zip to an existing outside file;
   - a link at `/usr/local/lib`;
   - a link at `/usr/local`;
   - a link at `/usr`;
   - the full chain from my review (a payload in the zip, then a link).
3. **Confirmed** (EXECUTED).
   - A planted `.cwasm` was neither loaded nor written over in all four unsafe layouts:
     - directory `0777`;
     - directory `0770`;
     - file `0666` in a `0700` directory;
     - cache directory reached through a symlink.
   - In each layout the plain reactor's `.cwasm`, planted under the snapshot's name, was not used: `'numpy' in sys.modules` was `True`, and `stats()` showed `loaded 0, compiled 1`. A warning was issued each time.
   - Under `umask 002` the runner made the directory `0700` and the file `0600`. `cache_dir=False` wrote nothing.
   - I accept the author's answer on a swapped file inside a private cache: anyone who can write there is already this user.
4. **Confirmed** (READ, and EXECUTED through the full run).
   - Runner: env (when set and not empty), then `build/artifacts/` (only in a checkout with `pyproject.toml`), then the wheel.
   - Harness: env (when set and not empty), then `build/artifacts/`, then the wheel.
   - They agree. `tests/test_api.py` checks the order, the empty variable included.
5. **Confirmed** (READ).
   - The check runs two fresh processes. It asserts `compiled 1, loaded 0, written 1`, then `compiled 0, loaded 1, written 0`.
   - The in-process cache can no longer mask the disk path. A runner whose disk load were broken would fail the second assertion.
6. **Confirmed** (READ; EXECUTED in the full run).
   - The check asserts `False` on the plain reactor and `True` on the snapshot for `'numpy' in sys.modules`.
7. **Confirmed** (EXECUTED).
   - Setup: about 2.25 GiB held by the guest, then `_host.call(b'hi' + bytes(8 << 20))`.
   - The host saw `(8388610, b'hi')`. The guest got its 4 MiB response back (`ok 4194307 b'hi-r'`), and the request's address was above 2³¹. Before the fix this raised `struct.error` from `run()`.
   - I accept "no check" in writing: such a guest is costly in a judge run.
8. **Confirmed** (EXECUTED).
   - Eight threads ran on one root, mixing the two binaries and fuel with no fuel. All returned exit 0 with their own stdout.
   - Before the fix, three of four threads raised.
   - The new check `test_runner_serves_concurrent_calls_on_one_root` covers four threads.
9. **Confirmed** (EXECUTED, wall clock, a benchmark fact). Deadlines now end close to their nominal value, with or without fuel:
   - 0.3 s → 0.31 to 0.38 s;
   - 1.0 s → 1.01 s;
   - 2.0 s → 2.01 s.

   There is now a single ticker thread.
10. **Confirmed** (EXECUTED). `fuel_used` is `None` after every deadline trap in my runs. It is still exact for `"out of fuel"`.
11. **Confirmed on APFS. Partly confirmed on a coarse-time file system** (EXECUTED, on a mounted HFS+ disk image).
    - The copy is now made once: the inode stayed 31 across three calls.
    - But see new finding 13.
12. **Confirmed.**
    - The `ImportError` now names `pip install "wasi-python[run]"` (EXECUTED).
    - The README lists `artifacts` and `cache_dir=False`, and says the cache must be private. Its timings point to the landing notes (READ).
    - The README example still prints `(0, b'6\n')` (EXECUTED, with `root` in my scratchpad).
    - The scoreboard now says "and 5 more", and a unit test covers it (EXECUTED, READ).
    - I accept the answer on "Next": the line is true at the landing commit.

### New findings from the confirmation (none blocks the landing)

13. **On a file system with one-second timestamps, a guest's rewrite of its own zip copy is not repaired** (`runner.py:204-209`, the `_stamp` shortcut).
    - Failure (EXECUTED, HFS+ disk image):
      1. a call places the copy;
      2. a guest writes 16 bytes into it within the same second;
      3. `st_ctime_ns` stays `1792187867000000000`;
      4. the next call in the same process matches the stamp and keeps the changed file.
    - With 1.5 s between the calls it is repaired. On APFS both cases are repaired.
    - The artifact set itself is never touched. Only that root's later calls see the change, which the spec already treats as the embedder's matter ("each untrusted program its own root").
    - But spec 001's sentence "replacing any file that is not byte for byte the artifact's zip" is not true there.
    - Fix: trust the stamp only when its change time has a sub-second part, or when it is more than the file system's granularity older than the call that placed it. Otherwise hash. Or qualify the spec's sentence.
14. **A guest that turns its zip path into a non-empty directory makes every later call on that root raise** (`runner.py:210-216`).
    - Failure (EXECUTED): `os.remove(zip); os.mkdir(zip); open(zip + '/x', 'w')`. After that, each `run()` on that root raises `IsADirectoryError` from `os.replace` instead of returning a `Completed`.
    - It only denies service on the guest's own root.
    - Fix: if `lstat` shows a directory, move it aside or remove it with `shutil.rmtree`, which does not follow links, before the rename.
15. **Concurrent calls on a shared root leave a check-then-use window** (`_real_dir`, then `mkstemp(dir=lib)` and `os.replace`; INFERRED, not raced).
    - While call A's guest runs, it could swap `usr/local/lib` for a link after call B's `_real_dir` has checked it. B would then place its copy, and replace a `python314.zip`, in a directory outside the root.
    - Spec 001 allows shared roots and tells embedders to give untrusted programs their own. The risk on a shared root is therefore a host write, not only "what another sees", and the spec's sentence should say so.
    - A full fix walks the path with directory descriptors (`O_NOFOLLOW`, `dir_fd=`).

### Confirmation verdict

**Confirmed: lands.** Findings 1 to 12 are fixed or answered, and the fixes are checked where a check is practical. The run is green with `gained 13` and nothing lost. Accept it with `--accept-judge`, naming the eight changed judge files.

Findings 13 to 15 are low. They touch only a root the embedder has already been told not to share between untrusted programs. Fix them, or answer them in writing in spec 001 as a follow-up; they do not block the landing.

One line: the guest can no longer reach the artifact set or write outside its root, and the cache refuses native code that others could plant. Lands, with three low follow-ups.

## Author's note after the confirmation

The confirmation's three new low findings were closed before acceptance. These changes come after the confirmation and are recorded here:

13. **Fixed.** A placed copy is recognised by its stamp only when its change time has a sub-second part. On a filesystem with whole-second times, the file is hashed on every call.
14. **Fixed.** A directory the guest leaves at the zip's path is removed with `shutil.rmtree`, which does not follow links inside it, before the copy is put in place. New check: `test_runner_replaces_a_directory_left_in_the_zips_place`.
15. **Answered in the spec.** Decision 3 now says that a guest running at the same time on a shared root could make the runner write outside the root. An embedder therefore gives each untrusted program its own root, or runs calls on a shared root one at a time. A handle-based walk that refuses links is left for when shared roots are a supported use.
