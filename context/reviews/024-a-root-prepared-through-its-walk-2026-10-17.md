# Review of 024: a root prepared through its walk (the build)

- **Date:** 2026-10-17
- **Reviewer:** a fresh agent (Claude Opus 5.5). I did not write the change. I wrote the 0.1.0a3
  security review whose S1 to S3 this specification fixes, so I know the attack. Every claim
  is labelled EXECUTED, READ or INFERRED.
- **Read:**
  - `AGENTS.md`;
  - the constitution (§4.15, §5.6);
  - specification 024 with its landing notes;
  - the 021 build review, for the format;
  - `git show 55cf078` (seven files);
  - in `src/wasi_python/runner.py`: `_walk_posix`, `_Walked`, `_make_missing`,
    `_run_checked`, `_call_deferred`, `_home_folder`, `_real_dir_at`, `_real_dir`,
    `_runtime_folders`, `_check_preopens` and `_Private`;
  - `scripts/steps/apply_patches.sh`;
  - the release workflow's Python set-up.
- **Reviewed:** commit `55cf078` on main (not pushed, not accepted): `runner.py` (+56/−8),
  `apply_patches.sh` (+2), `tests/checks/test_v1_2_hostile_guest.py` (+58),
  `tests/unit/test_patches.py` (+12), `README.md`, `CHANGELOG.md` and the specification.
- **Re-ran (EXECUTED, darwin-arm64, main's `build/artifacts` read only, step 90 already re-run
  by the author):** scripts and logs are under the scratch folders `sec03/` (the attack) and
  `rev024/` (mutants, logs). `build/progress/latest.json` was copied before the judge and
  restored byte for byte after (SHA-256 `8af4257a…`). `--accept` was never passed.

## The judge

- **`uv run pytest -p no:cacheprovider -q` (EXECUTED, the full run, slow checks included):**
  - scoreboard: `186/188 pass · 0 gap · 2 blocked · 0 fail` (unit suite 466/468, 2 skipped);
  - `652 passed, 4 skipped in 94.10s`;
  - ratchet vs `bf9581b971`: lost 0, absent 0, gained 2, grew 0;
  - judge changed: `tests/checks/test_v1_2_hostile_guest.py`, `tests/unit/test_patches.py`.

  These match the landing notes.
- **ruff (EXECUTED):** `ruff check src tests`: "All checks passed!"; `ruff format --check src
  tests`: "53 files already formatted".
- **The applier's hash (EXECUTED):** `MANIFEST`'s `recipe` line for `apply_patches.sh` is
  `1fd6bdbe…`, equal to `shasum -a 256` of the committed file.

## S1: the root is prepared through its walk

