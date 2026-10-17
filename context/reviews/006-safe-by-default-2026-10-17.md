# Review of 006 — Safe by default: the hostile guest, judged (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5), not the author. I read `AGENTS.md`, the
  constitution, `context/README.md`, `context/reviews/README.md`, the 005 build review (for its
  format), specification 006 with its landing notes, and its pre-build review with the
  dispositions and the confirmation (`006-safe-by-default-spec-2026-10-17.md`). Then I read the
  diff. I did not rely on the landing notes. Each claim is labelled EXECUTED, READ or INFERRED.
- **Reviewed:** commit `46cbc2f` (13 files), plus the move of `tests/unit/wat.py` to
  `tests/harness/wat.py`, which landed one commit earlier in `e51b438`. The artifacts in
  `build/artifacts/`. The commits after `46cbc2f` on `main` (`3ed454e`, `dbef7f2`) touch none of
  006's files (`git diff 46cbc2f HEAD --stat`) and are not part of this review.
- **Re-ran (EXECUTED, darwin-arm64, host Python 3.14.2, wasmtime-py 49.0.0).** Probes and outputs
  are under `…/scratchpad/rev006b/` (`probes/`, `mutations.txt`, `metric-deltas.txt`,
  `variants.txt`).
  - `uv run pytest -m "not slow"` → `108/116 pass · 1 gap · 2 blocked · 1 fail`;
    `1 failed, 267 passed, 2 skipped, 4 deselected, 1 xfailed`; ratchet `lost 1 · gained 18 ·
    grew 16 · judge changed`; **exit 1**. The one failure is not from this diff (finding 5).
  - `uv run pytest tests/checks/test_v1_2_hostile_guest.py` → `18 passed`.
  - The same file with `WASI_PYTHON_ARTIFACTS` on the 0.1.0a1 set → `4 failed, 14 passed`. The
    failures are 1.2 on both binaries and 1.11 in both orders. These are the checks that judge
    the binaries. The runner checks pass there because the runner is the new one.
  - Runner mutations on scratch copies of `src/wasi_python/` (through `PYTHONPATH`), each run
    against the new check file. The table is below.
  - `uv run ruff check src tests` → all passed. `uv run ruff format --check src tests` → 38
    files already formatted.
  - `shasum -a 256 -c SHA256SUMS` in `build/artifacts/` → every line OK. The reactor is
    `4e2b2470…` (29,802,408 bytes), the snapshot `c6a791d3…` (63,492,577 bytes) and the zip
    `e95b35de…`, as the notes say. `MANIFEST`'s recipe hashes for `reactor_main.c` and
    `reactor_bootstrap.py` match the committed files.
  - The author's `var006/measure.py` on the build and on both variants. It reproduces the landing
    notes' growth table to the instruction (`variants.txt`).
  - I did not run `scripts/build.sh`. I did not touch `build/artifacts/`, and I did not edit a
    tracked file, commit, push or tag. My pytest runs rewrote `build/progress/latest.json`, which
    is untracked build state.

## Acceptance criteria against evidence

1. *Guards of a change were seen failing first; guards of existing behaviour passed first.*
   **Met, as far as I can check.**
   - READ: the landing notes give a first-run table, check by check.
   - EXECUTED: on the 0.1.0a1 binaries, the binary checks fail as they should.
   - EXECUTED: each runner mutation below makes its check fail.
   - I cannot re-run the author's first run on the 005 runner.
2. *Steps 60 to 90 rebuild twice to the same bytes.* **Not verified by me** (I was asked not to
   build). EXECUTED: the artifacts match the hashes the notes give, and `MANIFEST` matches the
   committed recipes.
3. *`uv run pytest` green; `--accept-judge`; no lost pass; every grown metric has its cause.*
   **Not met yet.**
   - The run is red from a prior-art clone that is not part of this diff (finding 5).
   - One grown metric has no cause in the notes, and the notes misstate it (finding 4).
   - The other 15 grown metrics match the notes' causes.
4. *README "Safety" states the policy, each default and each unprotected channel; the CHANGELOG
   states the changes.* **Not met.**
   - The CHANGELOG is accurate.
   - The README says something is "enforced, and judged" when it is false (finding 2).
   - The README leaves out two unprotected channels (findings 3 and 6).

## Findings, most severe first

