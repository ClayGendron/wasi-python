# 127: The pin moves to wasmtime 50

- **Status:** **drafted 2026-10-24**, from decision 86 ("the shadow is removed with the pin that moves past wasmtime 49.0.3") and the research memo below, now that wasmtime-py 50.0.1 is on PyPI. Its checks are named in Decision 3 and not yet written: the builder writes them first and records them failing on main's code (AGENTS.md rule 3), then builds. It is runner code, and it hands two file calls of the sandbox back to wasmtime's own, so a **pre-build review is required** (AGENTS.md rule 8; constitution §5.6); a different agent reviews the build.
- **Date:** 2026-10-24
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, **not structural**, **a judge change**. It touches `pyproject.toml` and `uv.lock` (the pin), `src/` (`_wasmtime_ffi.py`, `_fs_memory.py`, `_fs_descriptors.py`, `_fs_paths.py`, `_fs_table.py`, `_call.py`, `_process.py`, `_engines.py`'s one message), `tests/` (the checks of Decision 3, `tests/harness/files.py`), `SECURITY.md`, `README.md`, four pages of `docs/`, the debt sheet `../upstream/34-wasmtime-py-public-api-for-the-runner/facts.md`, and `CHANGELOG.md`. It touches nothing under `scripts/`, `recipes/`, `downloads/SHA256SUMS` or the release workflow, and no artifact byte: the wasmtime CLI the build uses stays at 49.0.3 (Decision 6). Decision 8 says why it is not structural. It changes no default an embedder can see (constitution §4.15). `pyproject.toml` and `uv.lock` are judge files and the guard's checks go, so the acceptance carries `--accept-judge` (For the lane).
- **Depends on:** landed and unchanged: 048 (the two shadows and the removal predicate this specification carries out), 103 (the engine seam, where the one changed read lives), 068 (the counted calls, which stay), 104 and 105 (the package and the process object whose fields it deletes), 002 (the ratchet's rule for a changed wasmtime version). On nothing in flight. Spec 126 (drafted, not built) shares `_engines.py` with it by one line at most; the memo's §6 shows that 126's cause is gone under wasmtime 50, and what to do with 126 is the owner's, outside this specification.
- **Research it stands on:** `../research/2026-10-24-moving-to-wasmtime-50.md` (every fact below is EXECUTED or READ there unless marked), on `../research/2026-10-18-wasmtime-49-advisories.md` and its advisory records, which the rules check reads.

## The problem

The published pin is `wasmtime>=49,<50`. The only wasmtime-py in that range is 49.0.0, which bundles wasmtime 49.0.0, and 49.0.0 sits inside the vulnerable range of every wasmtime advisory fixed since September, two of which reach a guest. Spec 048 carried those two fixes in the runner as shadows of `fd_readdir` and `path_rename` on every call, as a belt to be taken off "with the pin that moves past wasmtime 49.0.3" (decision 86).

wasmtime-py 50.0.1 was uploaded to PyPI on 2026-10-22. It bundles wasmtime 50.0.0, released 2026-10-20. Against wasmtime 50.0.0's own WASI, with no runner and no guard, the trailing-slash symlink rename answers `ENOTDIR` and moves nothing, and `fd_readdir`'s padding is zero in every entry; on 49.0.0 the same two operations move the outside folder in and leak host bytes. So the condition decision 86 set is met.

Three more things the move must carry. The judge's removal rule, written against each advisory's `patched_versions`, does not admit the move: that field names only the patch lines (`36.0.18, 48.0.6, 49.0.3`), never the next major, so `>=50,<51` keeps both guards and the check would turn red the day they are deleted. wasmtime-py's `Slab` lost its `list` after 49.0.0, so one read of the seam raises. And wasmtime 50 changed the words it ends a run with when a guest passes an argument out of its type's range, which the mount's parity with a plain grant compares.

One thing the move gives for free: under wasmtime 50.0.0 the module's drop takes 20 ms where 49.0.0 took 5.7 s on macOS, and `wasi-python run -- -c "print(1)"` takes 0.43 s where it took 5.4 s.

## Decisions

### 1. The pin is `wasmtime>=50,<51`, done where the seam says

`pyproject.toml`'s one dependency becomes `wasmtime>=50,<51`; `_wasmtime_ffi.PIN` says the same; `uv.lock` is remade with `uv lock --upgrade-package wasmtime` and names 50.0.1; `_engines._wasmtime`'s `ImportError` message, which cannot import the seam because wasmtime-py itself is missing when it is raised, spells the pin by hand as it does today. The seam's docstring lists the steps of a major bump; the builder follows them and the landing notes say so.

- **Why a major line, not `>=50.0.1`.** The judge tests one wasmtime major (spec 004) and compares fuel within one version (spec 002, Decision 6). Within the line, wasmtime-py's patch releases are wasmtime-py's own (50.0.1 is one, on the same wasmtime 50.0.0), so the floor is the line's first release.
- **What the wheel bundles, recorded** (spec 048's Decision 5 asks the moving specification to record it, because the two numbers can differ): wasmtime-py 50.0.1 bundles wasmtime **50.0.0** (READ: `ci/download-wasmtime.py` at tag 50.0.1, `WASMTIME_VERSION = "v50.0.0"`; EXECUTED: the wheel's library carries `version: 50.0.0`). There is no wasmtime 50.0.1 and no PyPI files for wasmtime-py 50.0.0.

### 2. The guard goes, and the linker that stays is named for what it does

Everything spec 048 added to serve the two guarded calls is deleted, and the native call is used again:

- `_fs_memory`: `GUARDED`, `PRIVATE`, `stat_trampoline_wat`; the comment block on the two advisories.
- `_fs_descriptors`: `_fd_readdir`'s zeroing after a forward (`_zeroed`, `_zero_pads`, and `_grow` if nothing else uses it); the forward stays a forward.
- `_fs_paths`: `_path_rename`'s branch for two of wasmtime's numbers (the slash test, the staging limit, the no-follow stat through `_source_type`, the trimmed forward); a rename of two wasmtime numbers is forwarded unchanged. The **mount's own served rename keeps the rule** that a trailing slash on either path needs a folder source, judged without following its link: it is wasmtime's rule now, natively, and the parity holds the mount to a plain grant (`RENAME_SLASH_NEEDS_FOLDER` and its comment reworded).
- `_fs_table`: `_Files.forward`'s `stat=` branch and the guard's page; `bind`'s stat trampoline.
- `_call`: `_stat_trampoline_module`; the second module `_trampolines` returns. `_guard_linker` keeps only the three calls in `COUNTED` (spec 068's cap on open files) and is renamed **`_counted_linker`**, with `_Process.guard_linkers` renamed `counted_linkers` and `stat_trampolines` deleted (its `__init__` and its fork reset). `tests/harness/files.py`'s `Guarded` becomes `Counted`, its docstring the three calls.
- **Why rename.** "Code speaks for itself" (AGENTS.md): a linker called a guard that guards nothing misleads the next reader; the name now says what the three shadows are for.
- **What a guest sees change.** A slash-named rename answers wasmtime's own errno order: `EBADF` for a bad descriptor and `EPERM` on a read-only or mixed pair come before `ENOTDIR`, as spec 048's Decision 3 said they would once the guard went. An over-long slash-named source gets wasmtime's own answer, not the guard's `ENAMETOOLONG` (Decision 3b). `fd_readdir` and `path_rename` on a call without mounts no longer answer `EIO` once the call has stopped, since they are not shadowed (spec 048's stated stop behaviour goes with it; the counted three keep it). Nothing else: no default, no public name, no limit.

### 3. The checks first (the existing checks this changes, each with its reason, as a judge change)

Written or changed before the code, each seen failing on main's code where the row says so, in files the `own-runner` shard runs on three systems. No check measures time.

- **3a. `tests/checks/test_rules.py::test_the_rename_and_readdir_guard_match_the_floor`**: the rule reads each advisory's **`vulnerable_version_range`** from its record in the memo's folder, not `patched_versions`. The range is a comma list of clauses; consecutive clauses with `>=`/`>` and then `<`/`<=` bound one span, a lone upper bound opens at 0.0.0, a lone lower bound has no top. A guard may go when no version the requirement admits lies in any span; a requirement with an open top, a minor-version bound, or an operator outside `>=`, `<`, `<=`, `==` keeps the guard. The table of expectations becomes: `>=49,<50` keeps both; `>=50,<51` lets both go; `>=49.0.3,<51` lets both go (49.0.3 and the 50 line are outside every span); `>=49.0.2,<50` lets the padding guard go and keeps the rename guard; `>=49.0.3` (open top) keeps both. The record check becomes: each advisory's `vulnerable_version_range` equals the string written in the check. Once a guard may go, the rest holds as today: no advisory id in `src/`'s filesystem modules and no test names it. **Seen failing first:** on main's code with the table rewritten, `>=50,<51` reads False. Reason, for the claim list: the removal rule reads the advisories' own statement of which versions are vulnerable; a later major is outside every span, where `patched_versions` never names one.
- **3b. The two sandbox checks stay and now prove wasmtime's own rule**: `tests/checks/test_v1_2_hostile_guest.py::test_a_trailing_slash_symlink_rename_cannot_escape` (unchanged rows: the rename answers `ENOTDIR`, the canary stays, nothing named `stolen`) and `::test_a_trailing_slash_rename_rule`, whose over-long row (`"./" * 2100 + "s/"`, the guard's `ENAMETOOLONG`) is **re-derived against wasmtime 50's own answer** on the three systems and recorded with it, since the staging limit was the guard's; the other rows (`ENOTDIR` for a slash-named file or link, `ENOENT` for a missing source, folders renamed with or without slashes) are wasmtime's answers and stay. Their comments name the behaviour in words and no advisory id (3a's clause).
- **3c. `tests/unit/test_runner_mounts.py`**: the guard's own checks are deleted: the padding checks of the forwarded listing (the `0xA5` rows, the `used`-over-the-listing rows, the second listing's two failure branches, the page cap), `test_the_rename_rule_forward_is_fuel_neutral` with `NATIVE_RENAME_END` and the rename loop (wasmtime 50 ends it `ENOTDIR` on every system, so the per-system table has nothing to say), and the plain-name forward check. `test_a_guard_call_leaves_the_other_calls_native` becomes **`test_a_counted_call_leaves_the_other_calls_native`**: the counted linker shadows exactly `path_open`, `fd_close` and `fd_renumber`. The rule table's four rows marked "order" (`read-only file, slash`, `read-only nothing, slash`, `to a bad descriptor, slash`, `a file, slash, to read-only`) are re-derived against a plain grant, which answers wasmtime's order (`EPERM`, `EBADF` first). The mask `(21, 22, 23)` added at line 1185 goes: a plain grant's padding is zero and is compared. Every `files.Guarded` becomes `files.Counted` or `files.grant_raw` as the row's reference asks (a row about the cap keeps `Counted`; a row about what wasmtime answers takes the plain grant).
- **3d. `tests/unit/test_runner_grants.py::test_raw_calls_answer_as_a_grant_does`** holds the ten trap-word rows (Decision 4): the grant side is wasmtime 50, the mount side the runner; a passing table is the check. **Seen failing first:** the memo's run on main's code, ten rows. `SLASH_ROWS` stay (wasmtime 50 answers them natively); `_write_sides`' reference becomes a plain grant.
- **3e. `tests/unit/test_wasmtime_ffi.py::test_the_judges_three_reads_of_wasmtime_pys_own_tables`** passes once `host_function_count` reads `handles` (Decision 5); a new row **`test_a_slab_without_handles_is_named_by_the_import_check`**: `missing()` on a holder table whose `wasmtime._func.FUNCTIONS` lacks `handles` names `wasmtime._func.FUNCTIONS.handles`. **Seen failing first:** on main `NEEDED` has no such row. `test_the_pin_is_written_the_same_in_three_places` holds the three spellings; `tests/checks/test_rules.py::test_the_private_api_debt_is_documented` holds the debt sheet equal to the tuples, so the sheet gains the row.
- **3f. `tests/checks/test_v1_4_embedding.py::test_a_plain_install_brings_wasmtime`** and **`::test_a_wasmtime_that_cannot_load_is_named`**: `>=50,<51`. Reason: the pin moved.
- **3g. `tests/harness/files.py`**: `DIRENT_MASKED`'s comment (the padding is wasmtime's zero now); `Guarded` → `Counted`.
- Nothing in `tests/known_gaps.toml`, no golden output, no upstream allowance, no release-tier row changes. The fixtures that spell `"49.0.0"` as data (`test_gather.py`'s `WT`, `test_history.py`, `test_scoreboard.py`) are their own inputs, not the installed version, and stay.

### 4. The runner says wasmtime 50's words for an argument out of range

`_fs_memory._unsigned` ends the run with "number too small to fit in target type" for a negative value and "number too large to fit in target type" for one above its type's top, where it said "out of range integral type conversion attempted" for both (49.0.0's words). The parity (3d) is the check; the comment gives the reason in words (the mount answers as a grant does, and wasmtime's conversion names the direction).

### 5. The seam's one changed read, and the import check names it

`_wasmtime_ffi.host_function_count` returns `len(_func.FUNCTIONS.handles)`. `NEEDED` gains `("wasmtime._func.FUNCTIONS", "handles")`, with the holder table given `FUNCTIONS` under that dotted name, so a wasmtime-py that moves it again is named at the first `run()` and not at the judge's read. The seam's debt list gains the matching line (`-> none wanted (the judge reads it)`), and the debt sheet its row. Nothing else in the seam changes: every other private name exists in 50.0.1 and no public form the seam prefers appeared (the memo's §2).

### 6. The wasmtime CLI stays at 49.0.3

The three archives in `downloads/SHA256SUMS`, `scripts/line.conf` and `scripts/00_download.sh` are untouched. The CLI's one job is `wasmtime wizer` in the snapshot step, with one read-only preopen and no guest-controlled program; the two WASI fixes concern a running guest's file calls, and the critical aarch64 `br_table` advisory needs about 256k targets on one instruction where `python.wasm`'s largest has 3,203 (EXECUTED in the memo). Moving the CLI changes a recipe input and may change the snapshot's bytes (INFERRED in the memo's §7), which is a rebuild on three systems: build-class work. It is **a separate specification**, to be drafted for the next rebuild of the line (the roadmap holds it), not a dependency of this one. The runner's version and the CLI's are independent (READ: nothing in `src/` reads the CLI; nothing in `scripts/` reads wasmtime-py but `compare_snapshots.py`, a tool for a failed same-bytes check).

### 7. Fuel: not compared across versions, recorded fresh, no growth flag

Spec 002's Decision 6 and `scoreboard.py`: a row whose accepted `wasmtime` is not the run's goes to `fuel_not_compared`, never to growth, and the acceptance records the fresh value. So every metered check's fuel is re-recorded under 50.0.1 at the landing; no `--accept-growth` is needed, and a growth line for **bytes** is still red. The builder's branch run shows the `fuel_not_compared` count as the expected signal. Known moves: hello on the snapshot, the numpy sum and the stat loop are equal to the instruction; the plain reactor's hello fell by 502,255 instructions (1.8e-3). The landing notes quote these three fuels under 49.0.0 and 50.0.1 from the memo and from the branch's run.

### 8. The shape of the change (not structural)

The change deletes about 300 lines of guard machinery and adds a dozen: one row in `NEEDED`, one read in the seam, two words in `_unsigned`, one renamed linker. No module-level mutable or lock (two process-object fields go; none is added); no private wasmtime-py name outside `_wasmtime_ffi.py` (the changed read is inside it); no platform branch; no test seam. Every module shrinks or holds (`_call.py` from 1,343 lines; `_fs_descriptors.py`, `_fs_paths.py`, `_fs_table.py`, `_fs_memory.py` lose their guard parts); no function nears 80 lines. The rules checks show it green.

### 9. What the documents say

`SECURITY.md`'s wasmtime paragraph: the runner uses wasmtime-py 50.0.1, which bundles wasmtime 50.0.0, whose `path_rename` and `fd_readdir` carry the two fixes themselves; the runner carries no fix of its own; an embedder who drives the artifact set with an engine older than wasmtime 49.0.3 (or 48.0.6, 36.0.18) lacks them. The same in words on `docs/explanation/security-model.md` and `docs/how-to/embed-from-other-languages.md`; `docs/reference/support-and-versioning.md`, `docs/get-started/install.md` and the README's *Hosts* say wasmtime 50 (`wasmtime>=50,<51`). The hosts list's "wasmtime 47 or later" for the artifacts is unchanged: the binaries did not change.

## Intent

A `pip install wasi-python` user runs on a wasmtime whose own file calls hold the sandbox, with no fix carried in Python, and the project's pin names no vulnerable release. The two advisories' checks keep running, now against wasmtime itself. Nothing an embedder can observe changes but the errno order of a slash-named rename on a bad or read-only pair, which is wasmtime's own, and the time a process takes to end.

## Design

- `pyproject.toml`, `uv.lock`: Decision 1.
- `src/wasi_python/_wasmtime_ffi.py`: `PIN`, `NEEDED`, the holder table in `check(...)`, `host_function_count`, the debt list's new line; the docstring's bump steps unchanged.
- `src/wasi_python/_engines.py`: the one `ImportError` message spells `wasmtime>=50,<51`.
- `src/wasi_python/_fs_memory.py`, `_fs_descriptors.py`, `_fs_paths.py`, `_fs_table.py`, `_call.py`, `_process.py`: Decision 2's deletions and the rename; `_unsigned`'s words (Decision 4). Comments give the reasons in words: the mount answers as a grant does; a call without mounts shadows the three calls the cap on open files counts; nothing is said about advisories or versions.
- `tests/checks/test_rules.py`, `tests/checks/test_v1_2_hostile_guest.py`, `tests/checks/test_v1_4_embedding.py`, `tests/unit/test_runner_mounts.py`, `tests/unit/test_runner_grants.py`, `tests/unit/test_wasmtime_ffi.py`, `tests/harness/files.py`: Decision 3.
- `context/upstream/34-wasmtime-py-public-api-for-the-runner/facts.md`: the `handles` row (Decision 5); its "Against" line says 50.0.1.
- `SECURITY.md`, `README.md`, `docs/explanation/security-model.md`, `docs/how-to/embed-from-other-languages.md`, `docs/reference/support-and-versioning.md`, `docs/get-started/install.md`: Decision 9.
- `CHANGELOG.md`, under the next unreleased section (`release/version.py bump` makes it): one line (below).

### The CHANGELOG line

- **The pin moves to wasmtime 50** (spec 127). The wheel requires `wasmtime>=50,<51`; wasmtime-py 50.0.1 bundles wasmtime 50.0.0, whose `path_rename` and `fd_readdir` carry the fixes of the two advisories the runner had applied itself since 0.1.0a4 (a rename of a symbolic link named with a trailing slash could move a host folder into the sandbox on macOS; directory listings carried up to three bytes of host memory per entry). The runner's two shadows are gone, and a call without mounts passes only the three calls the cap on open files counts through the runner; the two sandbox checks now run against wasmtime's own calls. Fuel is equal to the instruction on the snapshot; the plain reactor's start-up spends 502,255 fewer. On macOS, ending a process that compiled or loaded the guest no longer costs about 5 s: `wasi-python run` of a one-line program takes about 0.4 s where it took 5.4 s, because wasmtime 50 registers its unwind information with the system in bulk. A guest that passes a file call an argument out of its type's range ends with wasmtime 50's words, which name the direction.

## Scope

In: the pin in its three spellings and the lock; the guard's removal and the linker's name; the seam's one read and its import-check row; the trap words; the checks of Decision 3; the documents of Decision 9; the CHANGELOG line. Out: the wasmtime CLI (Decision 6, its own build-class specification); spec 126 and the module cache's name; spec 011's own callback table (wasmtime-py's `Slab` is now thread-safe upstream, a later question); any change to the counted calls or their cost (the memo's §5); the mount's served rename rule (kept).

## Acceptance criteria

1. `pyproject.toml`, `_wasmtime_ffi.PIN` and `_engines._wasmtime`'s message spell `wasmtime>=50,<51`; `uv.lock` names wasmtime 50.0.1; `uv run python -c "import wasi_python._wasmtime_ffi"` succeeds (Decision 1).
2. No advisory id and no guard remains in `src/`'s filesystem modules; `_fs_memory` has no `GUARDED`, no `PRIVATE`, no stat trampoline; the process object has no `stat_trampolines`; the counted linker shadows exactly three calls (Decisions 2 and 3c).
3. The removal rule reads the vulnerable ranges and its table of expectations passes, with `>=50,<51` letting both guards go (Decision 3a).
4. The two sandbox checks pass on three systems against wasmtime's own calls, the over-long row recorded with wasmtime 50's answer (Decision 3b).
5. The parity of the mount with a plain grant passes with the ten trap-word rows and zero padding compared (Decisions 3c, 3d, 4).
6. The seam's import check names `wasmtime._func.FUNCTIONS.handles` when it is absent, and the judge's three reads pass; the debt sheet equals the tuples (Decisions 3e, 5).
7. The fast tier is green on the branch; the branch's release run is green on three systems, its `fuel_not_compared` rows named in the landing notes and no `grew` line for bytes (Decision 7).
8. `ruff check`, `ruff format --check`, `mypy --strict` and the rules checks are green; no module or function crosses a ceiling (Decision 8).
9. The builder records, as benchmark facts in the landing notes and not as checks: hello's three fuels under 49.0.0 and 50.0.1; one module drop timed in a fresh process on the build machine; `wasi-python run -- -c "print(1)"` wall before and after.

## For the lane

- **Wave kind:** parallel-safe, runner code; the pre-build review is required. It conflicts with nothing in flight but `CHANGELOG.md`; with spec 126, if built beside it, by `_engines.py`'s one message line at most.
- **The claim list:** `test_the_rename_and_readdir_guard_match_the_floor` (the rule reads the vulnerable ranges; the table rewritten); the guard's checks in `test_runner_mounts.py` deleted and `test_a_guard_call_leaves_the_other_calls_native` renamed; the four "order" rows and the over-long row re-derived against wasmtime's own answers; `test_raw_calls_answer_as_a_grant_does`'s ten trap-word rows and its unmasked padding; the pin's text in `test_a_plain_install_brings_wasmtime`, `test_a_wasmtime_that_cannot_load_is_named` and `test_the_pin_is_written_the_same_in_three_places`; the new `test_a_slab_without_handles_is_named_by_the_import_check`; every metered check's fuel re-recorded under wasmtime-py 50.0.1 (not compared, spec 002 Decision 6). No gap entry, no golden output, no growth.
- **Flags:** `--accept "127: the pin moves to wasmtime 50; the guard goes"`, `--accept-judge "127: pyproject.toml and uv.lock move the pin to wasmtime>=50,<51; the guard's checks go and the removal rule reads the advisories' vulnerable ranges; the parity's trap words follow wasmtime 50"`. No `--accept-growth`: a growth line for bytes ejects the entry; fuel shows as not compared, never as growth.
- **Sameness:** the reviewer's record and the lane's are both on 50.0.1, so fuel compares between them as usual; a record on 49.0.0 (an older worktree) compares no fuel with them, by the same rule.

## Landing notes

Not yet built. The builder fills this section: the commits, the checks seen failing on main's code first (the removal rule's table, the `Slab` row, the ten parity rows), the seam's bump steps as followed, the fast tier, the branch's release run (its id, every line green, the `fuel_not_compared` count, no `grew` line), the over-long row's answer on each system, the benchmark facts of acceptance criterion 9, the self-check list (`../reviews/README.md`), and the rebase onto the wave's tip with every conflict named.

## One line

The wheel requires `wasmtime>=50,<51` (wasmtime-py 50.0.1, wasmtime 50.0.0), spec 048's two shadows and their trampoline go because wasmtime's own `path_rename` and `fd_readdir` now hold the sandbox, the judge's removal rule reads the advisories' vulnerable ranges so it can say so, one `Slab` read and ten trap-word rows follow wasmtime 50, fuel is recorded fresh and not compared, the CLI stays at 49.0.3 for the next rebuild, and a process ends in milliseconds instead of seconds.