- **The security review's attack, re-run (EXECUTED, `sec03/scripts/race_root.py`, the same
  20 s attacker as the first run).** A victim calls `run` in a loop with `root=<arena>/sub`.
  Meanwhile a concurrent call with `root=<arena>` keeps replacing `sub`. Its guest uses only
  calls the README says it can make. A folder outside both roots holds regular files `tmp`,
  `usr` and `SECRET`.

  | run | attacker swaps | victim calls | outcomes | outside after |
  |---|---|---|---|---|
  | before the fix (security review) | 3,978 | 793 | 780 ran, 10 `ValueError`, 2 `FileNotFoundError`, 1 `RuntimeError` | **`tmp` removed** |
  | fixed, 1 | 644 | 668 | 668 ran | unchanged |
  | fixed, 2 | 10,753 | 1,269 | 713 ran, 415 `ValueError` (walk), 99 `WasmtimeError` (root gone at wasmtime's open), 42 `RuntimeError` (identity check) | unchanged |

  - Run 2's 42 `RuntimeError`s show the swap landed inside the window between the walk and the
    identity check 42 times. Nothing outside changed in any of them.
  - No victim guest ever listed `SECRET`.
  - Logs: `rev024/race_root_fixed_1.log` and `rev024/race_root_fixed_2.log`.
- **No path string of a root or grant is used between the walk and the identity check on
  POSIX, except wasmtime's own open (READ).** I went through every host-side use in
  `_run_checked` and `_call_deferred`:
  - **A given root:** `usr/local/lib` goes through `_real_dir_at(walked_root.fd, …)`. `tmp`
    goes through `_real_dir_at` from the `/` preopen's walked descriptor. `HOME` is made and
    removed with `dir_fd` on that result. `Path(walked_root.path)` and `root / "tmp"` are used
    only on the Windows branches, where `tmp_fd` is `None`.
  - **A writable grant at `/tmp`:** `os.dup(p.walked.fd)`, as before.
  - **The private root:** made by path, before its walk, inside the runner's own fresh `0700`
    folder in the temporary folder. No grant may be at or above that folder, read-only
    included (spec 017; EXECUTED in the security review). So no guest can reach any component
    of its path. Its `tmp` now goes through its walked descriptor too.
  - **A missing root:** made with `dir_fd` in `_make_missing`, then walked again with
    `judge=True`. It is never made again by path afterwards. `_real_dir` no longer calls
    `root.mkdir(parents=True)`.
  - **The zip folder:** walked with `judge=False`. It is in the temporary folder, which no
    grant can reach.
  - **Clean-up after the call** (`_Private.remove`, `_remove_zips` at exit): this is by path,
    but only for folders directly in the temporary folder. It runs after the store is closed,
    and `shutil.rmtree` does not follow links.
  - **`wasi.preopen_dir(p.walked.path, …)`:** by path, by design. The identity check covers it.
- **No descriptor leaks (READ).**
  - `_real_dir_at` dups its input. It closes `here` before replacing it with `child`, and
    closes `here` on any exception (`BaseException`). The caller's descriptor stays open, as
    documented.
  - `_run_checked` closes the result at once.
  - `_home_folder` returns it as `tmp_fd`. `_call_deferred` closes it in every path: in the
    `except` around the `HOME` mkdir, and in the `finally` after the store.
  - If `_real_dir_at` raises inside `_home_folder`, no descriptor has been handed out.
  - The walked descriptors are still open when `_home_folder` runs (`_check_preopens` closes
    them later, inside `_drive`), so the `/` preopen's `fd` is valid there.
  - One theoretical leak: if `os.close(here)` itself raised, `child` would leak. That close
    does not fail on a valid descriptor (INFERRED), so this is not a finding.
- **Search-only descriptors as `dir_fd`:**
  - **macOS:** `_DIR` is `O_SEARCH | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC` (EXECUTED: `O_PATH`
    is absent and `O_SEARCH` is `0x40100000`). The root-swap check passes on this machine
    (EXECUTED). It stats, unlinks, makes and opens through such descriptors, makes `HOME`
    through one, and removes it with `shutil.rmtree(…, dir_fd=…)`. On this Python, `os.stat`,
    `os.unlink`, `os.mkdir`, `os.open` and `os.rmdir` all take `dir_fd`, and
    `shutil.rmtree.avoids_symlink_attacks` is `True` (EXECUTED).
  - **Linux:** READ, not run. `open(2)` says an `O_PATH` descriptor "can be passed as the
    dirfd argument of openat() and the other *at() system calls". So `fstatat`, `unlinkat`,
    `mkdirat` and `openat` work through it. `shutil.rmtree` opens each child with its own
    `O_RDONLY` descriptor relative to that one, which `O_PATH` allows. `dup` of an `O_PATH`
    descriptor is allowed.
  - **Linux, a link put in place:** `O_PATH | O_NOFOLLOW` alone would open the link itself.
    With `O_DIRECTORY`, the kernel still requires a directory (`LOOKUP_DIRECTORY`), so it
    fails with `ENOTDIR` (READ, from the kernel's `do_open`; INFERRED for the kernels CI runs).
  - **Earlier evidence:** the writable `/tmp` grant branch has used `os.dup` of an `O_PATH`
    walked descriptor as `dir_fd` since spec 017, and that passed spec 017's and spec 021's
    Linux release dry runs (READ, from their landing notes).
  - **Still to run:** criterion 6, the dry run of this commit (finding 1).

## S2: the host Python's folders

- **The rule (READ, EXECUTED).** On this machine, `sysconfig.get_paths()` gives:
  - `stdlib`: uv's `cpython-3.14.2-macos-aarch64-none/lib/python3.14`, which is outside the
    venv;
  - `platstdlib`: `.venv/lib/python3.14`;
  - `purelib` and `platlib`: `.venv/lib/python3.14/site-packages`.

  A writable grant at `stdlib` is refused, naming "the host Python's own code". A read-only
  grant there runs (the new lines of `test_a_bad_grant_is_refused_before_any_work`, EXECUTED).
- **Ordinary grants on the three CI platforms (INFERRED from the workflow, READ).**
  - Every job gets Python from `astral-sh/setup-uv` with `UV_PYTHON: "3.14.2"`. So `stdlib` is
    in uv's Python folder (`~/.local/share/uv/python/…` on Linux and macOS, and under
    `%APPDATA%\uv\python` on Windows), and the other three paths are in the checkout's `.venv`.
  - The judge's grants live under `build/harness/guest-*` and pytest's `tmp_path`. Neither is
    at or above those folders.
  - The checkout itself was already refused before this change, since it holds `.venv` and
    `wasi_python`'s code.
  - On Windows, `platstdlib` for a venv is `.venv\Lib` (`nt` scheme). It is again inside the
    checkout.
  - What is newly refused is a writable grant at or above a Python installation: `/usr` for a
    distribution Python, `/opt/homebrew`, `~/miniconda3`, uv's Python folder. None of these
    is ordinary.
  - `d.is_dir()` skips a path that does not exist.
  - Criterion 6's dry run (Windows included) is what will execute this on all three
    platforms (finding 1).
- **Residual (READ, INFERRED):** finding 2.

## S3: the applier refuses a tree holding `.git`

- **The refusal (EXECUTED, `rev024/s3/`).** A tree whose `.git` is a gitfile
  (`gitdir: /nonexistent`) is refused with one line, `ERROR: <tree> holds .git; a source tree
  is never a repository`, and exit 1. The test covers a `.git` folder (`git init`). The
  `[ ! -e ] && [ ! -L ]` form also catches a dangling link (READ).
- **In-tree `.gitattributes` (EXECUTED).** numpy 2.5.2's tarball holds `numpy-2.5.2/.gitattributes`
  at the top of the tree it patches, and `doc/source/_static/scipy-mathjax/.gitattributes`
  (`tar -tzf`). No pinned tarball holds `.git` (EXECUTED, all sixteen downloads). Outside a
  repository, git ignored an in-tree `.gitattributes` in three tries: none,
  `a.c whitespace=-trailing,cr-at-eol eol=crlf text`, and `a.c -text binary`. Each applied
  the patch and left identical LF bytes. So with `.git` refused, the header's claim holds for
  the attributes I tried. I did not try every attribute git knows, such as `filter`, which
  needs configuration that `env -i` already clears (INFERRED).

## Mutants (EXECUTED, `rev024/m1`–`m3`, each a `git archive HEAD` copy with one fix reverted)

| mutant | reverted | result |
|---|---|---|
| m1 | S1: `_real_dir` by path at both sites, with `root.mkdir(parents=True)` restored | `test_a_swapped_root_is_never_prepared_by_path[link]` fails: `IsADirectoryError` on `outside/usr`, so the runner had replaced the host file with a folder. `[rename]` fails: `RuntimeError` instead of `WasmtimeError`, because the root was made again by path. 2 failed, 2 passed. |
| m2 | S2: the `sysconfig` folders | `test_a_bad_grant_is_refused_before_any_work` fails: `DID NOT RAISE ValueError`. 1 failed, 3 passed. |
| m3 | S3: the `.git` line | `test_a_tree_holding_git_is_refused` fails: the applier exits 0 and applies. 1 failed, 3 passed. |

Each mutant ran only these four checks, from its own copy, with the main venv's interpreter.
`PYTHONPATH` pointed at the copy's `src`, confirmed by `wasi_python.__file__`, and
`WASI_PYTHON_ARTIFACTS` at main's set. Main's `build/progress/latest.json` was unchanged after
(EXECUTED).

## Acceptance criteria against evidence

| # | criterion | evidence | holds |
|---|---|---|---|
| 1 | link swap: `RuntimeError`, host files unchanged, `usr/local/lib` in the moved folder; Windows refuses the swap | EXECUTED on macOS (the check passes; m1 fails it); Windows branch READ only | yes on POSIX; Windows by the dry run |
| 2 | rename swap: `WasmtimeError`, nothing made at the old path | EXECUTED (the check; m1 fails it) | yes |
| 3 | writable grant at `stdlib` refused, read-only allowed | EXECUTED (the check; m2 fails it) | yes |
| 4 | applier refuses `.git`, one line, nothing changed | EXECUTED (the check; m3 fails it; my gitfile case) | yes |
| 5 | judge green, lost 0, no growth (`--accept-judge` is the owner's step) | EXECUTED: 186/188, lost 0, grew 0 | yes, pending acceptance |
| 6 | a release dry run passes every job, Windows included | not in the landing notes | **open** (finding 1) |

## Findings, most severe first

### 1. Criterion 6, the release dry run, is not done: blocks landing, not the fix (READ)

The landing notes report only the macOS judge. Two things are shown on no platform but this
one:

- Windows' branch of the root-swap check, where the held handles refuse the rename and
  `_real_dir` is now used without `mkdir(parents=True)`;
- S2's `sysconfig` folders on Ubuntu's and Windows' uv Pythons.

The Linux `O_PATH` path is likely fine (READ, above). The dry run is the specification's own
criterion. Run it on this commit before acceptance.

### 2. S2 leaves two host-code folders out: low, does not block (READ, INFERRED)

`_runtime_folders` now covers `stdlib`, `platstdlib`, `purelib` and `platlib`. It does not
cover:

- **the user site-packages** (`site.getusersitepackages()`, such as
  `~/.local/lib/python3.14/site-packages`). An interpreter that is not in a venv imports it
  at start-up, including `usercustomize`. A writable grant there could plant code the next
  host process runs (INFERRED; not executed).
- **the interpreter's `scripts` folder** (`sysconfig.get_path("scripts")`: `bin/`, or
  `Scripts\` on Windows). This matters when it is outside an already-protected folder, as for
  a base interpreter's `bin/`. The venv's own `bin` is inside `.venv`, which is already
  refused, since it holds `purelib`.

An embedder must name such a folder writable on purpose, as in S2. Suggested: add both when
they exist (user site only when `site.ENABLE_USER_SITE`), or name the gap in *Grants*.

### 3. A guest with write access above another call's root can still make that call's `run` raise: informational (EXECUTED, INFERRED)

In fixed run 2 the victim's `run` raised:

- `ValueError` 415 times, at the walk;
- `WasmtimeError` 99 times;
- `RuntimeError` 42 times.

The README's *Grants* already names the last two for a folder swapped or removed after its
check. The fix also adds one path, INFERRED: two calls on one root, where the other guest
swaps `usr` or `tmp` for a link between `_real_dir_at`'s `mkdir` and its `O_NOFOLLOW` open.
That raises `OSError` (`ENOTDIR`/`ELOOP`), where the old code raised later or followed the
link. The README's "concurrent calls on one root" item says a guest can change the other
call's files, but not that its `run` can raise.

None of these escapes, and the old code raised in the same races. `SECURITY.md` puts "anything
a guest does that makes `run` raise" in scope, so one clause in "Not protected" would close it:
"…and make the other call's `run` raise (`ValueError`, `RuntimeError`, `WasmtimeError` or
`OSError`)".

### 4. The CHANGELOG entry is accurate; a note on wording: no finding (READ)

The entry says the runner "removed a file named `usr`, `local`, `lib` or `tmp`, or made
folders". m1's failure confirms the replacement of a host file by a folder (EXECUTED). The
README sentence ("a folder swapped above it changes nothing elsewhere") matches fixed runs 1
and 2.

## Constitution checks

- **§4.15:** no default is loosened. The new rule only refuses more writable grants. Read-only
  grants are unchanged (EXECUTED).
- **§4.1 and §4.2:** the applier's change is a recipe change, hashed in `MANIFEST` and re-run
  through step 90. No upstream source changes (EXECUTED for the hash).
- **§4.4:** no guest import is added (READ).
- **§4.9:** the new checks count outcomes and bytes, and none times (READ).
- **§4.10:** the landing notes' numbers match my re-run (EXECUTED).
- **§5.6:** this review is by a fresh agent that did not write the change. The specification
  skipped a pre-build review, and says why: the fix is the one the security review proposed.
  This review covers that design too.
- **AGENTS.md rule 4:** the judge's changes are additions only. No golden, gap list or progress
  file was edited to pass (READ, `git show --stat`).

## Disposition (filled in by the author, then confirmed by the reviewer)

1. **Answered, then done.** The dry run needs the push; it runs on the amended commit and is
   cited in the landing notes before the acceptance.
2. **Fixed.** `_runtime_folders` adds `sysconfig`'s `scripts` and, when `site.ENABLE_USER_SITE`,
   the user's site-packages. `test_a_bad_grant_is_refused_before_any_work` also refuses a
   writable grant at `scripts` (in a venv, `.venv/bin`, which no earlier rule covered): it
   fails with `scripts` removed from the list (EXECUTED) and passes with it. The README's
   *Grants* and Decision 2 name both.
3. **Fixed.** *Not protected* now says a guest that can write above another call's root can
   make that call's `run` raise `ValueError`, `RuntimeError`, `WasmtimeError` or `OSError`, and
   that nothing outside the grants changes.
4. No finding.


## Verdict

**S1, S2 and S3 are fixed and guarded.** Each fix has a check that fails when the fix is
reverted. The security review's own attack, re-run against the fixed runner, changed nothing
outside both roots. Land after finding 1, the release dry run of this commit with every job
passing, Windows included. Findings 2 and 3 do not block; answer each in writing or schedule
it. With this landed, the 0.1.0a3 security review's S1 blocker is closed. Its reviewer confirms
that in the security review's disposition, once the dry run is green.
