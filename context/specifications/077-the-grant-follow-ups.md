# 077 — The grant follow-ups

- **Status:** drafted 2026-10-19 on `spec/077-the-grant-follow-ups` from main `d900dd9`; awaiting
  its pre-build review (the lane asked for one, though §5.6 does not: it changes neither the
  guest's imports nor its exports, the artifact set nor the build recipe). A different agent
  reviews the build.
- **Date:** 2026-10-19
- **Owner:** Clay Gendron
- **Kind:** the runner, the judge and docs; **parallel-safe**, not build-class.
  `src/wasi_python/runner.py` (`_WIN_DEVICES` only); `tests/unit/test_runner_grants.py` (one
  case's module and rows, one case's rows, the Win32 model's device set and one folder);
  `README.md` (*Grants*), `CHANGELOG.md` (0.1.0a7). It touches no `scripts/`, `recipes/`,
  `downloads/SHA256SUMS` or workflow on its branch. One temporary commit that adds `-rA` to the
  release workflow's verify step lives only on a throwaway remote branch, `spec/077-verify`,
  deleted after the Windows dry run (Decision 4). **It changes no line of
  `tests/public_api.txt`.**
- **Depends on:** 076 (the grant checks agree on Windows: `_rewritten`, `_WIN_DEVICES`, the raw
  wrong-mode rows and the Win32 model), landed in `3ea0582`.
- **Research it stands on:**
  - Spec 076's build review, findings F1 and F2
    (`../reviews/076-the-grant-checks-agree-on-windows-build-2026-10-19.md`), and spec 076's
    landing notes, which hand both to this spec.
  - Microsoft, "Naming Files, Paths, and Namespaces" (learn.microsoft.com, page dated
    2024-08-28, updated 2025-04-11; READ 2026-10-19). Its reserved names are `CON, PRN, AUX,
    NUL, COM1` to `COM9`, `COM¹, COM², COM³, LPT1` to `LPT9`, `LPT¹, LPT², and LPT³`, "also
    … followed immediately by an extension". Its note: Windows treats the ISO/IEC 8859-1
    superscript digits as digits in `COM#` and `LPT#`, "making them reserved in every
    directory". It names no `COM0` or `LPT0` as reserved.
  - CPython's `Lib/ntpath.py` (`context/prior_art/cpython`, branch 3.14, `7c04882`, lines 307
    to 333, READ): `_reserved_names` is `CON PRN AUX NUL CONIN$ CONOUT$`, and `COM` and `LPT`
    with `1` to `9`, `¹`, `²`, `³`. Its comment: "The rules are complex and vary across Windows
    versions. On the side of caution, return True for names that may not be reserved." It
    matches the stem as `_rewritten` does (before the first period, trailing spaces dropped).
    `ntpath.isreserved` is new in 3.13, and the runner supports 3.11, so it cannot be called.
  - Probes, EXECUTED on macOS arm64 with wasmtime-py 49.0.0 on main `d900dd9`; scripts and
    outputs in the worktree's git-ignored `build/077/`:
    - `probe_raw_read.py` → `.out`. Today's `read` export's iovec at 400 is `(0, 0)`. A read
      through a write-only descriptor answers 8 through it and through the iovec at 200,
      `(300, 2)`. A control read of the grant's `f.txt` through 400 reads 0 bytes; through 200
      it reads 2 bytes, `b'or'`.
    - `probe_rewritten.out`. Today `_rewritten` is false for `COM¹`, `lpt³.txt`, `Com² .x`,
      `CONIN$`, `conout$.log`, `COM0` and `LPT0`, and true for `COM1`.

## Decisions

1. **The raw read row reads two bytes, and a control read proves it (F1).** The `read` export
   of `RAW` reads through the iovec at 200 (`buf 300, len 2`) that the module's data already
   holds, and writes its count at 208, as `write` does. The row's expected value is unchanged:
   `files.wrong_mode_errno(sys.platform)`. Then, after the file assertions, one control row:
   the grant's `f.txt` opened again to read, `read` through it answers 0, the count at 208 is
   2, and memory at 300 holds `b"or"`. The control is what makes the row's length checkable. An
   errno alone cannot tell a two-byte read from a zero-length one, since both answer 8 today
   (`probe_raw_read.out`). It runs last because it overwrites the `XX` the final write sends.
   The review's other option, eight more bytes of data at 400, was not taken: one iovec, used by
   both exports, is the simpler module.

2. **The reserved names are Microsoft's and CPython's, together (F2).** `_WIN_DEVICES` gains
   `com¹ com² com³ lpt¹ lpt² lpt³` (Microsoft's page) and `conin$ conout$` (CPython's
   `ntpath`). The rule 076 set is "refuse a name Windows may rewrite", and both sources say
   these may be rewritten; CPython says so "on the side of caution". Refusing one costs an
   embedder nothing it could use: a folder so named cannot be granted on Windows, as for `NUL`.
   `COM0` and `LPT0` stay allowed: neither source reserves them. The page mentions `COM0` once,
   as a link in the object manager's `Global??` folder; a `\\.\COM0` path reaches that, but a
   folder named `COM0` inside a path is an ordinary name (INFERRED from the page's two lists).
   The superscripts go in as `\u00b9`, `\u00b2`, `\u00b3` escapes, so the source shows which
   code points they are. `_rewritten` itself is unchanged: `str.lower()` leaves the superscripts
   and `$` alone. Without the change, a root still to be made, `C:\b\new\COM¹`, makes `new` and
   then fails "cannot be made" (076's build review, INFERRED there); with it, that root is
   refused before anything is made.

3. **The model follows the same list.** The Win32 model in `tests/unit/test_runner_grants.py`
   keeps its own `_WIN_DEVICES` (never imported from the runner, so a stand-in in the runner is
   caught) and gains the same eight names. Its folders gain `c:\b\com0`, so a row can show the
   boundary of Decision 2. The fuzz's alphabet is unchanged, so its count, 16,653, holds.

4. **How it runs on Windows: one temporary commit, `-rA` only** (spec 076's Decision 7 route,
   cut down). Main's verify step already runs `tests/unit/test_runner_grants.py` whole on all
   three systems, and both changed cases are in it. So no node id is added. The other two files
   076 named are unchanged here and hold none of the eight names. `-rA` is still needed: the
   step runs `pytest -q`, which prints a dot per test, not a `PASSED <node id>` line, and the
   workflow takes no dispatch input. The route:
   - `git commit-tree` on this branch's tip makes one commit whose only parent is the tip and
     whose tree differs only in `.github/workflows/release.yml`: `-rA` appended to the verify
     step's first command line (+1 −1). It is pushed straight to
     `refs/heads/spec/077-verify`; no local branch is made, and nothing is force-pushed.
   - `gh workflow run release.yml --ref spec/077-verify`, and wait for every job.
   - Record the run id, its `headSha`, that commit's parent (this branch's tip, the commit under
     review), the temporary diff and the per-system verdicts; quote the `PASSED` lines of
     criterion 5 from `verify (windows-2025)`.
   - `git push origin --delete spec/077-verify`; `git ls-remote` shows it gone.
   - **Authority.** Question 98's answer ("We should push changes as a branch"), as in 076.
   - **Freshness.** Any later change under `src/` or `tests/` (a review fix, or a rebase that
     changes a file there against the run's parent) needs a new dry run the same way. Only
     `context/`, `CHANGELOG.md` and `README.md` may follow it.
   - If spec 063 lands first, its shards run the whole file on Windows and print per-test
     results; the builder then uses that workflow's own output if it shows `PASSED` lines, and
     adds `-rA` only where it does not. The rest of the route is the same.

## Intent

Close spec 076's two low findings. The raw read row reads real bytes, and a control row shows
it. The Windows walk refuses the six superscript device names Microsoft reserves, and CPython's
two console names, before it opens or makes anything.

## Design

- `src/wasi_python/runner.py`: `_WIN_DEVICES` adds `*(f"com{c}" for c in "\u00b9\u00b2\u00b3")`,
  the same for `lpt`, and `"conin$"`, `"conout$"`, with a comment citing Microsoft's page and
  CPython's `ntpath`.
- `tests/unit/test_runner_grants.py`:
  - `RAW`'s `read` export: `(call $fd (local.get 0) (i32.const 200) (i32.const 1) (i32.const
    208))`.
  - `test_a_read_only_grant_refuses_raw_writes`: the docstring says the read row reads two
    bytes; the control row of Decision 1 at the end.
  - The model's `_WIN_DEVICES` gains the eight names; `_WIN_FOLDERS` gains `"c:\\b\\com0"` at
    its end.
  - `test_the_windows_walk_takes_dot_dot_on_walked_folders`: the rows of criterion 1 join the
    rewritten-name list, and their names join the `rewritten` tuple that asserts nothing was
    opened for them; one `walked_to(r"C:\b\COM0", r"C:\b\COM0")`.
- `README.md`, *Grants*: "`COM1` to `COM9`, `COM¹` to `COM³`, `LPT1` to `LPT9`, `LPT¹` to
  `LPT³`, `CONIN$`, `CONOUT$`".
- `CHANGELOG.md`, 0.1.0a7: 076's bullet names the superscript and console names, with "(spec
  077)" beside them. The raw row is a judge change, not a user-facing one, and is not listed.

## Scope

In: the two findings; the model; the README and CHANGELOG lines; one Windows dry run on a
throwaway branch.

Out:
- other reserved characters (`<>"|?*`, control characters): Windows cannot make a folder so
  named, so the walk's open fails and the path is refused, and the chain stays true (INFERRED);
- the fuzz's alphabet (Decision 3);
- a real-file-system row on Windows: the refusal comes before any open, and the model's rows
  run on every system and in the Windows verify step;
- the model's N1 (076's build review: one trailing period stripped from `a..`): it cannot
  change a verdict;
