# 024 — A root prepared through its walk

- **Status:** landed 2026-10-17. Built from the 0.1.0a3 security review and reviewed after
  (`../reviews/024-a-root-prepared-through-its-walk-2026-10-17.md`).
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`), the patch applier
  (`scripts/steps/apply_patches.sh`), judge additions in `tests/`, `README.md`, `CHANGELOG.md`.
- **Depends on:** 017 (typed grants: the walk, `_Walked`, the `_after_walk` seam), 020 (the
  applier), both landed.
- **Research it stands on:** the 0.1.0a3 security review
  (`../reviews/0.1.0a3-security-review-2026-10-17.md`), findings S1 (blocks the release), S2 and
  S3.

## The problem

Spec 017 walks a `root` one folder at a time, holds the last folder's descriptor, and checks
later that wasmtime opened the same folder. Between the two, the runner prepares the root by its
path string: `_real_dir` makes `root/usr/local/lib` and `root/tmp`, removing a link or file in
the way, and first re-makes the root itself with `mkdir(parents=True)`. Each step follows a link
anywhere in the root's own path.

So a guest of another call that can write a folder above this call's root (a per-job folder
inside a shared workspace, say) can swap that folder for a link between the walk and the
preparation. The runner then removes a file named `usr`, `local`, `lib` or `tmp`, or makes
folders, outside every grant. The identity check then refuses the call, so the victim's guest
never sees the wrong folder, but the host-side change has already been made. The review did
this (EXECUTED): a host file named `tmp` outside both roots was removed.

Two smaller findings ride along. S2: the host's own interpreter (a virtual environment's base
Python outside it, uv's or Homebrew's) is not among the folders a writable grant must stay away
from, though the runtime's own packages are. S3: the applier clears the caller's git settings
but would still read a `.git` folder inside an unpacked tree.

## Decisions

1. **The root is prepared only through its walked descriptor (S1).** On POSIX, where
   `os.mkdir`, `os.unlink` and `os.stat` take `dir_fd`:
   - a new `_real_dir_at(fd, parts)` goes down `parts` from the walked root's descriptor: for
     each name it `lstat`s it relative to the folder before, removes a link or file there
     (`unlink` with `dir_fd`, never followed), makes the folder if missing (a concurrent call's
     folder is accepted), and opens it `O_DIRECTORY | O_NOFOLLOW` relative to the one before. It
     returns the last folder's descriptor;
   - `_run_checked` makes `usr/local/lib` through it, from `walked_root.fd`;
   - `_home_folder` makes the root's `tmp` through it, from the root preopen's descriptor, and
     that descriptor is the one `HOME` is made and removed through (spec 017 already does both
     with `dir_fd`);
   - the root is never re-made by path after its walk: if it was moved, the preparation lands in
     the moved folder (the one that was checked); then a link in its place is opened by wasmtime
     and refused by the identity check (`RuntimeError`, "root changed between its check and the
     call"), and an empty path fails wasmtime's own open (`WasmtimeError`, as for any grant
     removed after its walk);
   - `_real_dir` is kept for Windows only, without its `mkdir(parents=True)`. There the walk
     holds every component without `FILE_SHARE_DELETE`, so no folder on the path can be renamed
     or removed, and guests cannot make links; this is spec 017's Decision 5 unchanged.
   The private root's `usr/local/lib` is made before its walk, inside the runner's own fresh
   `0700` folder, as today; its `tmp` goes through its walked descriptor like any root's.
2. **The host's interpreter is a runtime folder (S2).** `_runtime_folders` adds the running
   interpreter's `sysconfig` paths `stdlib`, `platstdlib`, `purelib`, `platlib` and `scripts`,
   and the user's site-packages when `site.ENABLE_USER_SITE` (the build review's finding 2),
   each that exists, resolved and de-duplicated, named "the host Python's own code". A writable grant at,
   inside or above one is refused, as for wasmtime-py's code. Read-only grants are unchanged.
3. **The applier refuses a tree that holds `.git` (S3).** One line after the tree is found:
   `ERROR: TREE holds .git; a source tree is never a repository`. No pinned tarball holds one
   (EXECUTED: `tar -tf` of all seven), so no tree changes. The applier's hash is recorded in
   `MANIFEST` (a `recipe` line), so the set is rebuilt by step 90, as spec 018's was; no other
   artifact changes. The header's claim, that git runs with every configuration cleared, then
   holds for every tree.
4. **Docs.** The README's *Grants* names S2's rule beside wasmtime-py's; *Not protected* is
   unchanged (the runner no longer acts outside the grants through a root's path). The
   CHANGELOG's 0.1.0a3 entry names all three.

## Intent

The runner changes the host only inside the folders it checked, whatever another guest does to
the path above them.

## Design

```
src/wasi_python/runner.py    _real_dir_at; _run_checked and _home_folder use it; _runtime_folders
scripts/steps/apply_patches.sh   the .git refusal
tests/checks/test_v1_2_hostile_guest.py   the root-swap check; the host-Python refusal
tests/unit/test_patches.py   the .git refusal
README.md, CHANGELOG.md
```

## Scope

In: S1, S2, S3. Out: S4 (0.1.0a2's F8, the artifact folder's preference, dispositioned then as a
later change); S5 (no finding).

## Acceptance criteria

1. **The root-swap check (v1.2), seen failing first.** Through `_after_walk`, a call's root
   `base/arena/sub` is swapped for a link to `base/outside`, which holds a regular file `usr` and
   a regular file `tmp`. On POSIX the call raises `RuntimeError` naming the root, and both files
   are unchanged, and `usr/local/lib` was made in the moved folder; on Windows the swap is refused by the held handles and the call runs on the
   granted folder. On today's code the files are removed.
2. A second case swaps the root out by rename alone (no link): on POSIX the call raises
   `WasmtimeError`, nothing is made at the old path, and the moved folder is the only one
   changed.
3. A writable grant at the host Python's `stdlib` is refused, naming "the host Python's own
   code"; a read-only grant there is not. Seen failing first.
4. The applier refuses a tree holding `.git` with one `ERROR` line and changes nothing. Seen
   failing first.
5. `uv run pytest` green with `--accept-judge`; lost 0; no growth.
6. A release dry run passes every job, Windows included.

## Landing notes

Built 2026-10-17 by the implementer (Claude Opus 5.5) on main (`7d4c4ad`), from the security
review's S1 to S3. Written straight after the review, without a pre-build review: the fix is the
one the review proposed. Every claim below was run (EXECUTED) on macOS arm64.

### Seen failing first

On today's code (`build/seen024.txt`): `test_a_swapped_root_is_never_prepared_by_path[link]`
failed with `IsADirectoryError` reading `outside/usr` (the runner had removed the host's file and
made a folder in its place); `[rename]` failed because the runner made the root again at its old
path; `test_a_bad_grant_is_refused_before_any_work` did not raise for a writable grant at the host
Python's `stdlib`; `test_a_tree_holding_git_is_refused` was not refused.

### What was built

- `runner.py`: `_real_dir_at(fd, parts)` (stat, unlink and mkdir with `dir_fd`, each folder
  opened `_DIR` from the one before); `_run_checked` makes `usr/local/lib` through
  `walked_root.fd`, and `_home_folder` makes `tmp` through the root preopen's descriptor, which
  `HOME` is then made and removed through; `_real_dir` (Windows only) no longer re-makes the
  root; `_runtime_folders` adds the host Python's `sysconfig` folders.
- `apply_patches.sh`: the `.git` refusal, one `ERROR` line.
- The checks of criteria 1 to 4, the README (*Grants*: the host Python's folders, and the
  root's preparation), the CHANGELOG entry. Step 90 re-run for the applier's new hash.

### Criterion 2, as built

Moved away (no link), the root's old path is empty when wasmtime opens it, so the call raises
wasmtime's `WasmtimeError` (as the README already says for any folder removed after its check),
not `RuntimeError`; the spec's Decision 1 and criterion 2 say so.

### The judge

`uv run pytest`, with main's set (step 90 re-run): 186/188 pass, 0 gap, 2 blocked, 0 fail; 652
passed, 4 skipped; ratchet vs `bf9581b971`: lost 0, gained 2, grew 0; judge changed:
`tests/checks/test_v1_2_hostile_guest.py`, `tests/unit/test_patches.py`. ruff: clean.

### The build review

`../reviews/024-a-root-prepared-through-its-walk-2026-10-17.md`, by the security reviewer who
found S1: it lands once the dry run passes. It re-ran the S1 attack (10,753 swaps against 1,269
victim calls, 42 inside the window): nothing outside either root changed. Each fix reverted
fails its own check. Its findings, answered in its Disposition: the dry run (1, below); the
host Python's `scripts` and the user's site-packages added to S2's rule, with a check seen
failing without it (2); *Not protected* names that such a guest can make the other call's `run`
raise (3). The judge after the revision: 186/188, lost 0, grew 0.

### Release dry run

Run 39060577579 on `de91fff` (024 accepted): every job passed, the arm64 Linux rebuild from the
pins and "the same bytes from every host" included, and the wheel verified on Windows, Linux and
macOS (criterion 6; the review's finding 1).
