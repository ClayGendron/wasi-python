# 076 — The grant checks agree on Windows

- **Status:** drafted 2026-10-18 on `spec/076-the-grant-checks-agree-on-windows` from main
  `7307f6f`; not built. It changes neither the guest's imports nor its exports, the artifact set
  nor the build recipe, so §5.6 asks no review before build. A different agent reviews the build.
  **It lands before spec 063 and before 0.1.0** (Decision 8).
- **Date:** 2026-10-18
- **Owner:** Clay Gendron
- **Kind:** the runner, the judge and docs; **parallel-safe**, not build-class.
  `src/wasi_python/runner.py` (`_walk_windows` only); judge changes in
  `tests/checks/test_v1_2_hostile_guest.py` (two checks), `tests/unit/test_runner_mounts.py`
  (one check) and `tests/unit/test_runner_grants.py` (two cases extended, one added);
  `README.md`, `CHANGELOG.md`; `context/upstream/` (fact 5 in facts sheet 12, a new facts sheet
  20 and its row in the folder's README). Its landed diff touches no `scripts/`, `recipes/`,
  `downloads/SHA256SUMS` or workflow. One temporary commit that adds four node ids to the
  release workflow's `verify` step exists only for the Windows dry run and is dropped before
  review (Decision 7). **It changes no line of `tests/public_api.txt`.**
- **Depends on:** 017 (typed grants: the walk, its rules and its `..` choice), 048 (the rename
  guard, carrying wasmtime 49.0.3's rule), 058 (the Windows grant precedent), all landed. Spec
  063 (the release judges in parallel shards, built, in review) found the failures; it does not
  depend on this spec's code, but its Windows judge cannot pass without it. Spec 068 (a cap on
  open files, confirmed, landing next) touches `mounts.py` and `runner.py` elsewhere; whichever
  lands second rebases, with no shared hunk expected.
- **Research it stands on:**
  - Spec 063's three branch dry runs, job "judge (windows-2025, own-guest)": runs 39182550825,
    39184807592 and 39186533835 (EXECUTED there). Their logs are in the main tree, git-ignored:
    `build/reviews-evidence/063-build/run2/judge__windows-2025__own-guest__.log`,
    `run3/judge__windows-2025__own-guest__.log` and `run4/windows-own-guest.log` (read whole
    here). The same four checks fail the same way in all three; in `run4`, lines 395 to 481
    (the read-only grant), 600 to 640 (the bad grant) and 645 to 667 (the rename).
  - wasmtime-wasi 49.0.0, the crate wasmtime-py 49.0.0 bundles (facts sheet 12, fact 1), from
    the local cargo registry, and `context/prior_art/wasmtime-v49` (tag `v49.0.3`, `f96eaba`),
    both READ, never edited. Cited as `49.0.0:` and `49.0.3:` below. `context/prior_art/wasmtime`
    (main, `2d9c19b`) is cited once.
  - CPython's `Lib/ntpath.py` and `Modules/_io/fileio.c` (`context/prior_art/cpython`, branch
    3.14, `7c04882`, READ).
  - The runner and the guard on main `7307f6f` (READ): `src/wasi_python/runner.py` and
    `src/wasi_python/mounts.py`.
  - Spec 017's "Choices the specification left to the build" (`..` after a missing component),
    spec 048's Decisions 1 to 3, spec 058's Decision 1.
  - Spec 063's build review, F4 (written in the lane's scratchpad, `063-buildreview/`; a copy is
    in the main tree at `build/reviews-evidence/063-buildreview/`, READ): none of the four is a
    security defect in itself (the bad grant INFERRED there), but the bad-grant check stops at
    its second refusal on Windows, so the refusals after it, and the rename check's loop over
    caps, have never run there; 063 lands only once they run green on Windows.

