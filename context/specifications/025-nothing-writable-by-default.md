# 025 — Nothing writable by default

- **Status:** landed 2026-10-17; reviewed (`../reviews/025-nothing-writable-by-default-2026-10-17.md`, which is also §5.6's security review of this change).
- **Owner:** Clay Gendron
- **Kind:** the runner (`src/wasi_python/runner.py`: `run`, `run_async`, `_check_root`), the
  command line (`src/wasi_python/cli.py`), judge changes in `tests/`, `README.md`, `CHANGELOG.md`.
- **Depends on:** 017 (typed grants, `root=False`), 019 and 022 (the command line), 024 (a root
  prepared through its walk), all landed.
- **Research it stands on:** `../research/2026-10-17-typed-grants.md` (question 1, the default),
  and the owner's answer below.
- **Decided by:** the owner's answer to question 24 (`../decisions.md`), recorded in the
  constitution's §4.15: "A call given no root and no grants has nothing writable: no folder, no
  `/tmp`, no `HOME`." It ships in 0.1.0a3, before the first PyPI release.

## The problem

Today `run(argv)` gives the guest a fresh, private, writable directory as `/`, removed after the
call. Nothing of the host is reachable through it, but it is a writable filesystem the embedder
never asked for. The owner's rule is that the guest touches no filesystem unless the embedder
provides one.

## Decisions

1. **The default is no root.** `run` and `run_async` take `root: str | PathLike | bool | None =
   False`. With `False` (or `None`, which means the same: none) the guest has no `/`: only the
   stdlib zip, read-only at `/usr/local/lib`, and the grants. With no writable grant at `/tmp`
   there is no `HOME`, as `root=False` does today; `TMPDIR` stays `/tmp` in `BASE_ENV`, so
   `tempfile` fails clearly instead of writing somewhere unexpected.
2. **The private root is asked for by name.** `root=True` gives today's fresh, private, writable
   `/`, made in the temporary folder, `0700`, locked (spec 016) and removed after the call.
   (`True` was refused until now, so no caller changes meaning.) A path gives that host folder,
   as today.
3. **The command line follows.** Without a root option the program has no `/`. `--private-root`
   asks for `root=True`; `--root HOST` is unchanged; `--no-root` stays accepted and now names
   the default. The three are mutually exclusive; `--root` given twice is still a usage error.
4. **What a program sees without a root.** It can import, compute, print, read the stdlib, call
   the door, and read and write its grants. `open('x', 'w')`, `tempfile`, `np.save`,
   `df.to_csv('x.csv')` and any relative path fail with `OSError`; the README says so, and that
   `root=True` or a writable grant is the remedy.
5. **The judge.** A new v1.2 check, seen failing first: a call with no `root` and no grants
   finds `/` absent (`os.listdir('/')` raises), cannot create a file anywhere (`/x`, `/tmp/x`,
   `/usr/local/lib/x`), has no `HOME`, and still imports numpy and pandas and computes. The
   command line's unit tests gain `--private-root` and the new default. Checks whose subject is
   not the default but whose program writes a file pass `root=True`, each named in the landing
   notes; none loses what it checks.
6. **Docs.** The README's lead example stays (it writes nothing). *From Python*, *Grants* and
   *From any language* describe the new default and `root=True`/`--private-root`; the CHANGELOG
   has a **Breaking** line with the one-line migration: pass `root=True` to keep the old
   behaviour.

## Intent

A guest touches no filesystem but the read-only stdlib unless the embedder grants one.

## Design

```
src/wasi_python/runner.py    run, run_async: root=False; _check_root: True asks for a private root
src/wasi_python/cli.py       --private-root; the default
tests/checks/…               the new default's check; root=True where a program writes
tests/unit/test_cli.py       the options
README.md, CHANGELOG.md
```

## Scope

In: the default and its spelling. Out: changing what a root or grant may be (spec 017's rules
stand); a writable `/tmp` by default (the owner chose nothing writable).

## Acceptance criteria

1. The new check exists and was seen failing on today's code.
2. `run(["-c", "open('/x','w')"])` exits 1 with `OSError` in its stderr; with `root=True` it
   exits 0.
3. `uv run pytest` green with `--accept-judge`; lost 0; growth only where a check now passes
   `root=True` to keep its old setup (stated).
4. A release dry run passes every job, Windows included.

## Landing notes

Built 2026-10-17 by the implementer (Claude Opus 5.5) on main (`f81d4e7`). Every claim below was
run (EXECUTED) on macOS arm64.

### Seen failing first

`test_nothing_is_writable_by_default` (both binaries) on today's code printed `root listed wrote
/x wrote /tmp/x refused /usr/local/lib/x wrote x HOME 6`: a listed `/`, writes at `/x`, `/tmp/x`
and a relative path, and a `HOME`.

### What was built

- `runner.py`: `run` and `run_async` default `root=False`; `_check_root` maps `None` and `False`
  to no root and `True` to a private root (kept internally as `None`, as before); the docstring.
- `cli.py`: `--private-root` (`root=True`) in the group with `--root` and `--no-root`;
  `--no-root` still passes `root=False`.
- The README (*From Python*, *Grants*, *From any language*) and question 22's state pattern in
  *Grants*, whose example was run (two calls printed 1 and 2); the CHANGELOG's **Breaking** line.

### Judge changes, each keeping its subject

These checks are about the private root itself, so their programs now ask for it with
`root=True`: `test_a_call_without_a_root_shares_nothing`,
`test_a_trapped_call_without_a_root_is_removed[*]`,
`test_a_guest_that_uses_up_host_descriptors_cannot_make_run_raise` (its child scripts), and the
`HELD` child of `test_a_killed_process_leaves_nothing_after_the_next_call` and
`test_a_live_calls_folders_are_never_swept` (which count the private root among the swept
folders). `test_a_bad_grant_is_refused_before_any_work` no longer expects `root=True` to be
refused, and `test_the_argument_types` asserts the new mapping; `test_root_reaches_run` gains
`--private-root`.

### The judge

`uv run pytest` with main's set (and spec 026's harness fix, committed separately): 188/190 pass,
0 fail; 656 passed, 4 skipped; ratchet vs `efa3f1203e`: lost 0, gained 2, grew 0. ruff clean.

### The build review

`../reviews/025-nothing-writable-by-default-2026-10-17.md`: lands after its dry run; the change
only tightens. A default call writes nothing on either binary, `run_async` and the command line
agree, and `root=True` keeps the private root's properties. Findings answered in its
Disposition: the dry run (below); the README's sqlite item (fixed); `--private-root` twice
(answered: a flag).

### Release dry run

Run 39066694075 on `cb0c5a6` (025 and 026 accepted): every job passed, the arm64 Linux rebuild
from the pins and "the same bytes from every host" included, and the wheel verified on Windows,
Linux and macOS. (criterion 4)
