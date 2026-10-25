# 139: The runner's folders are this user's, and the data guard refuses Windows's names

- **Status:** **drafted 2026-10-25** by the split of 137 (its pre-build review, `../reviews/137-the-door-answers-exact-bytes-and-the-audits-other-runner-notes-spec-2026-10-25.md`, which read these Decisions as 137's Decisions 3 and 4 and found no High in them), the review's Medium written in as Decision 1's Windows paragraph and Lows 6 and 7 as Decisions 3 and 2. Reviewed as part of 137's pre-build review, whose reviewer confirmed the Windows paragraph on 2026-10-25 against `Modules/posixmodule.c` (`os_mkdir_impl`: a mode of exactly 0700 gets an access list for SYSTEM, the Administrators and the owner; changed in 3.13) in the review's confirmation of the disposition; **fit to build**. Each row is to be written first and seen failing on main's code.
- **Date:** 2026-10-25
- **Owner:** Clay Gendron
- **Kind:** **parallel-safe**, **not structural**: `src/wasi_python/_platform.py` (`make_missing`, `_make_by_path` and one owner function; about 17 lines, **1,464 of 1,500 lines today, about 1,481 after**), `_private_dirs.py` (the sweep's folder check; `_owned` calls the owner function), `_zip.py` (`_member_parts` and the case-equal test in `_extract_data`), `_process.py` (one observers field, the owner seam), rows in `tests/unit/test_runner_grants.py`, `tests/unit/test_runner_sweep.py` and `tests/unit/test_runner_data.py`, the observers table in `tests/unit/test_process.py`, `docs/how-to/grants.md`, `CHANGELOG.md`. No `scripts/`, `recipes/`, pins, workflow or artifact byte. Every change tightens. No platform branch is added outside `_platform.py`: the owner function reads `os.geteuid` by `getattr`, as `_owned` reads `os.getuid` today, and `_zip` calls `_platform._rewritten` on every system.
- **Depends on:** nothing in flight. It is independent of 137 and 140 (the split's other two halves) and of 131 (the `_platform.py` split): `_platform.py` is 1,464 lines (EXECUTED, `wc -l src/wasi_python/_platform.py`, 2026-10-25), and this specification adds about 17 (INFERRED, a sketch of the change: the owner function with its docstring and blank lines 7, the descriptor branch's check 4, the by-path branch's mode, check and `where` argument 4, a two-line comment on Windows's mode), so about 1,481, under the 1,500 ceiling with no stacking. If 135 lands first and takes lines, the builder measures again, and stacks on 131 only if the sum passes the ceiling. Landed and unchanged: 111 and 113 (the file system along the WASI seams, and the root's walk), the private folders and their sweep, and the matplotlib data guard. It shares `_platform.py` with 131 and 135, `tests/unit/test_process.py` with 127 (127 changes the process fields table, this the observers table) and 129 (`on_capture`, the same observers table: a one-line rebase), `CHANGELOG.md` and `context/roadmap.md`.
- **Research it stands on:** h01's and h03's folder notes (`../reviews/0.1.0-security-audit-2026-10-25/agents/h01-fs-paths/`, `agents/h03-private-dirs/`), h12's zip-name scan (`agents/h12-binary/`), the pre-build review of 137 (its Medium 2 and Lows 6 and 7, and its reading of the sweep), and CPython's `os.mkdir` on Windows (READ, `Modules/posixmodule.c:6200-6230` and `Doc/library/os.rst:2569-2588` in the pinned 3.15.0 source, unpacked under `build/Python-3.15.0/`).

## The problem

Three places where a folder or a name the runner makes or reads is not checked as the check means (READ and EXECUTED by h01, h03 and h12; READ again here).

**A missing root's folders** (`_platform.py:387-409`). `make_missing` makes a root's missing components with `os.mkdir(name, dir_fd=fd)` at the umask's mode (0755 under 022) and adopts a `FileExistsError` as "a concurrent call made it". A missing root named under a folder another user can write (`/tmp` on Linux; macOS's `/private/tmp`, which is not the temp folder there) can be pre-made by that user, who then reads and seeds the guest's files. The by-path branch, `_make_by_path` (`_platform.py:602-606`), used on a POSIX system without `dir_fd` and by `_Windows.make_missing` (`_platform.py:1270-1275`), does the same with `Path.mkdir(exist_ok=True)`.

**The sweep** (`_private_dirs.py:152-190`). The sweep checks that the lock file is this user's, by `_owned`, which compares `st_uid` with `os.getuid()`, but not that the folder beside it is. `os.lstat` and `S_ISDIR` already refuse a symbolic link at the folder's name, and `isjunction` a junction (READ, the review). In a sticky temporary folder no other user can swap the name between the check and `remove_tree`, so an `lstat`-time owner check is enough (INFERRED, the review).

**The data guard's names** (`_zip.py:108-119`). `_member_parts` refuses an empty name, a leading `/`, a backslash, any `:`, and `""`, `.` or `..` as a component (a NUL never reaches it: `zipfile.ZipInfo` cuts a name at its first NUL). It does not refuse a Windows reserved device name, a component ending in a dot or a space, or names equal under case folding. The shipped zip holds none (h12 checked), and the guard's input is the checked set, so it matters only for a caller-supplied `artifacts=`.

## Decisions

### 1. A made root component is this user's, at 0700, on Linux and macOS

`make_missing` makes each missing component with `os.mkdir(name, 0o700, dir_fd=fd)` and, after `os.open(name, _DIR, dir_fd=fd)`, passes `os.fstat` of the opened descriptor to the owner function (Decision 2): a component another user owns raises `ValueError` naming it ("a folder on the way to the root was made by another user"), and nothing is walked. Reason: the descriptor is the folder the guest will be given, so its owner is the one that matters, and a check by path would race the open. `FileExistsError` is still adopted (a concurrent call of this user), and the owner check after it is what makes adoption safe. `_make_by_path` takes `where`, makes each component with `Path.mkdir(mode=0o700, exist_ok=True)`, and passes `os.lstat` of it to the owner function the same way. Reason: the by-path branch has no descriptor, and `lstat` refuses to look through a link put at the name.

On Windows the mode and the owner test do what Windows lets them. `os.mkdir` applies a mode of exactly 0700 as a protected access list giving full control to the user who made it, SYSTEM and the Administrators, and ignores any other mode, from Python 3.13 (READ, `Modules/posixmodule.c:6208-6215` and `os.rst:2569-2570,2587-2588` in the pinned 3.15.0 source); on 3.11 and 3.12 the documentation's "changed in 3.13" says the mode is ignored, so a made folder takes its parent's inherited access list there (INFERRED from that note; whether a 3.11 or 3.12 release carries a backport is not established here, so nothing relies on one). Windows has no uid: `os.geteuid` does not exist and `os.lstat(...).st_uid` is 0, so the owner function answers yes, and a folder another user made on the way is adopted on Windows as it is today. The folder rows are POSIX-only with that reason, and `grants.md` says "on Linux and macOS" for the owner test. Reason: a Windows owner test reads the folder's owner security identifier through `GetSecurityInfo`, new Windows code in `_platform.py` that would pass its ceiling; it waits on 131, and is the owner's to ask for.

### 2. One owner test, in `_platform.py`

The owner test is one function in `_platform.py`, `_this_users(st)`: true where `os.geteuid` does not exist, else whether the owner of `st` is `os.geteuid()`; `_private_dirs._owned` calls it. Reason: two tests would disagree, `make_missing` by the effective uid and `_owned` by `getuid()` today; the effective uid is the one a made file or folder is owned by, so it is the one to compare with. `_platform` cannot import `_private_dirs`, which imports `_platform`, so the function lives in `_platform`. The owner it compares is `st.st_uid`, or what `process().observers.owner_of(st)` returns when the judge sets that field (`owner_of: Callable[[os.stat_result], int] | None = None`, a new `_Observers` field; `None` is production). Reason: no check can make a folder another user owns, and a stand-in owner for one inode lets the rows tell the lock from the folder beside it.

The sweep's walk gains `_owned(folder)` beside the lock's check, on the `os.lstat` it already makes (`_private_dirs.py:186-188`), so a folder another user made at the name of this user's dead lock is never walked. The lock's check moves from `getuid()` to the effective uid with it.

### 3. The data guard's names are refused by Windows's rules too

A component for which `_platform._rewritten` is true is refused, on every system; the case-equal test is `_zip`'s own. Reason: `_rewritten` is already "the same answer as `ntpath.isreserved` gives" (READ, `_platform.py:1111-1118` and `:197-207`): the devices with `COM¹` to `LPT³`, `CONIN$` and `CONOUT$`, with or without an extension, a trailing dot or space, `:`, and the characters Windows rejects; a second list in `_zip.py` would drift from it. The case-equal test: two distinct member paths, or folder prefixes of them, equal under `casefold()` after NFC, are refused where `_extract_data` walks the members (`_zip.py:141-143`). Reason: the data folder is written by the runner, and a name that two systems would read differently is a name the guard should not have to reason about. The refusal is the guard's existing `RuntimeError` naming the member.

### 4. The documents

- `docs/how-to/grants.md`, *Choose a root*: "On Linux and macOS, a missing root's folders are made for you alone (0700), and a folder another user made on the way is refused. On Windows, from Python 3.13, a made folder gets an access list for you and the administrators alone; a folder that already exists is used as it is."
- The CHANGELOG line: "A missing root's folders are made at 0700 and refused on Linux and macOS if another user made them, the sweep of dead private folders removes only this user's, and the matplotlib data guard refuses the names Windows reserves or rewrites and names equal under case folding." Under constitution §4.15 this tightening needs no decision from the owner; the line names the one change an embedder can see, a made root's mode.

### 5. The rows first

Each seen failing first on `2cd47507`'s code.

- Folders, in `tests/unit/test_runner_grants.py`, POSIX-only (on Windows: no uid, and the mode is CPython's access list, which the judge does not read): a missing root's made components are mode 0700 under a umask of 022; a pre-made 0777 component, for whose inode `owner_of` returns another uid, is refused with `ValueError` naming it and nothing is walked (today it is adopted); the same through `_platform._make_by_path` called directly.
- The sweep, in `tests/unit/test_runner_sweep.py`, POSIX-only for the same reason: a dead lock of this user's beside a folder for whose inode `owner_of` returns another uid leaves the folder unwalked and in place (today it is removed).
- Names, in `tests/unit/test_runner_data.py`, every system, with a crafted inner archive: `CON.txt`, `aux`, `COM¹`, `name.`, `name `, `a?b` and `a*b` as components are refused; `Foo/x` beside `foo/x`, and `é` beside `é`, are refused as case-equal; the existing rows' names still pass.
- `tests/unit/test_process.py::test_the_observers_refuse_a_misspelt_field`: the fields list gains `owner_of` (a changed verdict, named in the claim list).

## Intent

After this specification, a root the runner makes on Linux and macOS is this user's alone and a folder another user put on the way is refused; the sweep removes only this user's folders; one owner test, by the effective uid, serves both; and the matplotlib data guard refuses every name a system would rewrite or read as another. On Windows a made folder gets Python's own access list from 3.13, and the documents say what is and is not checked there.

## Design

- `src/wasi_python/_platform.py`: `_this_users` (Decision 2); `make_missing` at 0700 with the owner check on the descriptor; `_make_by_path(where, path, missing)` at 0700 with the owner check on `lstat` (Decision 1). Measured against the ceiling first; `make_missing` is 23 lines today (EXECUTED, `ast`, by the review) and about 27 after.
- `src/wasi_python/_private_dirs.py`: `_owned` calls `_platform._this_users`; `_sweep_entry` checks the folder's owner on its `lstat` (`_sweep_entry` is 57 lines today, one more after).
- `src/wasi_python/_zip.py`: `_member_parts` calls `_platform._rewritten` per component; `_extract_data` refuses case-equal paths (Decision 3).
- `src/wasi_python/_process.py`: the `owner_of` field on `_Observers`.
- The rows of Decision 5, first; `docs/how-to/grants.md` and `CHANGELOG.md` (Decision 4).
- The commits, in order: the rows seen failing; the owner function and the folders; the sweep; the names; the documents.

## Scope

In: Decisions 1 to 5. Out: a Windows owner test by security identifier (after 131, the owner's call); checking components of a root that already exist (they are walked and judged by the root's rules today); the door and the security model's sentences (137); the poll shadow (140).

## Acceptance criteria

1. Every row of Decision 5 green on three systems (the POSIX-only rows skipped on Windows with their reason), each seen failing first on `2cd47507`'s code (output in `build/139/`).
2. `_platform.py` at or under 1,500 lines, measured by `wc -l` on the built tip, or the Kind line revised to stack on 131; every touched function under 80 lines; no module-level mutable; the one new seam on the process object; the rules checks green.
3. `tests/public_api.txt` unchanged; `ruff`, `mypy` clean; no code file names a specification, review, finding or `context/` path.
4. `grants.md` carries Decision 4's sentences.
5. The release workflow dispatched on the built tip; the Windows legs read for the name rows and the POSIX-only skips.

## For the lane

- **Kind:** parallel-safe, runner code, not structural; next wave; shares `_platform.py` with 131 and 135, `tests/unit/test_process.py` with 127 and 129, `CHANGELOG.md`, `context/roadmap.md`.
- **News file:** `context/changes/139-the-runners-folders-are-this-users.md` once 138's news files are in use, holding Decision 4's CHANGELOG line and the claim block below; until then the line goes under the unreleased section.
- **Claim list** ("139:"): new the rows of Decision 5; **changed verdicts:** `tests/unit/test_process.py`'s observers table (one field, `owner_of`); retired none; lost passes none; fuel none; bytes none.
- **Flags:** `--accept "139: a missing root's components are made at 0700 and refused on Linux and macOS if another user made them, one owner test by the effective uid serves the folders and the sweep, the sweep walks only this user's folders, and the data guard refuses Windows's reserved and rewritten names and case-equal names"`, `--accept-judge "139: folder, sweep and name rows, each seen failing first; the observers table gains owner_of; no other expectation edited"`.

## Landing notes

Not yet built. The builder fills this section: the commits, the checks seen failing on main's code first, the fast tier, `_platform.py`'s line count, the branch's release run (its id, every line green on three systems, no growth line), the self-check list (`../reviews/README.md`), and the rebase onto the wave's tip with every conflict named.

## One line

A folder the runner makes or sweeps is this user's, by one owner test on Linux and macOS and by Python's own access list on Windows, and a data name that any system would read as another is refused.