**The bad grant is not a security hole.** On Windows a root spelled `…\new\..\x` is accepted,
and the runner makes and grants `…\x`. That is the folder the spelling names on Windows: the
runner judges that folder by identity, holds it, hands wasmtime that exact path, and checks the
folder wasmtime opened against the one it judged. No rule is skipped and no other folder can be
granted (cause 3, below, READ here line by line; spec 063's build review, F4, reached the same
conclusion as INFERRED). It is a parity defect: POSIX refuses the same spelling before any
work, and spec 017 decided it should. It is fixed here, in the product, so every system refuses
it.

## The problem

Spec 063 runs product-check files on Windows that never ran there before. Four checks fail on
`windows-2025`, the same way in three branch dry runs (EXECUTED there):

1. `test_a_read_only_grant_refuses_every_write[plain]` and `[snapshot]`. Every write is still
   refused, and the host files are unchanged (the check got past `exit_code` and the control
   write, and failed on the table only). Two rows differ from the check's table:
   - "write a read descriptor" answers 2 (`EACCES`), where the table says 8 (`EBADF`);
   - "through a link in the grant" answers 63 (`EPERM`), where the table's Windows branch says 44
     (`ENOENT`). On Linux and macOS this row's table value is 63.
2. `test_a_bad_grant_is_refused_before_any_work`. `refused(ValueError, "does not exist",
   root=base / "new" / ".." / "x")` raises nothing on Windows: "DID NOT RAISE ValueError". The
   call ran, so the rest of the check never ran on Windows.
3. `test_the_rename_rule_forward_is_fuel_neutral`. The first comparison fails: today's native
   linker ends `('returned 44', 2005)` and the guard's ends `('returned 54', 2005)`. The fuel is
   equal; the ending is not. The per-cap loop after it never ran on Windows.

## The causes

Each was found by reading the code and wasmtime's sources; no Windows machine was used here.

1. **"write a read descriptor": wasmtime's preview1 lets the host answer** (READ). `fd_write`
   and `fd_pwrite` on a file go straight to the host's write: `fd_write_impl` checks neither the
   grant's permissions nor the descriptor's open mode (49.0.0: `crates/wasi/src/p1.rs:626-695`;
   49.0.3: `p1.rs:625-694`; main `2d9c19b`: `p1.rs:625`, unchanged). The host's error becomes
   the guest's errno through wasmtime's table. On Linux and macOS, `write(2)` on a descriptor
   opened only to read is `EBADF`. On Windows, `WriteFile` on a handle without write access is
   `ERROR_ACCESS_DENIED`, which wasmtime maps to `ErrorCode::Access`, preview1's `EACCES`, 2
   (49.0.0 and 49.0.3: `crates/wasi/src/filesystem.rs:434`). The write is refused on every
   host; only the number differs. `fd_read` is built the same way (49.0.3: `p1.rs:1665-1720`),
   so a read through a descriptor opened only to write should answer `EACCES` on Windows too
   (INFERRED; criterion 5 observes it).

   wasmtime's preview2 `write` does check, and answers `NotPermitted` on a read-only grant
   (49.0.0: `crates/wasi/src/p2/host/filesystem.rs:141`). The runner uses preview1.