1. **After a trap, the call's `Store` stays alive until Python's cycle collector runs. That
   includes up to 1 GiB of guest memory, the guest's open host files and the private root's
   handle. So the memory default does not protect the host, and the private root is removed
   while it is still open** (`src/wasi_python/runner.py`, `_call` and `run`'s `finally`). High.
   - **Memory (EXECUTED, `probes/p3c_memory.py`, `p3d_memory_gc_on.py`).**
     - Four calls on the plain reactor each touch 400 MiB and then end by deadline.
     - With the collector **enabled**, host RSS goes 23 → 492 → 896 → 1301 → 1706 MB.
     - After `gc.collect()` it drops to 90 MB.
     - So each trapped call keeps its guest's memory after `run()` returns. A host whose guests
       hit the default deadline, which is the safety net this specification adds, gains up to
       1 GiB per such call until a collection happens to run. That defeats "cannot exhaust the
       host's memory through the guest" (the Intent).
   - **The private root (EXECUTED, `probes/p3_release.py`, `p3b_release_gc.py`).**
     - At the moment `shutil.rmtree` runs on a private root, `lsof` shows this process still
       holding the root directory and the guest's open file. This happens after a deadline trap,
       and after a trap raised inside the door.
     - After a normal exit, a `sys.exit`, or a host that raises, nothing is held.
     - A `gc.collect()` before the removal releases everything.
     - Decision 2 says the directory is removed "after the `Store` that holds its preopen is
       released". On the trap path it is not.
     - On POSIX the removal still succeeds.
     - On Windows (INFERRED, not run), an open handle blocks the removal, and
       `ignore_errors=True` hides the failure. So every trapped rootless call would leave its
       private root behind in `%TEMP%`: an 11 MB zip copy plus whatever the guest wrote.
   - **Cause (READ).** wasmtime-py's `enter_wasm` (`_func.py:231-241`) is a generator context
     manager that raises the trap. The trap's traceback and the frames that hold `store` form a
     reference cycle, so reference counting never frees the `Store`.
   - **Fix, verified (EXECUTED on a scratch copy).**
     - Call `store.close()` (wasmtime-py's `Managed.close`) in a `finally` in `_call`, after
       `fuel_used` is read.
     - With that one line, RSS stays at 89–90 MB across the four trapped calls.
     - `lsof` then shows nothing held at removal in all five cases.
   - **Add a check that counts.** A guest opens a file and ends by deadline. Assert that this
     process's open-descriptor count is back where it started after `run()` returns. That counts
     descriptors and never times anything.

2. **Code planted in a reused root still runs in a later call, through pdb's `.pdbrc`, on both
   binaries.** The `HOME=/tmp` that this change adds opens one route, and the current directory
   `/` was already a route (`runner.py` `BASE_ENV`; `README.md` "Safety"; the spec's policy
   sentence). High.
   - **Run 1 (EXECUTED, `probes/p1_pdbrc.py`, `p1b_pdbrc_nostdin.py`, plain and snapshot).** It
     writes `/tmp/.pdbrc` holding one Python line that creates a marker file.
   - **Run 2 runs that line** when the program on the same root does any of these:
     - calls `breakpoint()`, with or without stdin;
     - calls `pdb.post_mortem()`;
     - is run as `-m pdb /s.py`.
     The marker file appears every time.
   - **The older route.** With `env={"HOME": "/nonexistent"}`, a planted `/.pdbrc` in the
     current directory runs instead. That route existed before this change. `HOME=/tmp` adds a
     second one.
   - **Why the checks miss it.** Check 1.2 plants only import-path routes.
   - **What the README says.** It lists "modules, `.pth` files or a `pyvenv.cfg` … never run"
     under "Enforced, and judged". The policy sentence says "never". AI-written code does call
     `breakpoint()` and `pdb`.
   - **Other stdlib code that runs a file from HOME or the current directory (READ).** I grepped
     3.15's `Lib/` for `expanduser(` and rc-file names, outside tests, idlelib and tkinter. Only
     `pdb` executes what it reads. `netrc`, `mimetypes`, `trace`, `webbrowser`, `mailbox` and
     `sysconfig` read or name paths, but they run nothing.
   - **Fix: the author's choice, decided in writing.**
     - Either the reactor's bootstrap (a recipe, not a stdlib patch) stops `pdb` reading rc
       files.
     - Or the policy and the README name the exception: "a program that starts pdb reads
       `.pdbrc` from `HOME` and `/`".
     - Either way, add check 1.2's sixth route: plant both rc files, then `breakpoint()`. The
       check guards the fix or names the gap.

3. **Host file descriptors are not bounded, and the README does not list them.** Medium.
   - **The probe (EXECUTED, `probes/p2_fds.py`).** The host's `RLIMIT_NOFILE` was lowered to
     4096.
     - A rootless call with every default held **4088 open files**.
     - Then it called the door. The host function's own `os.open(os.devnull)` failed with
       `EMFILE`.
     - After the call, the descriptors were released.
   - **What it means.** For up to the deadline (60 s by default), the embedding process cannot
     open files. That includes concurrent calls, whose zip copy and stdin file need descriptors.
     Finding 1 makes it longer: after a trap the descriptors stay open until a collection runs.
   - **No limit applies (READ).** wasmtime's descriptor table allows 1,000,000 entries by default
     (`wasmtime-v49 crates/wasmtime/src/runtime/component/resource_table.rs:73`), and
     wasmtime-py does not expose that setting. This machine's own soft limit is 1,048,576.
     INFERRED: a guest could press on the system-wide file table there. I did not try.
   - **Fix.**
     - Add "host file descriptors, for the length of a call" to "Not protected".
     - Write a placeholder memo naming how a cap could be enforced (§5.2), as the spec does for
       disk.

4. **The landing notes misstate one grown metric and give it no cause** (spec 006, landing
   notes, "Growth"). Medium-low.
   - **What grew (EXECUTED, `metric-deltas.txt`, from `build/progress/latest.json` against
     `context/progress/accepted.json`).** `test_numpy_and_pandas_are_builtin_at_manifest_versions
     [plain]` went from 4,995,332,324 to 4,996,044,326. That is **+0.014%**, past the 0.01%
     tolerance. It is one of the 16 grown metrics.
   - **What the notes say.** "The plain reactor's −0.08% to −0.18%". That holds only for the
     `-c pass`-shaped runs. The plain `import numpy, pandas` grew.
   - **The rest checks out (EXECUTED).** The snapshot's runs are +0.03% to +0.09%. The binaries
     grew by 542 and 8,221 bytes. `measure.py` reproduces the variant table exactly. The growth
     figures in the table come from the author's variant builds, which I re-measured but did not
     rebuild (INFERRED that each variant differs only as named).
   - **Fix.** Correct the sentence and give the plain import's growth a cause. A likely candidate
     is the `site` helpers' 4.06M against what `site.main()` used to cost, but that is not
     measured.

5. **The scoreboard is red for a reason outside the diff** (`context/prior_art/wasmtime-v49/`).
   Medium-low, a blocker for criterion 3.
   - `test_every_prior_art_clone_has_its_licence_recorded` fails with "wasmtime-v49: no row with
     a licence" (EXECUTED).
   - The clone's directory was made at 00:44, three minutes after `46cbc2f`. It is ignored by
     git.
   - Before `--accept`, someone must record its licence in `context/prior_art/README.md` or
     remove it. The landing also needs `--accept-judge` and `--accept-growth` for the 16 grown
     metrics. Their causes are finding 4 and the notes.

6. **The README's "Not protected" list and the policy sentence miss three things.** Low.
   - **Files the caller names to run.** A script, a directory with `__main__.py`, or
     `-m unittest` discovery runs code from the root by design. The pre-build confirmation
     suggested adding "unless the caller names that file to run" (point 5). Neither the spec nor
     the README took it up.
   - **Concurrent calls on one root are not isolated from each other.** A guest can hard-link the
     zip (EXECUTED: `os.link('/usr/local/lib/python315.zip', '/hard.zip')` succeeds). A call
     still running can then rewrite the zip that a later, concurrent call on the same root has
     already had verified and is importing from (INFERRED). Sequential calls are safe, because
     the zip is re-verified before each one.
   - **Cost.** A rootless call copies 11 MB into the host's temp directory each time. The spec
     states this as a cost, but the README does not.

7. **Check 1.5 asserts less than the spec says** (`tests/checks/test_v1_2_hostile_guest.py`,
   `test_a_call_without_a_root_shares_nothing`). Low.
   - The spec says the two calls "see different roots holding only the runtime's own files".
   - The check prints the first root's listing but never compares it. Assert that it equals
     `['left-behind', 'tmp', 'usr']`.
   - No check covers cleanup after a trap (finding 1).

8. **The judge's door has only part of the runner's bounds** (`tests/harness/guest.py`). Low.
   - It bounds the request. It does not bound `out_ptr_ptr` or `out_len_ptr`, and it does not
     catch an exception from `memory.write`.
   - Decision 3 says "the same bounds". Either add them or say why the judge may differ.

9. **Housekeeping.** Low.
   - The spec's status line still reads "draft … so it is reviewed again before it is built".
   - The `wat.py` move sits in a spec-005 commit (`e51b438`). The landing notes should say so, so
     the 006 diff reads as complete.
   - `MAX_RESPONSE` is compared with `len(response)`. For a `memoryview` whose items are wider
     than a byte, that counts items, not bytes. The host is trusted, so the only effect is an
     unclear bound. Compare `response.nbytes`, or convert to bytes first.

### Runner mutations against the new checks (EXECUTED, `mutations.txt`)

| mutation of `runner.py` | the new checks that fail |
|---|---|
| memory default ignored | 1.6 |
| deadline default ignored | 1.7 hangs: it never ends, which leaves the judge red. I stopped it at 90 s |
| output cap off | 1.8 |
| `BASE_ENV` not applied | 1.3 only. 1.4 still passes, because the runner creates `/tmp` and `tempfile` tries `/tmp` anyway, so 1.4 guards the directory and not `TMPDIR` (INFERRED from `tempfile._candidate_tempdir_list`) |
| private root not removed | 1.5 |
| no `ptr + length` bound | 1.9 "request past memory" |
| no `MAX_RESPONSE` | 1.9 "response too large" |
| door body not wrapped | 1.9 "host raises" |
| output callback returns the short count | the pytest process aborts (exit 134, a panic inside wasmtime). The judge goes red, but the cap's "return `len(data)`" rule matters more than a comment says |

Each check guards what it names. Check 1.4 is the only one whose guard is weaker than its name.

### Confirmed (EXECUTED unless marked)

- **Decision 4, on both binaries.**
  - `sys.path == ['/usr/local/lib/python315.zip']`.
  - `sys.flags` gives `isolated=1`, `ignore_environment=1`, `safe_path=True`, `no_site=1`.
  - `sys._stdlib_dir` and `os.__file__` are in the zip.
  - `help` and `license` exist, and `exit(7)` returns 7.
- **Routes that do not run planted code, on both binaries, through the runner
  (`probes/p5_routes.py`).** These were planted: `sitecustomize`, `usercustomize`, a codec
  module, `fractions.py` and `statistics.py` beside a script, in `/`, in `HOME` and in
  `python3.15/`, `__pycache__` directories, and a `python315.zip.pth`.
  - Run 2 tried each of these: `-c`, `/script.py` (runpy does not add a file's directory to the
    path), `-m fractions`, `-m this`, and a directory with `__main__.py`. Run 2 was given
    `env={PYTHONPATH, PYTHONSTARTUP, PYTHONHOME, PYTHONBREAKPOINT, PYTHONINSPECT, PYTHONUSERBASE,
    PYTHONPLATLIBDIR, …}`.
  - No marker appeared.
  - `importlib.metadata.distributions()` finds nothing outside the zip, and
    `sys.path_importer_cache` holds only the zip.
  - `env=` is the caller's explicit choice, and isolated mode ignores those variables (READ:
    `PyConfig_InitIsolatedConfig`). The one exception is `PYTHONTZPATH`, which `zoneinfo` reads
    from `os.environ` as intended.
- **Decision 5.** Check 1.11 passes, in both orders.
- **The output cap holds (`probes/p6_output.py`).**
  - Each stream stops at exactly the cap, with `truncated == ('stdout', 'stderr')`.
  - The program tried 20,000 two-byte `os.write`s to each of fd 1 and fd 2, a write through
    `os.dup(1)`, and `-u`.
  - The run exits 0.
- **Removing a private root (`probes/p4_cleanup.py`, host Python 3.14).**
  - The guest made relative links that climb out (`../sentinel`, `..`), a hard link and a tree
    1,200 directories deep.
  - Absolute link targets were refused at creation (errno 63).
  - Removal deleted the root and nothing else: a sentinel directory beside it was intact.
  - `rmtree` does not follow links.
  - A 5,000-deep attempt ended by deadline and was removed as well.
- **Four concurrent rootless calls (threads)** each saw only their own root, and all four were
  removed.
- **The door.**
  - A deadline that expires inside the door is reported as `trapped == "deadline"`. N3 holds.
  - A host that raises gives −2, and the program goes on.
- **The base environment.** `env={"HOME": "/h"}` overrides `HOME`, `PYTHONTZPATH` stays `''`,
  and other keys pass through. This matches the README and the CHANGELOG.

## Constitution checks

- **§4.1 zero patches:** holds. The changes are in `recipes/` and `src/`.
- **§4.4 two channels:** holds. The suite's import checks pass, and the reset uses calls that are
  already imported.
- **§4.5 embedder-neutral:** holds.
- **§4.6 artifact set:** holds. Nothing large was added to git.
- **§4.9 tests count:** holds. Check 1.7 asserts only the stop reason. The check I propose for
  finding 1 counts descriptors.
- **§4.10 claims carry evidence:** two claims fail. "Enforced, and judged" is disproved by
  finding 2, and the notes' plain-reactor growth range by finding 4.
- **§5.4 small, finished, verified:** not yet. The scoreboard is red (finding 5).
- **§7:** nothing tripped.

## Disposition (filled in by the author, then confirmed by the reviewer)

1. **Fixed.** `_call` closes the store in a `finally`, before the private root is removed. A new
   check, `test_a_trapped_call_without_a_root_is_removed`, ends a rootless call by its deadline
   and asserts the scratch directory is empty.
2. **Fixed in part, documented for the rest.** `HOME` is now a fresh, empty directory per call
   (`/tmp/.home-<32 hex>`, removed after), so the `HOME` route is closed; a new check,
   `test_a_planted_pdbrc_in_home_never_runs`, plants `$HOME/.pdbrc` and asserts pdb in the next
   call does not run it (it fails with a fixed `HOME=/tmp`: EXECUTED by the author). The
   current-directory route (`/.pdbrc`) is native pdb's behaviour and is closed only by a fresh
   root; the policy now says "at start-up or on import", and the README and Decision 6 list
   `./.pdbrc` as reused-root data that pdb runs.
3. **Documented.** The README's and Decision 6's "not protected" lists name the host's file
   descriptors.
4. **Answered with a measurement.** Plain `import numpy, pandas`: 4,996,044,326 with this spec,
   4,991,298,112 without the `site` helpers, 4,995,332,324 on spec 005 (EXECUTED, the judge's
   driver). The helpers cost 4.75M; dropping `site.main()`'s path work saves about 4.0M; net
   +0.71M (+0.014%). The landing notes say so.
5. **Answered.** The prior-art row for `wasmtime-v49` is in `context/prior_art/README.md`
   (commit 7116620); landing runs `--accept-judge` and `--accept-growth`.
6. **Fixed.** The README and Decision 6 add files the caller names to run, concurrent calls on
   one root, and the rootless call's 11 MB copy.
7. **Fixed.** Check 1.5 asserts the first root's listing; the trap-cleanup check is added.
8. **Fixed.** The judge's door checks the two out-pointers too, and counts response bytes.
9. **Fixed.** The status line is updated at landing; the `wat.py` move's commit is named in the
   landing notes; `MAX_RESPONSE` is compared with `memoryview(response).nbytes`.

## Verdict

**Does not land yet.**
- The import-path fix, the snapshot's preopens, the bounded door and the output cap are sound,
  and the checks guard them.
- But two of the specification's headline claims fail under attack:
  - a trapped call keeps its guest's memory and handles until a collection runs (finding 1);
  - planted code still runs through `.pdbrc` (finding 2).
- The scoreboard is also red (finding 5).
- Finding 1 is a one-line fix, verified in scratch. Finding 2 needs a decision written into the
  spec. Findings 3 and 4 are text.

One line: the wall holds for imports, output and the door, but close the `Store` in a `finally`,
decide and judge pdb's rc files, list host descriptors as unprotected, and fix the growth note
before landing.

## Confirmation by the reviewer, 2026-10-17

- **Reviewed:** the working tree's uncommitted fixes on top of `46cbc2f`, eight files. They are
  `runner.py`, `guest.py`, the hostile-guest and data-stack checks, README, CHANGELOG,
  `AGENTS.md`, and the spec's revision with its landing notes. I also read the author's
  dispositions above. I read the whole diff, not only the lines the dispositions name.
- **Re-ran (EXECUTED).**
  - `uv run pytest -m "not slow"` → `111/118 pass · 0 fail`; `270 passed, 2 skipped, 4
    deselected, 1 xfailed`; ratchet `lost 0 · gained 20 · grew 16 · judge changed`. The run
    exits 1 only for growth.
  - `tests/checks/test_v1_2_hostile_guest.py` → `20 passed`, twice.
  - The same file on the 0.1.0a1 set → `4 failed, 16 passed`. These are the same four checks
    that judge the binaries.
  - `ruff check` and `ruff format --check` on `src` and `tests` → clean.
  - My probes `p1_pdbrc`, `p1b_pdbrc_nostdin`, `p3c_memory`, `p3d_memory_gc_on`, `p3_release`,
    `p5_routes` and `p6_output`, all re-run on the fixed runner (`confirm-probes.txt`).
  - Two new probes: `p7_fdcount.py`, a counting guard, and `p8_home_race.py`.
  - Two mutations of the fixes, on scratch copies (`mut2/`).

### Each finding

1. **Confirmed fixed in the code. The new check does not guard the fix (reopened as C1).**
   - **The fix works.**
     - Memory: four trapped calls that each touch 400 MiB leave RSS at 88 MB throughout, with
       the collector on or off. Before the fix it reached 1,706 MB.
     - Handles: `lsof` shows nothing held at removal in all five cases, trapped ones included.
   - **The new check passes without the fix.** I removed `store.close()` (mutation `no-close`),
     and `test_a_trapped_call_without_a_root_is_removed` still passes. On POSIX, `rmtree` deletes
     a directory that is still open. So this check can catch a regression only on Windows.
2. **Confirmed for the HOME route.**
   - Every probe now leaves no marker from a planted `$HOME/.pdbrc`, on both binaries. The probes
     covered `breakpoint()`, `pdb.post_mortem()` and `-m pdb`, with and without stdin.
   - The new check fails with `HOME` fixed at `/tmp` (mutation `home-fixed`), so it guards the
     fix.
   - The `/.pdbrc` route in the current directory still runs on a reused root (EXECUTED). It is
     now disclosed in the policy, the README and Decision 6. A rootless call, the default, closes
     it.
   - I accept this as a written answer. One wording point (C3): it is listed as "data", though
     pdb runs it as code.
3. **Confirmed.** Host descriptors are listed as not protected, in the README and in Decision 6.
4. **Confirmed.** The author's three figures for plain `import numpy, pandas` match the
   scoreboard's 4,996,044,326 and the accepted 4,995,332,324. The landing notes now say +0.014%
   and give its cause. I did not rebuild the variant without the helpers.
5. **Confirmed.**
   - `wasmtime-v49` has its row (`7116620`).
   - The rules check passes.
   - The landing needs `--accept-judge` and `--accept-growth`. The `--accept-growth` covers the
     15 metrics I listed (the snapshot's −c runs, the plain numpy/pandas import and the two
     sizes); the scoreboard counts 16.
6. **Confirmed.** The README lists caller-named scripts, concurrent calls on one root and the
   11 MB copy.
7. **Confirmed.** Check 1.5 now asserts `['left-behind', 'tmp', 'usr']`. The trap-cleanup check is
   C1.
8. **Confirmed.** The judge's door checks both out-pointers and counts `nbytes`.
9. **Confirmed.**
   - The landing notes name `e51b438`.
   - `MAX_RESPONSE` is now compared in bytes.
   - The status line is still "draft". The author will change it at landing, which is acceptable.

None of 2 to 9 is reopened.

### New findings from the fixes, most severe first

C1. **The trapped-call check does not guard the store's release on POSIX**
    (`test_a_trapped_call_without_a_root_is_removed`). Medium-low.
    - The check passes with `store.close()` removed (EXECUTED).
    - A counting guard tells the two apart (EXECUTED, `p7_fdcount.py`). Warm up with one call,
      then count `/dev/fd` entries before and after a trapped call whose guest holds five open
      files.
      - Fixed runner: 8 before, 8 after.
      - Without `close()`: 8 before, 14 after.
    - **Fix.** Add that count to the check. Skip the count where `/dev/fd` does not exist, and
      keep the empty-directory assertion for Windows. It counts descriptors and times nothing
      (§4.9). AGENTS.md rule 3 asks for this: a failure mode, once seen, becomes a check.

C2. **The fresh `HOME` is made through `/tmp`, a path component a concurrent guest on the same
    root controls** (`runner.py` `_call`: `home.mkdir()`, and `shutil.rmtree(home)` in the
    `finally`). Low.
    - **The probe (EXECUTED, `p8_home_race.py`).** It simulates what a second guest running on
      the same root can do between `_real_dir` and `home.mkdir()`: replace `/tmp` with
      `../outside`, a relative link out. Relative links that climb out can be created; the guest
      cannot open through them.
    - **What happened.** The host made `outside/.home-<hex>` **outside the root**. The call ran.
      The `finally` then removed that directory, again through the link.
    - **Why the harm is small.**
      - The directory is empty and has a random name.
      - Guests cannot open through the link.
      - Removal reaches only the directory the runner itself made. The 128-bit name cannot be
        planted outside the root beforehand.
      - It needs concurrent calls on one root, which the README now lists as not isolated.
    - **Still, it is a host write outside the root.** That is the class of thing `_real_dir`
      exists to prevent.
    - **Fix, the author's choice.**
      - Make the directory relative to a descriptor: open `tmp` with `O_DIRECTORY|O_NOFOLLOW`,
        then `os.mkdir(name, dir_fd=…)`, and remove it the same way.
      - Or set `HOME` to the random path without creating it. pdb then finds no `.pdbrc`, and a
        program that writes under `~` gets `ENOENT`.
      - Or state the residue next to "concurrent calls on one root".

C3. **Text.** Low.
    - **Decision 2.** "The three can be overridden but not removed; the README and the CHANGELOG
      say so…" now hangs off the store-closing bullet. With `HOME` per call, the base is two keys
      plus `HOME`. Move the sentence back to the environment bullet and reword it.
    - **The policy, the README and Decision 6.** They call `./.pdbrc` "data planted in a reused
      root", and then say pdb runs it. Name it for what it is: "code that pdb runs from `./.pdbrc`
      when a program starts it".

C4. **One judge change in this tree belongs to another specification** (`test_v1_3_data_stack.py`:
    the C++ check's fuel metric is removed, citing spec 008's review N2). Low.
    - The reason is stated, and the metric's noise is that review's measurement (READ; I did not
      re-measure it).
    - But AGENTS.md rule 4 makes a judge change its own change. Name it in the `--accept-judge`
      reason, or land it with 008, so the history shows why a metric left the ratchet.

### Verdict

**Ready to land once C1 is fixed.** The two High findings are closed in the code, and I verified
both by re-running the attacks:
- a trapped call's memory and handles are released at once;
- a planted `$HOME/.pdbrc` no longer runs.

Each remaining channel is disclosed. C1 is a few lines of a check: without it, the store fix is
judged only on Windows. C2, C3 and C4 may be answered in writing at landing. Landing runs
`--accept-judge` and `--accept-growth` with the reasons above.

One line: the fixes hold under the same attacks; make the trapped-call check count descriptors,
then land.

## The author's answers to the confirmation

- **C1:** fixed. The check makes one warm-up call, then counts `/dev/fd` before and after the
  trapped call; it passes with `store.close()` and fails without it (EXECUTED by the author).
- **C2:** fixed. The fresh `HOME` is made and removed through a handle on `/tmp` opened with
  `O_NOFOLLOW | O_DIRECTORY` (`os.mkdir(..., dir_fd=)`, `shutil.rmtree(..., dir_fd=)`); Windows,
  which has no `dir_fd` and whose guests cannot make links, uses the path.
- **C3:** fixed. Decision 2's sentence is back on the environment bullet; the policy and the
  README say `./.pdbrc` is run as code, not data.
- **C4:** answered. The C++ check's metric removal is named in this landing's `--accept-judge`
  reason, with spec 008's review as its cause.