- any change to the workflow that lands.

## Acceptance criteria

Each check is seen failing first, before the code it guards, and against each stand-in named.
Stand-ins are made in the worktree, run, and restored; their output goes to `build/077/*.log`.

1. `test_the_windows_walk_takes_dot_dot_on_walked_folders` passes on macOS and Linux, and on
   Windows in the verify step. New rows, each refused "a name Windows rewrites" with nothing
   opened for the name:
   - roots still to be made, `C:\b\new\COM¹` and `C:\b\new\CONIN$` (`may_make`): nothing is
     made, since the walk raises before it returns `missing`;
   - `C:\b\com²\x`, `C:\b\Com³.log`, `C:\b\LPT¹`, `C:\b\lpt² .x`, `C:\b\lpt³.txt` and
     `C:\b\conout$.log`, so each of the six superscript names is refused in some case and
     position;
   - and `C:\b\COM0` is walked to itself (Decision 2's boundary).

   Seen failing before the change (every new refused row). **S1:** `_WIN_DEVICES` without the
   superscripts: fails on `C:\b\new\COM¹`, "DID NOT RAISE". **S2:** without `conin$` and
   `conout$`: fails on `C:\b\new\CONIN$`.
2. `test_a_read_only_grant_refuses_raw_writes` passes on macOS and Linux, and on Windows in the
   verify step, with the read row through the iovec at 200 and the control row. Seen failing
   before the change: the control row (the count at 208 is 0). **S3:** the `read` export back
   at offset 400: the control fails, `0 == 2`. **S4:** the write-only descriptor opened with
   `READ | WRITE` rights: the read row fails, answering 0, not the wrong-mode errno.
3. The README and CHANGELOG lines of the Design.
4. In the worktree, without `--accept`: the fast tier while building, then the full judge with
   `-n 6` before "built": no pass lost, nothing grows, the judge change named
   (`tests/unit/test_runner_grants.py`); `ruff check` and `ruff format --check` green;
   `tests/public_api.txt` unchanged.
5. **On Windows:** one release dry run on `spec/077-verify` (Decision 4), every job passed on
   all three systems. The landing notes record the run id, its `headSha`, that commit's parent
   (this branch's tip, as reviewed), the temporary diff and the branch's deletion, and quote
   the `PASSED` line from `verify (windows-2025)` for
   `test_the_windows_walk_takes_dot_dot_on_walked_folders`,
   `test_the_windows_walk_records_the_true_chain` and
   `test_a_read_only_grant_refuses_raw_writes`. A node missing, `SKIPPED`, blocked or
   deselected there fails this criterion, as a `FAILED` one does. A failure is fixed here and
   run again on a new throwaway branch; nothing is skipped or allowed to fail.

## Landing notes

Not yet built.

## One line

Point the raw read row at a real two-byte buffer and prove it with a control read, and refuse
`COM¹` to `COM³`, `LPT¹` to `LPT³`, `CONIN$` and `CONOUT$` on Windows as `NUL` is refused, run
once on Windows with `-rA` on a throwaway branch.
