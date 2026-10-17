# 017 — Typed grants

- **Status:** landed 2026-10-17. Reviewed before build
  (`../reviews/017-typed-grants-spec-2026-10-17.md`) and after
  (`../reviews/017-typed-grants-2026-10-17.md`, with its confirmation).
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`, `src/wasi_python/__init__.py`), the judge's
  reference embedder (`tests/harness/guest.py`), judge additions and changes in `tests/`, the
  release workflow's `verify` file list, `README.md`, `CHANGELOG.md`, `context/constitution.md`
  (§4.15's alpha exception ends).
- **Depends on:** 006 (private roots), 013 and 014 (arguments checked before any work), 015
  (`run_async` takes `run`'s arguments), 016 (lock files beside private folders, the sweep, and
  its `_LOCK_NAME`, which this specification extends).
- **Research it stands on:** `context/research/2026-10-17-typed-grants.md` (section 7b is the
  identity check; its probe is saved in `context/research/2026-10-17-typed-grants/`), and the
  pre-build review's probes. The owner's answers: question 1 (typed grants, which may be none),
  question 2 (matplotlib's data as a read-only grant), question 3 (§4.15 is binding), and the
  alpha exception of 2026-10-17. Question 24 (a stricter default) is open and does not block:
  this specification changes no default.

## The problem

- A guest sees one host directory, `root`, writable, at `/`. An embedder cannot say "read-only",
  nor hand over a separate output folder. The agent-runtime study ranks this first
  (`2026-10-17-the-runtime-for-agent-code.md`, §5 item 1).
- The stdlib zip sits inside that writable root. A guest can change it, and a reused root hands
  the change to the next call; the runner re-copies it before each call to undo that. §4.15
  allows this only as an alpha exception, which ends with this specification.
- Copying the zip costs every call without a root about 7 ms and 11 MB of disk (memo §5,
  EXECUTED; benchmark facts).

## Decisions

1. **`Grant` and `grants=`.**
   - `Grant(host, guest, *, writable=False)`, a frozen dataclass exported from `wasi_python`.
     `host` is a `str` or `os.PathLike[str]` (never `bytes`); `guest` a `str`; `writable` a real
     `bool` (`"no"` is refused, not truthy). A grant is read-only unless it says
     `writable=True` (§4.15).
   - `run(..., root=None, grants=(), ...)`, and `run_async` alike. `grants` is any iterable of
     `Grant` except a `str`; `_checked` turns it into a tuple, so `run_async` hands the worker
     the checked tuple, never a used iterator.
   - `root`: `None` is a fresh private writable root at `/` (unchanged); a path is that host
     directory, writable, at `/` (unchanged in meaning, now checked like a writable grant,
     Decision 4); `False` means no root, so the guest sees only its grants. `True` and `bytes`
     are refused with `TypeError`.
   - A read-only grant is `preopen_dir(host, guest, fs_mutable=False)`, which wasmtime enforces
     with `EPERM` on every write-type call (memo §1; the pre-build review re-ran it on both
     binaries).
2. **The zip moves to a read-only folder at `/usr/local/lib` (§4.15's exception ends).**
   - **One folder per zip, per process.** For each distinct zip (its SHA-256, as
     `_place_checked` checks it today) a process makes one private folder,
     `wasi-python-zip-<16 hex>`, with its lock file beside it (spec 016's `_Private`; spec 016's
     `_LOCK_NAME` becomes `wasi-python-(root-|zip-)?[0-9a-f]{16}\.lock`, so a killed process's
     copy is swept). It holds `python315.zip` alone, copied once and its hash checked.
   - **Its own lock.** The copy runs under `_zip_lock`, not `_lock`, which the epoch ticker
     takes every round.
   - **Checked before each call.** The copy's stamp (size, `mtime_ns`, `ctime_ns`, device,
     inode) is compared with the one recorded; any change re-copies it and checks its hash.
   - **Removed at exit.** `_release` (atexit) removes each zip folder through `_Private.remove`.
   - **Granted on every call**, on both binaries, as a read-only grant at `/usr/local/lib`,
     first among the preopens.
   - **The root keeps its folders.** For a root, the runner still makes real folders
     `usr/local/lib` inside it, as `_place_stdlib` does today, but writes no zip there: without
     them `/usr` would vanish from a fresh root's listing, and `realpath` of the zip's path could
     lead into a file a guest wrote in a reused root (the review, EXECUTED both). A root's
     `usr/local/lib` is hidden behind the grant for every path a program spells normally (memo
     §2).
   - **An old zip is ignored.** A `python315.zip` that 0.1.0a2 left in a reused root is never
     read again; the CHANGELOG says it may be deleted.
   - The snapshot needs no rebuild (memo §3; review: imports reach the grant, never a root's
     zip). §4.15's alpha exception paragraph is removed from the constitution, and the README's
     "Not protected" entry for the zip goes.
3. **`HOME` and `TMPDIR`.** `TMPDIR` stays `/tmp`. `HOME` is made fresh, as today, in the
   folder the guest sees at `/tmp`:
   - a writable grant at `/tmp`, if there is one (with or without a root; the grant hides the
     root's own `tmp`, so making `HOME` there instead would point at nothing, as the review ran);
   - otherwise the root's `tmp`, if there is a root;
   - otherwise nowhere: `HOME` is left out of the environment, and Python's own error says so to
     a program that needs it.

   With `root=False`, `/` does not exist and relative paths fail (memo §4).
4. **Every grant, and `root`, is checked before any work** (`TypeError` for a wrong type,
   `ValueError` for a value, as specs 013 and 014; messages name the grant's position and guest
   path):
   - **The guest path** is a `str`, absolute, with no NUL, no empty, `.` or `..` component and no
     trailing `/`; not `/` (that is `root`); not `/usr/local/lib` or under it. No two grants
     share a guest path. Nested guest paths are allowed.
   - **The walk.** Each host path, `root` included, is opened one component at a time from `/`
     (POSIX: `os.open(component, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC,
     dir_fd=parent)`), and the final descriptor is kept until Decision 5's comparison. Each
     component is first `lstat`ed through `dir_fd`: on macOS `O_NOFOLLOW` on a link fails with
     `ENOTDIR`, not `ELOOP`, so links are recognised by `lstat`, never by the error. A component
     that is a link is followed only if the directory that holds it is one this user cannot write
     (`os.access(parent, os.W_OK, effective_ids=True)` where supported, else `os.access`); its
     target is walked by the same rule, at most 40 links in all. Otherwise the call raises
     `ValueError`. On POSIX, links in directories other users own (the system's, such as macOS's
     `/var -> private/var`) are followed: a guest writes as this user, so only a link in a
     directory this user can write could be a guest's (memo 7a). On Windows, where CPython's
     `os.access(dir, W_OK)` is always true, every link and junction on the way is refused.
   - **A root that does not exist** is made, as today, but only after every rule has been
     decided on its existing chain: the deepest existing ancestor is walked by the rule above; a
     root still to be made counts as inside whatever that ancestor is inside, and above nothing
     (so `root=~/newproj` is not "above" the module cache); if no rule refuses, each missing
     component is made with `os.mkdir(name, dir_fd=parent)` and walked. A refused root makes no
     folder. A grant's host path must exist. **Amended by the build review (finding 1):** "above
     nothing" holds only if every runtime folder exists when judged, so the runner makes the
     module cache, if it can, before it walks `root`; a missing root at or above a missing cache
     is then judged to hold it.
   - **Identity, not spelling.** Every comparison below uses `(st_dev, st_ino)` of the walked
     directories and their ancestors, never path strings: macOS folders are case-insensitive, so
     `~/LIBRARY/CACHES` is `~/Library/Caches` (the review, EXECUTED).
   - **Read-only means read-only here.** A read-only grant whose directory is, or is inside, a
     writable grant's (`root` counts) is refused. A writable grant inside a read-only one is
     allowed.
   - **The runtime's files are out of reach.** A writable grant, `root` included, that is, is
     inside, or is above the zip folder, the artifact directory or the module cache is refused.
     The protected folders may not exist yet (a fresh machine has no module cache, and the zip
     folder is made at the first call): each one's chain of identities starts at its deepest
     existing ancestor (for the zip folder, the temporary folder itself), resolved following every
     link, and a protected folder's own walk never refuses. So `root=Path.home()` is refused on a
     fresh machine too, before the runner would make its module cache inside that root.
     **Amended by the build review (findings 2 and 4):** the runtime's folders also include the
     code of `wasi_python` and wasmtime-py (a guest that rewrote them would run in the next host
     process) and the folders of each of the artifact set's files; and any grant, read-only too,
     at or above the temporary folder is refused, since that folder holds every call's private
     root and `stdin`.
     This now refuses some `root=` values that worked before: the home folder, a project folder
     holding `.venv` or `build/artifacts`, and the temporary folder itself. Each could let a guest
     change files the next call trusts; the CHANGELOG names it as a change.
5. **Each grant is checked again after it is opened.** wasmtime opens each host path itself
   inside `preopen_dir`. The runner passes the path its walk resolved, and then, inside `_drive`,
   before the guest is instantiated, runs a check module of its own in the call's store (three
   WASI imports, `fd_prestat_get`, `fd_prestat_dir_name` and `fd_filestat_get`, compiled once per
   engine). For each preopen `3 + i` it confirms the guest name and reads the `ino` wasmtime
   reports, and compares it with the hash of the walk's own descriptor:
   - **POSIX:** SipHash-1-3, zero keys, over `(st_dev & (2**64 - 1), st_ino)` packed as two
     native-endian 64-bit words (`struct.pack("=QQ", …)`; Rust sign-extends a negative `dev_t`,
     hence the mask).
   - **Windows:** Python cannot open a directory with `os.open`, so the walk opens every
     component, root to last, through `CreateFileW` with `FILE_FLAG_BACKUP_SEMANTICS |
     FILE_FLAG_OPEN_REPARSE_POINT`, refuses one that is a reparse point (a link or a junction),
     and holds each handle with `FILE_SHARE_READ | FILE_SHARE_WRITE` but not `FILE_SHARE_DELETE`
     until the comparison. While they are held, no walked folder can be renamed, removed or
     replaced, so no path string is compared (8.3 short names, `\\?\` prefixes, `subst` and
     mapped drives cannot cause a false refusal). The handles are closed after the comparison,
     and before a private root is removed. The hash is over `(dwVolumeSerialNumber,
     nFileIndexHigh << 32 | nFileIndexLow)` from `GetFileInformationByHandle` on the last handle,
     which is what wasmtime hashes (`filesystem/windows.rs:85-91`, READ).
   - A mismatch raises `RuntimeError("grant <n> at <guest> changed between its check and the
     call")` before the guest runs. A deadline that has already passed traps the check module
     with `INTERRUPT`, which the call reports as `"deadline"`, never as a refusal.
   - A swap of a middle component after the walk changes what wasmtime opens but not the walk's
     descriptor, so it shows as a mismatch (the review, EXECUTED: a check against a final-only
     `O_NOFOLLOW` open passed such a swap; the walk's descriptor catches it).
   - **Pinned on every OS.** A unit test compares the runner's hash with the `ino` a store
     reports for a scratch folder; the `verify` job runs it on Linux, macOS and Windows, so a
     wasmtime that hashes differently, or a platform the formula misses, fails there first, and
     at run time every grant is refused, loudly.
6. **The embedder contract changes in one line.** README, "Any other embedder", step 1: preopen
   the artifact set's zip, read-only, in a folder at `/usr/local/lib`, plus whatever the embedder
   grants, possibly nothing. The judge's reference embedder, `tests/harness/guest.py`, changes to
   do exactly that, and its docstring says so.
7. **The README gains:** `..` never crosses from one grant into another; a grant does not appear
   in a listing of its parent; a read-only grant can still change if the same host files are
   writable elsewhere (outside this call); a SQLite database in a read-only grant opens only
   through a URI that takes no lock; and a folder reachable by two routes (a bind mount, a second
mount of one share) is judged by the route the embedder gives, so a read-only grant by one route
does not stop a writable grant of the same files by another (each is checked against the
runtime's files and the other grants by identity, which a bind mount shares, but a network
share's second mount may not).
8. **Checks.** Each counts; none measures time. Each new one is seen failing first.
   - New:
     - v1.2, `test_a_read_only_grant_refuses_every_write[call]`, both binaries: every row of memo
       §1's table and the review's extra rows (`fd_allocate`, `fd_renumber` onto a grant's file,
       `os.replace` across grants, `shutil.move`'s copy into a read-only grant, a link inside the
       grant), through Python and the raw WASI call; `EPERM`, and the host bytes and listing are
       unchanged.
     - v1.4, `test_grants_reach_the_guest_in_any_order`: five grants, read-only and writable,
       nested and not, in shuffled orders (a fixed seed), both binaries.
     - v1.4, `test_no_root_and_no_grants_runs`, and `test_home_follows_a_writable_tmp_grant`
       (with and without a root: `os.path.isdir(os.environ["HOME"])`).
     - v1.2, `test_the_zip_is_read_only_and_shared`, in a child process with its own
       `tempfile.tempdir`: a write to `/usr/local/lib/python315.zip` is `EPERM`; a root holds no
       zip after a call; two calls copy it once; a copy changed on disk is replaced before the
       next call; the folder is gone after the child exits.
     - v1.2, `test_a_bad_grant_is_refused_before_any_work`: one case per rule in Decision 4,
       including a link in a middle component in a writable folder, a case-changed spelling of
       the module cache's parent, `root=True`, `writable="no"`, `bytes` paths, and the memo's 7a
       reproducer.
     - v1.2, `test_a_swapped_grant_is_refused` (POSIX): a real swap of a middle component between
       the walk and the preopen, made through a test seam that runs code at that instant; the call
       raises `RuntimeError` and a door host that counts calls stays at 0.
     - Unit, `test_the_grant_identity_matches_wasmtimes`, in `tests/unit/test_runner_grants.py`,
       which `verify`'s file list gains; on Windows it includes a grant under the real temporary
       folder (the runners' `%TEMP%` may be an 8.3 short name), which must not be refused.
   - Changed (a judge change under `--accept-judge`, AGENTS rule 4; each keeps what it guards: the
     guest's write is refused, the next call works, nothing outside is written):
     - `test_runner_keeps_the_artifact_zip_out_of_the_guests_reach`: the vandal's write is now
       refused with `EPERM`, and the next call imports from the grant.
     - `test_runner_never_follows_a_link_a_guest_left[the zip]` and `[its directory]`: removing or
       renaming the zip or its folder through `/usr/local/lib` is refused; the guest then makes the
       same links through `/usr/./local/lib`, which reaches the root's own folder; the next call
       works, never follows them, and the folder `outside` stays empty.
     - `test_runner_replaces_a_directory_left_in_the_zips_place`: the guest cannot leave one; the
       check asserts the refusal and that a root's `usr/local/lib` holds no zip.
     - `test_planted_code_never_runs` (both binaries): the `/usr/local/lib/python3.X` routes are
       refused, and the same code planted through `/usr/./local/lib/python3.X` (the root's own
       folder) and the `/usr/local/bin` routes never runs.
     - `test_a_call_without_a_root_shares_nothing`: a fresh root lists `tmp` and `usr`, as now.
     - `tests/unit/test_guest.py::test_cpython_sees_only_its_root`: the harness's root keeps real
       `usr/local/lib` folders and the stdlib arrives through its own read-only preopen at
       `/usr/local/lib` (a zip, or the reference build's stdlib directory), so the root still
       lists `['data', 'usr']`; the check is unchanged.
     - The checks that list the temporary folder (the descriptor check, `CANCEL_ASYNC`,
       `shares_nothing`, and spec 016's two) set `tempfile.tempdir` in their child before its
       first call, so the zip folder is the child's own and gone at its exit, or filter the names
       `wasi-python-zip-*`; each says which.
9. **Docs.** README: `Grant`, `grants=`, `root=False`, `HOME`, the facts above, the contract
   step, and "Not protected" loses the zip entry. CHANGELOG under 0.1.0a3: typed grants; the zip
   is read-only and no longer copied into a root (an old one may be deleted); some `root=`
   values are now refused; a missing root is still made, now through the walk.

## Intent

An embedder hands a guest exactly the host folders it names, each read-only unless it says
otherwise, possibly none; the runtime's own files are read-only and out of reach; and a guest's
link or swap cannot redirect a grant to anything else.

## Design

```
src/wasi_python/runner.py    Grant; grants=, root=False; the walk and its checks; the zip folders
                             and _zip_lock; the post-preopen identity check; HOME
src/wasi_python/__init__.py  Grant exported
tests/harness/guest.py       the reference embedder follows the new contract
tests/checks/…, tests/unit/test_runner_grants.py
.github/workflows/release.yml  verify runs tests/unit/test_runner_grants.py
README.md, CHANGELOG.md, context/constitution.md (§4.15)
```

## Scope

In: the above. Out:
- An importable grant (owner question 16).
- A per-call working directory (`cwd=`): its own specification.
- `Completed.outputs`, and write-back rules such as refusing hard links (memo 7g).
- A stricter default for `run(argv)` (owner question 24).
- Building matplotlib.

## Acceptance criteria

1. The new checks exist and were seen failing before the change; each changed check's reason is
   in the landing notes.
2. `uv run pytest` is green with `--accept-judge` and `--accept-growth`: a separate preopen for
   the zip adds a little fuel to the judge's own harness calls (the review measured +0.020% on
   the snapshot and +0.0135% on the plain binary, past the ratchet's 0.01%).
3. A dry run of the release workflow passes every job, Windows' identity check included.
4. §4.15's alpha exception paragraph is gone, and the security review §5.6 requires before the
   next release reviews this change.

## Landing notes

Built 2026-10-17 by the implementer (Claude Opus 5.5) in a scratch clone of `7dc59fd` (spec 016
landed), after the pre-build review's second confirmation. **Not yet reviewed and not
accepted.** Every claim below was run (EXECUTED) on macOS arm64, CPython 3.14.2, wasmtime-py
49.0.0, with the main tree's artifact set, unless it says otherwise.

### What was built

- `runner.py`: `Grant`; `root=False` and `grants=` on `run` and `run_async`, checked in the
  caller's thread (`_check_root`, `_check_grants`, `_guest_path`, `_host_path`); the walk
  (`_walk_posix`, `_walk_windows`, `_make_missing`) and `_Walked`; the runtime's folders'
  chains (`_chain`, `_runtime_folders`); the rules (`_judge`); the zip folders (`_zip_folder`,
  `_copy_zip`, `_zips` under `_zip_lock`, removed by `_release` at exit, forgotten in a forked
  child); the identity check (`_CHECK_WAT`, `_siphash13`, `_wasi_ino`, `_check_preopens`, run in
  `_drive` before the guest is instantiated); `HOME` (`_home_folder`); a test seam,
  `_after_walk`. `_place_stdlib`, `_place_private`, `_place_checked` and their caches are gone.
  `_LOCK_NAME` takes `zip-`.
- `tests/harness/guest.py`: the stdlib (a zip, or the reference build's directory) is its own
  read-only preopen at `/usr/local/lib`, first; the root keeps real `usr/local/lib` folders.
- The release workflow's `verify` runs `tests/unit/test_runner_grants.py`.
- README (*Grants*, the runner paragraph, the embedder contract's step 1, Safety and "Not
  protected"), CHANGELOG (three entries), and the constitution: §4.15's alpha exception
  paragraph is removed and the status line says so.

### Choices the specification left to the build

- **A read-only grant at `/tmp`** hides a root's `tmp` but cannot hold `HOME`, so then there is no
  `HOME`, as with no `/tmp` at all (Decision 3 names only a writable grant).
- **`..` after a missing component of a root** (`root=new/../x`) is refused as "does not exist",
  as the kernel would answer, rather than made.
- **The zip's copy is mode 0644, not read-only:** Windows can neither replace nor remove a
  read-only file, and the guest's grant is read-only in a 0700 folder anyway.
- **The raw WASI rows** (memo §1's second table, `fd_allocate` and `fd_renumber`) are checked in
  `tests/unit/test_runner_grants.py` on a preopen made with `fs_mutable=False`, as the runner
  makes one, since the guest's Python cannot make raw calls; that file runs on all three systems
  in `verify`. The Python rows are `test_a_read_only_grant_refuses_every_write`, one guest
  program per binary.
- **The swap check on Windows** (`test_a_swapped_grant_is_refused`) cannot swap: the walk holds
  every folder, so there it asserts the rename is refused and the call reads the granted folder.
  It sits in `test_v1_2_hostile_guest.py`, which `verify` does not run, so Windows' identity check
  is exercised by the unit file and by the v1.4 grant checks, which `verify` runs.

### Seen failing first

Against `main`'s runner (`git archive` of `0ea00df`'s `src` on `PYTHONPATH`): all 18 new and
changed goal checks fail, and the unit file fails to import `Grant` (scratch
`build017/seen-failing.txt`). Against stand-ins of this runner, each one change made by text
replacement in a copy (scratch `build017/mut/run.py`, `mut/results.txt`):

| stand-in | checks that fail |
|---|---|
| no identity check | `test_a_swapped_grant_is_refused` |
| every preopen writable | the read-only check, both binaries; the zip checks; the grant checks |
| the zip folder writable | the zip checks, `test_planted_code_never_runs` |
| no rules (`_judge` skipped) | `test_a_bad_grant_is_refused_before_any_work` |
| links never judged | `test_the_walk_judges_links`, `test_a_bad_grant_is_refused_before_any_work` |
| the zip copied on every call | `test_the_zip_is_read_only_and_shared` |
| a changed copy not replaced | `test_the_zip_is_read_only_and_shared` (it first survived: the third call imported only modules the snapshot holds; the check now compares the copy's bytes) |
| `HOME` always in the root's `tmp` | `test_home_follows_a_writable_tmp_grant`, both |

A stand-in run in one pytest process cascades: a stand-in that lets one check damage the
process's shared zip folder fails later checks too. Each named check also fails alone.

### Changed checks, and why each still guards what it did

- `test_runner_keeps_the_artifact_zip_out_of_the_guests_reach`: the vandal's write is refused;
  the artifact zip is unchanged; the next call imports; a root holds no zip.
- `test_runner_never_follows_a_link_a_guest_left[...]`: the route through `/usr/local/lib` is
  refused, and the same links are planted through `/usr/./local/lib`; the next call works,
  `outside` stays empty, and the root's `usr/local/lib` is a real folder again.
- `test_runner_replaces_a_directory_left_in_the_zips_place`: the guest cannot remove the zip or
  make a folder in its place; the root's `usr/local/lib` is empty; the next call works.
- `test_planted_code_never_runs`: the `/usr/local/lib/python3.X` routes are refused, and the same
  code planted through `/usr/./local/lib/python3.X` never runs.
- The checks that list the temporary folder: the descriptor check and `CANCEL_ASYNC` filter
  `wasi-python-zip-*` while their child lives, and the descriptor check also asserts the folder
  is gone after the child exits. Spec 016's killed-process check now counts the killed child's
  zip folder among what the next process sweeps (three folders, not two), which shows the
  `_LOCK_NAME` change; the live-call check counts six entries.
- `test_cpython_sees_only_its_root` (unit) is unchanged and passes with the reference build.

### The judge

`uv run pytest` in the clone, with the main tree's artifact set: 165/176 pass, 0 fail, 11
blocked; v1.2 36/37; v1.4 64/64; 524 passed, 12 skipped; ratchet lost 0, gained 10, **grew 3**;
judge changed: the v1.2 and v1.4 checks, `tests/harness/guest.py`, and the new unit file. ruff:
clean. The growth is the harness's separate stdlib preopen (acceptance criterion 2):
`test_default_integer_width_is_documented` +194,555 fuel (+0.0172%), `test_longdouble_parses`
+131,629 (+0.0117%), `test_sqlite_holds_a_lock_while_it_writes` +32,608 (+0.0342%).

### Left over

- Windows runs the walk's `CreateFileW` path, the held handles and the identity formula for the
  first time in the release dry run (criterion 3).
- The security review §5.6 requires before 0.1.0a3 must review this change.

### Revised against the build review

The build review (`../reviews/017-typed-grants-2026-10-17.md`) found one high defect and eight
smaller ones; its disposition says how each is answered. In short (EXECUTED in the clone):

- **Finding 1 (high).** The runner makes the module cache, if it can, before it walks `root`, so a
  root still to be made above a cache still to be made is judged to hold it and refused, with no
  folder of its own made. Decision 4 is amended. Seen failing: the stand-in "cache not made first"
  fails `test_a_bad_grant_is_refused_before_any_work`.
- **Finding 2.** Any grant at or above the temporary folder is refused, read-only too
  (`_shared_folders`). Stand-in "temp not shared" fails the same check.
- **Finding 3.** A zip folder removed on the host is made again; on Windows a replace refused while
  a guest holds the zip is accepted when the file in place hashes right. Stand-in "no zip
  recovery" fails `test_the_zip_is_read_only_and_shared`, which now removes the folder mid-run.
- **Finding 4.** `wasi_python`'s and wasmtime-py's own folders, and each artifact file's folder,
  are runtime folders; the README's `.venv` claim names the `.venv` this process runs from.
- **Finding 5.** Windows unit cases: a junction is refused; a walked folder cannot be moved while
  held. The README names other reparse points (OneDrive, container layers).
- **Finding 6.** Walk errors are `ValueError`s naming the grant; folders are opened for search
  only (`O_PATH`, `O_SEARCH`), so a folder one may search but not list is walked through
  (a unit case); the README names wasmtime's own error for a folder removed mid-call.
- **Finding 7.** Three checks, each seen failing on its stand-in: a forked child's exit leaves the
  parent's zip folder (`test_a_forked_child_leaves_the_parents_zip_folder`); a preopen at a guest
  name of the same length is refused; a deadline during the check is `"deadline"`
  (`test_a_deadline_during_the_grant_check_is_a_deadline`, the epoch advanced by count).
- **Findings 8 and 9.** README: a killed process leaves its zip folder whenever it dies; calls
  share only the read-only zip folder; run as the superuser every link on the way is refused.
- **The judge:** v1.4 66/66; 0 fail; ratchet lost 0, gained 12, grew 3 (the same three fuel
  growths as before, criterion 2's `--accept-growth`). ruff: clean. Stand-ins:
  `build017/mut/run2.py`, `mut/results2.txt`.