2. **"through a link in the grant": the check's Windows branch was a guess, and the product
   already agrees** (READ). The check makes the link `escape` only on POSIX, so on Windows the
   row opens a missing path for writing. wasmtime's `open_at` refuses any create or write open
   on a read-only grant with `NotPermitted`, `EPERM`, before the host sees the path (49.0.0 and
   49.0.3: `crates/wasi/src/filesystem.rs:1003-1009`). So the answer is 63 on every host, link
   or no link. The branch `want["through a link in the grant"] = "44"` was never run on Windows
   before (the check's comment says "no link was made on Windows").

3. **The bad grant: Python collapses `..` by text before the Windows walk sees it** (READ and
   EXECUTED). With `judge`, `_walk_windows` begins with `full = os.path.abspath(path)`
   (`runner.py:1609`). On Windows that is `ntpath.abspath`, which is
   `_getfullpathname(normpath(path))` (`Lib/ntpath.py:531-534`); `normpath` drops each `..` with
   the name before it, in pure Python. `ntpath.normpath(r"D:\a\bad\new\..\x")` is
   `D:\a\bad\x` (EXECUTED on macOS; `ntpath` is the same pure-Python code on every host). The
   walk then opens `D:\a\bad`, finds `x` missing, and returns it to be made, because a root may
   be made. The POSIX walk keeps the `..`: it joins the path to the current folder without
   normalising, takes `..` on the folders it walked, and refuses a missing component followed by
   `..` as "does not exist" (`runner.py:1435-1491`, the test at 1457), which is spec 017's
   recorded choice.

   **Why it is not a hole** (READ, with one INFERRED step). Win32's own path parsing also drops
   `..` by text before the file system sees a path (INFERRED from Microsoft's documented path
   normalisation; Python's `abspath` reproduces it). So the folder the Windows walk judges is the
   folder the spelling means on Windows. The walk holds a handle on each component, without
   `FILE_SHARE_DELETE`, refusing any reparse point (`runner.py:1608-1641`). wasmtime is given the
   walked path, not the caller's spelling (`wasi.preopen_dir(p.walked.path, …)`,
   `runner.py:2455`). Every rule compares identities on the walked chain (`_judge`), and a root
   still to be made is judged on its deepest existing ancestor's chain. Before the guest runs,
   `_check_preopens` compares the folder wasmtime opened with the walked one (`runner.py:2054`).
   So `root=<module cache>\new\..\made` is still refused, as inside the module cache: the
   collapse changes which spelling is accepted, never which folder is judged. What is wrong is
   the parity: Linux and macOS refuse the spelling, Windows grants the folder, and the guest ran
   ("before any work" was not kept).

4. **The rename: wasmtime 49.0.0 on Windows renames a file named with a trailing slash; the
   guard does not** (READ, and EXECUTED there). The loop's third rename is `f/` to `e`, where `f`
   is a file. On a call without mounts the guard shadows `path_rename` (spec 048): a path ending
   in `/` needs a folder source, judged by `path_filestat_get` without following, else `ENOTDIR`
   (`mounts.py:1938-1985`). That is wasmtime 49.0.3's rule, which checks on every system but
   Linux (49.0.3: `crates/wasi/src/filesystem/primitives/via_parent/rename.rs:25-27, 55-60`).
   wasmtime 49.0.0, which today's native linker runs, strips the slash and re-appends it only
   under `#[cfg(unix)]` (49.0.0: the same file, lines 22-26 and 33-42; `strip_dir_suffix`,
   `primitives/windows/fs/dir_utils.rs:50-58`); on Windows it renames by `std::fs::rename` with
   no kind check (`primitives/windows/fs/rename_unchecked.rs`). So natively `f` becomes `e`. On
   the next turn `d/` to `e` renames the folder over the file `e`, which Windows allows (spec
   058's cause, EXECUTED there); from then on `f/` is missing, `ENOENT`, 44, every turn. The
   loop ORs every errno, so the native ending is 44 and the guard's is 54 (the path to 44 is
   INFERRED; the two endings are EXECUTED there). The fuel is equal because host calls spend no
   guest fuel and each forward's allowance is set back (spec 048). On Linux and macOS, 49.0.0's
   re-appended slash makes the kernel answer `ENOTDIR`, so there both endings are 54.

   The product is right on Windows: it answers `ENOTDIR`, as Linux, macOS and wasmtime 49.0.3
   do. The check's reference, wasmtime 49.0.0 on Windows, is the one that differs.

## Terms

- **The walk.** The runner's check of a host path before any work (spec 017, Decision 4):
  `_walk_posix` or `_walk_windows`, one component at a time.
- **Per system.** A value chosen by `sys.platform` (`linux`, `darwin`, `win32`), as spec 058's
  `WRITE_BY_SYSTEM` does; a system the table does not name raises `KeyError`.
- **Native, guarded.** In the rename check, the same store run on today's linker
  (`linker.define_wasi()`, wasmtime 49.0.0 alone) or on the guard's linker (spec 048).
- **The verify step.** The release workflow's step "The v1.1 to v1.4 checks on these bytes",
  in job `verify (windows-2025)` and its two siblings; it runs a fixed list of files.

## Decisions

1. **The Windows walk takes `..` on the folders it walked, as the POSIX walk does (a product
   change).** With `judge`, `_walk_windows` no longer collapses the path by text. It walks the
   caller's components in order: an empty or `.` component is skipped; `..` closes the handle of
   the last folder walked and drops it from the chain, and at the drive's root it stays there,
   as POSIX's `..` at `/` does; any other name is opened as today. A `..` after a component
   that does not exist is refused, "does not exist", whether the path is a root or a grant,
   exactly as `_walk_posix` refuses it (`runner.py:1457`). A file followed by `..` is refused,
   "is not a folder", as on POSIX, because the file is opened before the `..` is taken.
   - **Why this is exact.** A judged Windows walk refuses every reparse point (spec 017,
     Decision 4). So a `..` can only follow a real folder that the walk opened and holds, and
     taking it on the walk gives the same folder as dropping it by text. The two differ only
     where the name before `..` is missing, is a file, or is a link or junction: POSIX refuses
     the first two, and Windows' own rule refuses the third. After this change Windows refuses
     all three. It never accepts a spelling Linux or macOS refuses, and it accepts every
     spelling it accepted before that names only real folders.
   - **Why not refuse every `..`.** The POSIX walk accepts `base/sub/../x` when `sub` is a real
     folder, and the README promises nothing else. Refusing every `..` would change Linux and
     macOS, and a Windows-only refusal would be a new difference. The rule here is spec 017's,
     on every system.
   - **Where the start comes from.** The path is made absolute without dropping `..`: an
     absolute tail starts at its drive's root (a letter or a UNC share, as today); a relative one
     starts at the current folder of its drive, `ntpath.abspath(drive or ".")`, which holds no
     `..`. Only that start is ever normalised.
   - `_walk_windows` uses `ntpath` by name rather than `os.path` (on Windows they are the same
     module), so its parsing runs, with a stand-in for `_win_open`, on every system
     (criterion 1).
   - The walk without `judge` (the runtime's own folders, every link followed through
     `os.path.realpath`) is unchanged.

2. **The bad grant is a parity defect, not a hole; it still blocks spec 063 and 0.1.0.** The
   cause above says why no folder outside what the spelling names can be granted and no rule is
   skipped. It still matters: an embedder's spelling is refused on two systems and granted on
   the third, and a guest ran where the check promises none would. It is fixed in the product,
   not stated per system, because §6.3 asks for one behaviour on every host and spec 017 already
   decided which.

3. **"through a link in the grant": the check's Windows branch goes; the row is 63 everywhere.**
   The product already answers `EPERM` on every host, for the reason cause 2 gives. The branch
   was the check's own error, never run before spec 063. Deleting it makes the check stricter:
   one value on every system. The link itself is still made only on POSIX (making one on Windows
   needs a privilege a user may lack), so on Windows the row asserts that a write open under a
   missing path in a read-only grant is `EPERM`. The assertion that the folder outside stays
   empty holds everywhere, as today.

4. **"write a read descriptor": stated per system (c), not relabelled (b).** The table holds 8
   on `linux` and `darwin` and 2 on `win32`, with the cited wasmtime fact beside it. The README
   says it (Decision 6). The facts go to a new upstream facts sheet (Decision 6). Relabelling was
   weighed first, since a guest's code should behave the same on every host, and refused:
   - **It is exact but not cheap.** A relabel is exact: on an `EACCES` from a forwarded write,
     ask `fd_fdstat_get`, and if the descriptor lacks `FD_WRITE` (wasmtime clears it for a file
     opened without write, `p1.rs` `fd_fdstat_get`), answer `EBADF`. But it needs `fd_write` and
     `fd_pwrite` shadowed on every call, so every write the guest makes crosses into Python
     first; and its twin (a read through a write-only descriptor) needs `fd_read` and
     `fd_pread` shadowed, the calls every import makes on the stdlib zip. That is a host
     round trip on the guest's hottest calls to change one error number.
   - **Python code does not reach it.** CPython's file objects refuse a write on a file opened
     to read, and a read on one opened to write, with `io.UnsupportedOperation`, before any
     call (`Modules/_io/fileio.c:878-880, 939-941`). Only `os.write` or `os.read` on a raw
     descriptor of the wrong mode meets the host's number, and either way it is refused.
   - **The precedent.** Spec 058, Decision 1: a grant is the host's folder as the host keeps it;
     a Windows difference is documented, not shadowed. Here nothing on the host differs; only
     the host's error does, and it is wasmtime's own mapping, unchanged in 49.0.3 and on main.
   - The twin is observed here (criterion 5), so the README states both from evidence.

5. **The rename check: the guard's ending is asserted on every host; today's native ending per
   system (c, a fact about the reference).** The check's purpose, fuel neutrality, is kept
   whole: fuel equal at every cap, on every host. Its endings become:
   - the guarded loop ends `returned ENOTDIR` on every host (the product's rule; new: today this
     is asserted only through equality with native);
   - the native loop ends as the guarded one on `linux` and `darwin`, and `returned ENOENT` on
     `win32` (wasmtime 49.0.0's Windows rename, cause 4);
   - at each cap the two runs are equal in fuel and ending, except that on `win32` a loop that
     completes ends with those two values.

   The fact goes to facts sheet 12 as fact 5: wasmtime 49.0.0 renames a file named with a
   trailing slash on Windows; 49.0.3 refuses it with `ENOTDIR`; the guard carries 49.0.3's rule,
   so the runner already answers as 49.0.3 does. When `uv.lock` moves to a wasmtime-py on
   49.0.3 the guard goes (spec 048), today's native linker then answers 54 on Windows too, and
   the `win32` value fails the check, which then loses it, with a reason.

6. **Docs and facts sheets.**
   - README, *Grants*: the walk paragraph says `..` is taken on the folders walked, so a `..`
     after a missing folder or a file is refused on every system. *What grants do not do* gains:
     a write through a descriptor opened only to read, or a read through one opened only to
     write, is refused on every system; the error is `EBADF` on Linux and macOS and `EACCES` (a
     `PermissionError`) on Windows, the host's own answer, which wasmtime passes on; Python's
     file objects refuse both before the call. (If criterion 5 shows the read twin otherwise on
     Windows, the README says what it showed.)
   - CHANGELOG, under `0.1.0a7 — unreleased`: one entry, "On Windows, a grant or `root` with
     `..` after a missing folder or a file is refused, as on Linux and macOS" and the documented
     errno.
   - `context/upstream/12-wasmtime-py-on-wasmtime-49-0-3/facts.md`: fact 5, cause 4 with its
     citations and the runs that showed it.
   - `context/upstream/20-wasmtime-preview1-write-on-a-read-descriptor/facts.md`, a new facts
     sheet in the house form (Project, Against, Status: drafted, Title, Files, why), and its row
     in `context/upstream/README.md`: preview1's `fd_write` and `fd_read` check neither the
     grant's permissions nor the open mode, so the host's error reaches the guest; `EBADF` on
     Unix, `EACCES` on Windows; preview2 checks. The owner decides whether to ask wasmtime for
     `EBADF` everywhere; Wasmtime's AI tool policy (facts sheet 12) keeps agents from posting.

7. **How it runs on Windows before review: one temporary commit on this branch.** Since spec 063
   is not on main, main's verify step runs a fixed file list that leaves out
   `tests/checks/test_v1_2_hostile_guest.py` and `tests/unit/test_runner_mounts.py`. The route:
   - Criteria 1, 2 and 5 are in `tests/unit/test_runner_grants.py`, which the verify step already
     runs on all three systems. They need nothing more.
   - For the other checks, the builder adds one commit, last on the branch, that appends four
     node ids to the verify step's list:
     `tests/checks/test_v1_2_hostile_guest.py::test_a_read_only_grant_refuses_every_write`,
     `tests/checks/test_v1_2_hostile_guest.py::test_a_bad_grant_is_refused_before_any_work`,
     `tests/unit/test_runner_mounts.py::test_the_rename_rule_forward_is_fuel_neutral`, and
     `tests/unit/test_runner_mounts.py::test_the_rename_ends_are_stated_per_system` (criterion
     6's new unit case). Not whole files: on main, other rows of the hostile-guest file fail on
     Windows for reasons spec 063 handles (its "descriptor limit" need), and they are not this
     spec's.
   - The builder pushes the branch (question 98's answer allows it) and runs `gh workflow run
     release.yml --ref spec/076-the-grant-checks-agree-on-windows`, waits for every job, and
     records the run id, the head commit and the per-system verdicts.
   - Then, on a clean tree (`git status` empty), the builder drops the temporary commit (`git
     reset --hard HEAD~1`, `git push --force-with-lease`). The landing notes record its hash and
     its diff, a few lines of one step, so the reviewer can see exactly what ran.
   - **Why this route.** The coordinator allows building on top of 063's branch, once 063 is
     rebased onto main, if that is simpler. It is not simpler here. The temporary commit runs
     exactly the failing checks, on the exact source the review will see, on main's own
     workflow, in one dry run. Stacking on 063's branch would put 063's harness, still in
     review, under this spec's evidence, and its branch would carry 063's commits, which must
     land after 076 (Decision 8). If the temporary route cannot run a row honestly (for
     example, main's harness blocks it on Windows for a reason 063 fixes), the builder stacks
     076 on 063's rebased branch for that one dry run instead, says so in the landing notes,
     and 076 still lands first, from its own branch. A permanent change to the verify step was
     refused: it makes this spec build-class, and 063 rewrites that job into shards
     within days. A `workflow_dispatch` input does the same as the temporary commit with more
     lines.

8. **The landing order.** 076 lands first, on its own. Then 063 rebases onto main and its next
   branch dry run is the full confirmation: its shards run every product-check file on Windows,
   including the rows of these checks that have never run there. 0.1.0's release dry run
   (AGENTS.md rule 6b) needs both.

9. **Every row that has never run on Windows must run green there, and is this spec's to fix;
   none is skipped** (spec 063's build review, F4). The bad-grant check stops at its second
   `refused` today, so these security refusals have never run on Windows: a writable grant that
   holds the module cache; a root that holds the artifact set; a root at the temporary folder (or
   the stdlib folder in it); a read-only grant of the temporary folder; a root at a moved
   temporary folder; writable grants of wasmtime-py's code, the host Python's `stdlib` and its
   `Scripts\` folder (and the read-only grant of `stdlib` that must stay allowed); a root still to
   be made above a cache still to be made (and the cache the only folder made); a read-only grant
   inside a writable one; two grants at one guest path; a missing grant; the two type checks; a
   root inside the module cache (and no folder made); the same root spelled with its case
   swapped, a row that exists for `win32`; and the final `calls == []`. The memo §7a link row is
   POSIX-only by design (on Windows a judged walk refuses every reparse point, whoever made it,
   which `test_a_junction_is_refused_on_windows` already checks in the verify step) and stays
   so. The rename check's loop over caps, and
   its `ENOTDIR` assertion, have never run on Windows either.

   If the dry run shows one of them failing, the builder decides it here by the same order: a
   product change if a guest or an embedder would see a different outcome, above all if a
   refusal does not happen; a per-system value only with a cited wasmtime or Windows fact. It is
   fixed and run again, never skipped, marked, or moved to make the run green. A failure that
   needs a design of its own is written down (AGENTS.md rule 7), and this spec, and so 063, waits
   for it.

## Intent

Make the four Windows failures pass for the right reasons: the product refuses a bad grant
spelling on every system, each check asserts one value where the product has one, and the two
places where Windows answers with another number are stated per system, with wasmtime's own
source as the reason and the README saying so.

## Design

- `src/wasi_python/runner.py`, `_walk_windows(where, path, judge, may_make)`, with `judge`:
  - start: `drive, tail = ntpath.splitdrive(path)`; if `tail` starts with `\` or `/`, the start
    is `drive + "\\"`; otherwise it is `ntpath.abspath(drive or ".")`, whose own components are
    walked from its drive's root;
  - components: `re.split(r"[\\/]", tail)`, walked in order with a list of held handles,
    identities and names that `..` pops (never below the start's root);
  - a missing component: if anything after it (empty and `.` skipped) is `..`, or `may_make` is
    false, raise "does not exist"; else return it as `missing` with the rest, as today;
  - every other line of the function (the reparse-point refusal, "is not a folder", the held
    handles, `_Walked`) is unchanged. Without `judge`, `full = os.path.realpath(path)` as
    today. `ntpath` by name throughout.
- `tests/unit/test_runner_grants.py`:
  - **new** `test_the_windows_walk_takes_dot_dot_on_walked_folders`: on every system, with
    `runner._win_open` and `runner._close_held` replaced by a stand-in over a small in-memory
    tree of Windows paths (folders, one file, one reparse point; identities `(1, n)`), and the
    current folder fixed; rows in criterion 1. It asserts the handles held at the end, so a `..`
    that leaks a handle fails.
  - `test_the_walk_judges_links`: new rows on the real file system, every system: `new/../x` as
    a root (`may_make`) and as a grant, "does not exist"; `file/../x`, "is not a folder";
    `sub/../x` with `sub` and `x` real, walked to `x`'s identity.
  - `test_a_read_only_grant_refuses_raw_writes`: `fd_write` through the read-only grant's
    read descriptor, before the renumber, answers `{"linux": 8, "darwin": 8, "win32": 2}` per
    system; `fd_read` through a descriptor of the writable grant opened write-only answers
    `{"linux": 8, "darwin": 8, "win32": 2}`; the file is unchanged. The module `RAW` gains a
    `read` export over `fd_read`.
- `tests/checks/test_v1_2_hostile_guest.py`:
  - `test_a_read_only_grant_refuses_every_write`: `want["write a read descriptor"]` per system
    as above; the `os.name != "posix"` branch deleted; the docstring names both facts.
  - `test_a_bad_grant_is_refused_before_any_work`: after the root row, `assert not (base /
    "x").exists()`; a grant row `Grant(base / "new" / ".." / "shared", "/s")`, "does not
    exist"; a root row `base / "shared" / "data" / "f.txt" / ".." / "y"` with a file made there,
    "is not a folder"; and `root=cache / "new" / ".." / "made"`, "does not exist" (before the
    fix on Windows this one is refused as inside the module cache, which is the evidence for
    Decision 2; after it, "does not exist" on every system).
- `tests/unit/test_runner_mounts.py`:
  - `NATIVE_RENAME_END = {"linux": f"returned {ENOTDIR}", "darwin": f"returned {ENOTDIR}",
    "win32": f"returned {ENOENT}"}` with a comment citing cause 4;
  - `test_the_rename_rule_forward_is_fuel_neutral`: the guarded loop at full fuel ends
    `returned {ENOTDIR}`; the native loop's ending is `NATIVE_RENAME_END[sys.platform]`; the
    fuel is equal; at each cap, fuel equal and endings equal, except a completed loop, whose two
    endings are those values;
  - **new** `test_the_rename_ends_are_stated_per_system`, parametrized over the three systems,
    needing no wasmtime: the table names each, `freebsd` raises `KeyError`, and only `win32`
    differs from the guard's ending.
- `README.md`, `CHANGELOG.md`, `context/upstream/` as Decision 6 says.

## Scope

In: `_walk_windows`'s `..`; the three checks; three unit cases; the README, CHANGELOG and the two
facts sheets; one Windows dry run with a temporary commit. Out: any shadow of `fd_write`,
`fd_pwrite`, `fd_read` or `fd_pread` (Decision 4); the POSIX walk; a Windows link in the
read-only check; Win32's other path rewrites (trailing dots and spaces, `\\?\` paths), which the
identity check already covers and no check shows wrong; any change to the workflow that lands;
063's own Windows rows (the descriptor limit and the rest it handles).

## Acceptance criteria

Each check is seen failing first, before the code it guards, and against each stand-in named.
Stand-ins are made in the worktree, run, and restored; their output goes to `build/076-*.log`.

1. `test_the_windows_walk_takes_dot_dot_on_walked_folders` passes on macOS and Linux (and on
   Windows in the verify step). Rows: root `C:\b\new\..\x` with `may_make`, "does not exist";
   grant `C:\b\new\..\x`, "does not exist"; `C:\b\f.txt\..\x`, "is not a folder";
   `C:\b\sub\..\x`, walked to `x`'s identity with handles held on `C:\`, `b` and `x` only;
   `C:\..\b`, walked to `b`; `C:\b\link\..\x` with `link` a reparse point, "passes through a
   link or junction"; `C:\b\new\deeper`, `missing == ("new", "deeper")`; a relative `sub\x`
   from the fixed current folder `C:\b`, walked to `x`. Seen failing before the change (the
   rows that collapse). **S1:** a `_walk_windows` that collapses the path with `ntpath.normpath`
   first: fails, naming `new\..\x`. **S2:** a walk that refuses every `..`: fails on
   `C:\b\sub\..\x`. **S3:** a `..` that does not close its handle: fails on the held handles.
2. `test_the_walk_judges_links`' new rows pass on macOS and Linux (and on Windows in the verify
   step). **S4:** `_walk_posix` that applies `os.path.normpath` to the joined path first: fails
   on macOS, naming the `new/../x` row.
3. `test_a_bad_grant_is_refused_before_any_work` passes on macOS and Linux, and on Windows in
   the dry run (criterion 9), **every row of it**: the dry run's log shows the check passed on
   `verify (windows-2025)`, which means each refusal Decision 9
   lists ran and refused there, and `calls == []` held. The `cache/new/../made` row is the one row whose message changes
   on Windows with the fix. **S5:** S4's stand-in again: the root row fails on macOS ("DID NOT
   RAISE"), and `base/x` is made.
4. `test_a_read_only_grant_refuses_every_write[plain]` and `[snapshot]` pass on macOS and Linux,
   and on Windows in the dry run. **S6:** a stand-in that selects the `win32` values on macOS:
   fails naming "write a read descriptor". **S7:** the deleted branch put back, unconditioned:
   fails naming "through a link in the grant".
5. `test_a_read_only_grant_refuses_raw_writes` passes on macOS and Linux, and on Windows in the
   verify step, where it is the first observation of the read twin. **S8:** S6's selection
   again: fails on macOS naming the write row.
6. `test_the_rename_rule_forward_is_fuel_neutral` and `test_the_rename_ends_are_stated_per_system`
   pass on macOS and Linux, and on Windows in the dry run, with the loop over caps run whole
   there (from 1 up to past the need). **S9:** a stand-in that selects the
   `win32` native ending on macOS: fails. **S10:** a guard whose `_source_type` answers 0 for a
   file, so `f/` is renamed: the guarded ending is not `returned 54` and the check fails on
   macOS.
7. The README, the CHANGELOG entry, facts sheet 12's fact 5, facts sheet 20 and its row, as
   Decision 6 says.
8. In the worktree, without `--accept`: the fast tier while building, then the full judge with
   `-n 6` before "built": no pass lost, nothing grows, the judge change named
   (`tests/checks/test_v1_2_hostile_guest.py`, `tests/unit/test_runner_grants.py`,
   `tests/unit/test_runner_mounts.py`); `ruff check` and `ruff format --check` green;
   `tests/public_api.txt` unchanged.
9. **On Windows:** one release dry run on this branch with Decision 7's temporary commit, every
   job passed on all three systems; criteria 1 to 6's checks among the passes on
   `verify (windows-2025)`. The run id, its head commit, the temporary commit's diff and its
   removal are in the landing notes. A failure there is decided by Decision 9, fixed in this
   spec, and run again; no check, row or cap is skipped, deselected or allowed to fail.
10. After landing (063's, not this spec's): 063's next branch dry run passes
    "judge (windows-2025, own-guest)" with these checks, on main with 076.

## Landing notes

Not built.
